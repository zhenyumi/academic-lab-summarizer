from __future__ import annotations

"""Copyable template runner for academic-lab-summarizer.

Reads lab_summary_input.json and upstream worker artifacts (from fixtures or
real worker outputs), then writes lab_summary_manifest.json.

No network calls. Copy into <run>/tools/ and adapt for real runs.
"""

import argparse
import json
from pathlib import Path


EXPECTED_SITE_ARTIFACTS = [
    "lab_site_plan.json",
    "lab_pages.jsonl",
    "lab_site_evidence.jsonl",
    "lab_site_audit.json",
]

EXPECTED_PUB_ARTIFACTS = [
    "publication_search_plan.json",
    "publication_candidates.jsonl",
    "publications.curated.json",
    "publication_evidence.jsonl",
    "publication_audit.json",
    "research_theme_profile.json",
]

EXPECTED_FIT_ARTIFACTS = [
    "position_signals.json",
    "lab_summary_assessment.json",
    "lab_profile.json",
    "report.md",
    "lab_summary_audit.json",
]


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def file_exists(path: Path) -> bool:
    return path.is_file()


def read_audit_status(audit_path: Path) -> str:
    """Read audit status, trying .sample. variant if canonical name not found."""
    if not audit_path.exists():
        sample_path = audit_path.with_name(
            audit_path.name.replace(".json", ".sample.json")
        )
        if sample_path.exists():
            audit_path = sample_path
        else:
            return "fail"
    try:
        data = read_json(audit_path)
        return data.get("status", "fail")
    except Exception:
        return "fail"


def build_manifest(
    input_data: dict,
    out_dir: Path,
    site_fixtures: Path | None,
    pub_fixtures: Path | None,
    fit_fixtures: Path | None,
) -> dict:
    lab_id = input_data["lab_id"]
    rel_prefix = f"lab_summaries/{lab_id}/"

    def artifact_entry(filename: str) -> str:
        return f"{rel_prefix}{filename}"

    # Step 1: site evidence
    site_audit_path = out_dir / "lab_site_audit.json"
    if site_fixtures:
        site_audit_path = site_fixtures / "lab_site_audit.json"
    site_audit_status = read_audit_status(site_audit_path)
    site_status = "completed" if site_audit_status in ("pass", "partial") else "failed"
    site_artifacts = {a: artifact_entry(a) for a in EXPECTED_SITE_ARTIFACTS}

    # Step 2: publication profile
    pub_audit_path = out_dir / "publication_audit.json"
    if pub_fixtures:
        pub_audit_path = pub_fixtures / "publication_audit.json"
    pub_audit_status = read_audit_status(pub_audit_path)

    if site_audit_status == "fail":
        pub_status = "skipped"
        pub_audit_status_val = "skipped"
        pub_artifacts = {}
    else:
        pub_audit_status_val = pub_audit_status
        pub_status = "completed" if pub_audit_status in ("pass", "partial") else "failed"
        pub_artifacts = {a: artifact_entry(a) for a in EXPECTED_PUB_ARTIFACTS}

    # Step 3: lab profile synthesis
    fit_audit_path = out_dir / "lab_summary_audit.json"
    if fit_fixtures:
        fit_audit_path = fit_fixtures / "lab_summary_audit.json"

    if site_audit_status == "fail" or (pub_audit_status == "fail" and site_audit_status != "fail"):
        fit_status = "skipped"
        fit_audit_status_val = "skipped"
        fit_artifacts = {}
    else:
        fit_audit_status = read_audit_status(fit_audit_path)
        fit_audit_status_val = fit_audit_status
        fit_status = "completed" if fit_audit_status in ("pass", "partial") else "failed"
        fit_artifacts = {a: artifact_entry(a) for a in EXPECTED_FIT_ARTIFACTS}

    # overall_status
    step_statuses = [site_status, pub_status, fit_status]
    if "failed" in step_statuses:
        overall = "failed"
    elif all(s in ("completed", "partial") for s in step_statuses):
        overall = "completed"
    else:
        overall = "partial"

    steps = [
        {
            "skill": "lab-site-evidence-extraction",
            "status": site_status,
            "audit_status": site_audit_status,
            "artifacts": site_artifacts,
        },
        {
            "skill": "lab-publication-profile",
            "status": pub_status,
            "audit_status": pub_audit_status_val,
            "artifacts": pub_artifacts,
        },
        {
            "skill": "lab-profile-synthesis",
            "status": fit_status,
            "audit_status": fit_audit_status_val,
            "artifacts": fit_artifacts,
        },
    ]

    return {
        "lab_id": lab_id,
        "lab_name": input_data.get("lab_name", ""),
        "pi_name": input_data.get("pi_name", ""),
        "institution": input_data.get("institution", ""),
        "lab_url": input_data.get("lab_url", ""),
        "input_mode": input_data.get("input_mode", "from_lab_url"),
        "steps": steps,
        "overall_status": overall,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to lab_summary_input.json")
    parser.add_argument("--out", required=True, help="Output directory for manifest")
    parser.add_argument("--site-fixtures", help="Directory with site evidence fixtures")
    parser.add_argument("--pub-fixtures", help="Directory with publication profile fixtures")
    parser.add_argument("--fit-fixtures", help="Directory with lab profile synthesis fixtures")
    args = parser.parse_args()

    input_data = read_json(Path(args.input))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    site_fix = Path(args.site_fixtures) if args.site_fixtures else None
    pub_fix = Path(args.pub_fixtures) if args.pub_fixtures else None
    fit_fix = Path(args.fit_fixtures) if args.fit_fixtures else None

    manifest = build_manifest(input_data, out_dir, site_fix, pub_fix, fit_fix)

    manifest_path = out_dir / "lab_summary_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    n_steps = len(manifest["steps"])
    completed = sum(1 for s in manifest["steps"] if s["status"] in ("completed", "partial"))
    skipped = sum(1 for s in manifest["steps"] if s["status"] == "skipped")
    print(f"Wrote {manifest_path}: {n_steps} steps, {completed} completed/partial, {skipped} skipped, overall={manifest['overall_status']}")


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Copyable template audit script for lab-profile-synthesis.

Reads lab profile synthesis artifacts and writes lab_summary_audit.json.
No network calls. Copy into <run>/tools/ and adapt for real runs.
"""

import argparse
import json
from pathlib import Path


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


def write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def audit(artifact_dir: Path) -> dict:
    errors: list[str] = []

    hs_path = artifact_dir / "position_signals.json"
    fa_path = artifact_dir / "lab_summary_assessment.json"
    lp_path = artifact_dir / "lab_profile.json"
    se_path = artifact_dir / "lab_site_evidence.jsonl"
    pe_path = artifact_dir / "publication_evidence.jsonl"
    cu_path = artifact_dir / "publications.curated.json"
    th_path = artifact_dir / "research_theme_profile.json"

    if not hs_path.exists():
        errors.append("position_signals.json not found")
    if not fa_path.exists():
        errors.append("lab_summary_assessment.json not found")
    if not lp_path.exists():
        errors.append("lab_profile.json not found")

    if errors:
        return {
            "lab_id": "unknown",
            "status": "fail",
            "metrics": {},
            "blocking": errors,
            "warnings": [],
            "repair_hints": [],
        }

    positions = read_json(hs_path)
    fit = read_json(fa_path)
    profile = read_json(lp_path)
    lab_id = positions.get("lab_id", profile.get("lab_id", "unknown"))

    site_evidence = read_jsonl(se_path) if se_path.exists() else []
    pub_evidence = read_jsonl(pe_path) if pe_path.exists() else []
    curated = read_json(cu_path) if cu_path.exists() else {"candidates": []}
    themes = read_json(th_path) if th_path.exists() else {"themes": []}

    curated_items = curated.get("candidates", curated.get("publications", []))
    confirmed = [c for c in curated_items if c.get("match_tier") == "confirmed"]
    likely = [c for c in curated_items if c.get("match_tier") == "likely"]
    ambiguous = [c for c in curated_items if c.get("match_tier") == "ambiguous"]

    signals = positions.get("signals", [])
    confirmed_sigs = [s for s in signals if s.get("signal_strength") == "confirmed_opening"]
    generic_sigs = [s for s in signals if s.get("signal_strength") == "generic_recruitment"]

    dims = fit.get("dimensions", [])
    dims_assessed = sum(1 for d in dims if d.get("status") == "assessed")
    dims_partial = sum(1 for d in dims if d.get("status") == "partial")
    dims_unavail = sum(1 for d in dims if d.get("status") == "unavailable")

    all_refs = []
    for sig in signals:
        all_refs.extend(sig.get("evidence_refs", []))
    for dim in dims:
        all_refs.extend(dim.get("evidence_refs", []))
    for theme in profile.get("research_themes", []):
        all_refs.extend(theme.get("evidence_refs", []))

    weak_ev = sum(1 for ev in site_evidence if ev.get("evidence_quality") in ("link_text_only", "none"))
    weak_ratio = round(weak_ev / len(site_evidence), 2) if site_evidence else 0.0

    blocking = []
    warnings = []
    repair_hints = []

    if not site_evidence:
        blocking.append("No site evidence found.")
    if not confirmed and not likely:
        blocking.append("No confirmed or likely publications found.")
    if not signals:
        warnings.append("No position signals found.")

    for ws in generic_sigs:
        warnings.append(f"Signal {ws.get('signal_id', '?')}: generic recruitment — must not be reported as a confirmed open position.")

    if ambiguous:
        warnings.append(f"{len(ambiguous)} publication(s) ambiguous and excluded from research themes.")

    fi_dim = next((d for d in dims if d.get("dimension") == "funding_indicators"), None)
    if fi_dim and fi_dim.get("status") == "unavailable":
        warnings.append("Funding indicators dimension is unavailable.")
        repair_hints.append("Check lab site for grant or funding pages if funding indicators are important.")

    if dims_unavail > 2:
        warnings.append(f"{dims_unavail} dimensions unavailable — limited assessment quality.")

    status = "fail" if blocking else ("partial" if warnings or dims_unavail > 0 else "pass")

    return {
        "lab_id": lab_id,
        "status": status,
        "metrics": {
            "site_evidence_count": len(site_evidence),
            "publication_evidence_count": len(pub_evidence),
            "confirmed_publication_count": len(confirmed),
            "likely_publication_count": len(likely),
            "ambiguous_publications_excluded": len(ambiguous),
            "position_signals_count": len(signals),
            "confirmed_position_signals": len(confirmed_sigs),
            "generic_position_signals": len(generic_sigs),
            "dimensions_assessed": dims_assessed,
            "dimensions_partial": dims_partial,
            "dimensions_unavailable": dims_unavail,
            "evidence_refs_total": len(all_refs),
            "weak_evidence_ratio": weak_ratio,
        },
        "blocking": blocking,
        "warnings": warnings,
        "repair_hints": repair_hints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", help="Directory containing lab profile synthesis artifacts")
    parser.add_argument("--out", help="Output path (default: <artifact_dir>/lab_summary_audit.json)")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_dir():
        print(f"Error: not a directory: {artifact_dir}", file=sys.stderr)
        return 1

    result = audit(artifact_dir)
    out_path = Path(args.out) if args.out else artifact_dir / "lab_summary_audit.json"
    write_json(out_path, result)

    status = result["status"]
    print(f"Audit {status}: wrote {out_path}")
    return 0 if status in ("pass", "partial") else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SIGNAL_STRENGTHS = {
    "confirmed_opening", "likely_opening", "generic_recruitment",
    "closed_or_past", "none", "unknown",
}
POSITION_CATEGORIES = {
    "phd", "masters", "undergraduate", "postdoc", "research_assistant",
    "technician", "lab_manager", "staff_scientist", "other", "none",
}
CONFIDENCE_VALUES = {"high", "medium", "low", "unknown"}
DIMENSIONS = {
    "research_focus", "publication_profile", "position_availability",
    "lab_activity_and_trajectory", "methods_and_approaches", "funding_indicators",
}
DIMENSION_STATUSES = {"assessed", "partial", "unavailable", "skipped"}
OVERALL_ASSESSMENT = {"strong_profile", "usable_profile", "limited_profile", "insufficient_evidence", "unknown"}
AUDIT_STATUSES = {"pass", "partial", "fail"}

SAMPLE_NAME_MAP = {
    "lab_summary_input.json": "lab_summary_input.sample.json",
    "position_signals.json": "position_signals.sample.json",
    "lab_summary_assessment.json": "lab_summary_assessment.sample.json",
    "lab_profile.json": "lab_profile.sample.json",
    "lab_summary_audit.json": "lab_summary_audit.sample.json",
    "report.md": "report.sample.md",
    "lab_site_evidence.jsonl": "lab_site_evidence.sample.jsonl",
    "publications.curated.json": "publications.curated.sample.json",
    "publication_evidence.jsonl": "publication_evidence.sample.jsonl",
    "research_theme_profile.json": "research_theme_profile.sample.json",
}

EVIDENCE_REF_RE = re.compile(r"^(site|pub):(\d+)$")


def parse_evidence_ref(ref: str) -> tuple[str, int] | None:
    m = EVIDENCE_REF_RE.match(ref)
    if m:
        return m.group(1), int(m.group(2))
    return None


def load_json(path: Path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path.name} line {i}: invalid JSON: {e}") from e
    return rows


def validate_position_signals(data: dict, site_evidence_ids: set[int], errors: list[str]) -> None:
    if "lab_id" not in data:
        errors.append("position_signals.json: missing lab_id")
    if "signals" not in data or not isinstance(data.get("signals"), list):
        errors.append("position_signals.json: missing or invalid signals array")
        return
    if "overall_position_signal" not in data:
        errors.append("position_signals.json: missing overall_position_signal")
    elif data["overall_position_signal"] not in SIGNAL_STRENGTHS:
        errors.append(f"position_signals.json: invalid overall_position_signal={data['overall_position_signal']}")
    for sig in data["signals"]:
        sid = sig.get("signal_id", "?")
        for field in ("signal_id", "source_url", "snippet", "position_category",
                      "signal_strength", "evidence_refs", "confidence",
                      "last_observed_or_posted_date"):
            if field not in sig:
                errors.append(f"position_signals.json: signal {sid}: missing {field}")
        if sig.get("position_category") not in POSITION_CATEGORIES:
            errors.append(f"position_signals.json: signal {sid}: invalid position_category={sig.get('position_category')}")
        if sig.get("signal_strength") not in SIGNAL_STRENGTHS:
            errors.append(f"position_signals.json: signal {sid}: invalid signal_strength={sig.get('signal_strength')}")
        if sig.get("confidence") not in CONFIDENCE_VALUES:
            errors.append(f"position_signals.json: signal {sid}: invalid confidence={sig.get('confidence')}")
        if sig.get("signal_strength") == "confirmed_opening" and sig.get("position_category") in {"other", "none"}:
            errors.append(f"position_signals.json: signal {sid}: generic/unknown role cannot be confirmed_opening")
        for ref in sig.get("evidence_refs", []):
            parsed = parse_evidence_ref(ref)
            if parsed is None:
                errors.append(f"position_signals.json: signal {sid}: invalid evidence_ref format '{ref}'")
            elif parsed[0] == "site" and parsed[1] not in site_evidence_ids:
                errors.append(f"position_signals.json: signal {sid}: site:{parsed[1]} not in site evidence")


def validate_fit_assessment(data: dict, site_evidence_ids: set[int], pub_ids: set[int], errors: list[str]) -> None:
    if "lab_id" not in data:
        errors.append("lab_summary_assessment.json: missing lab_id")
    if "dimensions" not in data or not isinstance(data.get("dimensions"), list):
        errors.append("lab_summary_assessment.json: missing or invalid dimensions array")
        return
    if "overall_assessment" not in data:
        errors.append("lab_summary_assessment.json: missing overall_assessment")
    elif data["overall_assessment"] not in OVERALL_ASSESSMENT:
        errors.append(f"lab_summary_assessment.json: invalid overall_assessment={data['overall_assessment']}")
    if "overall_confidence" not in data:
        errors.append("lab_summary_assessment.json: missing overall_confidence")
    elif data["overall_confidence"] not in CONFIDENCE_VALUES:
        errors.append(f"lab_summary_assessment.json: invalid overall_confidence={data['overall_confidence']}")
    for dim in data["dimensions"]:
        dname = dim.get("dimension", "?")
        if dname not in DIMENSIONS:
            errors.append(f"lab_summary_assessment.json: dimension {dname}: unknown dimension")
        for field in ("dimension", "description", "assessment", "confidence", "evidence_refs", "status"):
            if field not in dim:
                errors.append(f"lab_summary_assessment.json: dimension {dname}: missing {field}")
        if dim.get("status") not in DIMENSION_STATUSES:
            errors.append(f"lab_summary_assessment.json: dimension {dname}: invalid status={dim.get('status')}")
        if dim.get("confidence") not in CONFIDENCE_VALUES:
            errors.append(f"lab_summary_assessment.json: dimension {dname}: invalid confidence={dim.get('confidence')}")
        if "limitations" not in dim:
            errors.append(f"lab_summary_assessment.json: dimension {dname}: missing limitations")
        for ref in dim.get("evidence_refs", []):
            parsed = parse_evidence_ref(ref)
            if parsed is None:
                errors.append(f"lab_summary_assessment.json: dimension {dname}: invalid evidence_ref '{ref}'")
            elif parsed[0] == "site" and parsed[1] not in site_evidence_ids:
                errors.append(f"lab_summary_assessment.json: dimension {dname}: site:{parsed[1]} not in site evidence")
            elif parsed[0] == "pub" and parsed[1] not in pub_ids:
                errors.append(f"lab_summary_assessment.json: dimension {dname}: pub:{parsed[1]} not in confirmed/likely publications")


def validate_lab_profile(data: dict, confirmed_ids: set[int], likely_ids: set[int], errors: list[str]) -> None:
    for field in ("lab_id", "lab_name", "pi_name", "institution", "lab_url", "research_themes",
                  "confirmed_publication_count", "likely_publication_count", "position_signal",
                  "overall_assessment", "evidence_summary", "limitations"):
        if field not in data:
            errors.append(f"lab_profile.json: missing {field}")
    themes = data.get("research_themes", [])
    valid_pub_ids = confirmed_ids | likely_ids
    for theme in themes:
        if "theme" not in theme:
            errors.append("lab_profile.json: research theme missing 'theme'")
        if "confidence" not in theme:
            errors.append("lab_profile.json: research theme missing 'confidence'")
        for ref in theme.get("evidence_refs", []):
            parsed = parse_evidence_ref(ref)
            if parsed is None:
                errors.append(f"lab_profile.json: theme '{theme.get('theme', '?')}': invalid evidence_ref '{ref}'")
            elif parsed[0] == "pub" and parsed[1] not in valid_pub_ids:
                errors.append(f"lab_profile.json: theme '{theme.get('theme', '?')}': pub:{parsed[1]} not in confirmed/likely publications")


def validate_report(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    required_sections = [
        "# Lab Profile:",
        "## PI:",
        "## Institution:",
        "## Research Themes",
        "## Important Recent Publications",
        "## Recent Publications",
        "## Position Signals",
        "## Lab Summary Assessment",
        "## Methods and Approaches",
        "## Funding/Resource Indicators",
        "## Limitations",
    ]
    for section in required_sections:
        if section not in text:
            errors.append(f"report.md: missing required section '{section}'")


def validate_audit(data: dict, errors: list[str]) -> None:
    if "lab_id" not in data:
        errors.append("lab_summary_audit.json: missing lab_id")
    if "status" not in data:
        errors.append("lab_summary_audit.json: missing status")
    elif data["status"] not in AUDIT_STATUSES:
        errors.append(f"lab_summary_audit.json: invalid status={data['status']}")
    for field in ("metrics", "blocking", "warnings", "repair_hints"):
        if field not in data:
            errors.append(f"lab_summary_audit.json: missing {field}")
    blocking = data.get("blocking", [])
    if blocking and data.get("status") != "fail":
        errors.append("lab_summary_audit.json: blocking issues present but status is not 'fail'")


def resolve_path(base: Path, name: str, sample_names: bool) -> Path | None:
    lookup = SAMPLE_NAME_MAP.get(name, name) if sample_names else name
    p = base / lookup
    return p if p.exists() else None


def validate_artifacts(artifact_dir: Path, sample_names: bool = False) -> list[str]:
    errors: list[str] = []

    site_path = resolve_path(artifact_dir, "lab_site_evidence.jsonl", sample_names)
    site_evidence_ids: set[int] = set()
    if site_path:
        for row in read_jsonl(site_path):
            if "evidence_id" in row:
                site_evidence_ids.add(row["evidence_id"])

    curated_path = resolve_path(artifact_dir, "publications.curated.json", sample_names)
    all_pub_ids: set[int] = set()
    confirmed_ids: set[int] = set()
    likely_ids: set[int] = set()
    if curated_path:
        curated = load_json(curated_path)
        for c in curated.get("candidates", curated.get("publications", [])):
            cid = c.get("candidate_id")
            if cid is not None:
                all_pub_ids.add(cid)
                tier = c.get("match_tier")
                if tier == "confirmed":
                    confirmed_ids.add(cid)
                elif tier == "likely":
                    likely_ids.add(cid)

    hs_path = resolve_path(artifact_dir, "position_signals.json", sample_names)
    if hs_path:
        validate_position_signals(load_json(hs_path), site_evidence_ids, errors)
    else:
        errors.append("position_signals.json: not found")

    fa_path = resolve_path(artifact_dir, "lab_summary_assessment.json", sample_names)
    if fa_path:
        validate_fit_assessment(load_json(fa_path), site_evidence_ids, all_pub_ids, errors)
    else:
        errors.append("lab_summary_assessment.json: not found")

    lp_path = resolve_path(artifact_dir, "lab_profile.json", sample_names)
    if lp_path:
        validate_lab_profile(load_json(lp_path), confirmed_ids, likely_ids, errors)
    else:
        errors.append("lab_profile.json: not found")

    report_path = resolve_path(artifact_dir, "report.md", sample_names)
    if report_path:
        validate_report(report_path, errors)
    else:
        errors.append("report.md: not found")

    audit_path = resolve_path(artifact_dir, "lab_summary_audit.json", sample_names)
    if audit_path:
        validate_audit(load_json(audit_path), errors)
    else:
        errors.append("lab_summary_audit.json: not found")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate lab profile synthesis artifacts")
    parser.add_argument("artifact_dir", nargs="?", help="Directory containing artifacts")
    parser.add_argument("--examples", action="store_true", help="Validate .sample. files in examples/")
    args = parser.parse_args()

    if args.examples:
        base = Path(__file__).resolve().parent.parent / "examples"
        if not base.is_dir():
            print(f"INVALID: examples directory not found: {base}", file=sys.stderr)
            return 1
        errors = validate_artifacts(base, sample_names=True)
        if errors:
            print("INVALID: synthetic examples", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("VALID: synthetic examples")
        return 0

    if not args.artifact_dir:
        parser.error("artifact_dir is required when --examples is not used")

    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_dir():
        print(f"INVALID: not a directory: {artifact_dir}", file=sys.stderr)
        return 1

    errors = validate_artifacts(artifact_dir, sample_names=False)
    if errors:
        print(f"INVALID: {artifact_dir}", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"VALID: {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

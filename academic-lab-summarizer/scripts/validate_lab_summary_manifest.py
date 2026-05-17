#!/usr/bin/env python3
"""Validate lab_summary_manifest.json against the workflow contract.

Checks manifest structure, required fields, step artifacts, audit_status,
artifact paths, stop conditions, and overall_status consistency.
No network calls, no file mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_INPUT_MODES = {"from_lab_url"}
ALLOWED_STEP_STATUS = {"completed", "partial", "failed", "skipped"}
ALLOWED_AUDIT_STATUS = {"pass", "partial", "fail", "skipped"}
ALLOWED_OVERALL_STATUS = {"completed", "partial", "failed"}

EXPECTED_SKILLS = [
    "lab-site-evidence-extraction",
    "lab-publication-profile",
    "lab-profile-synthesis",
]

EXPECTED_ARTIFACTS = {
    "lab-site-evidence-extraction": {
        "lab_site_plan.json",
        "lab_pages.jsonl",
        "lab_site_evidence.jsonl",
        "lab_site_audit.json",
    },
    "lab-publication-profile": {
        "publication_search_plan.json",
        "publication_candidates.jsonl",
        "publications.curated.json",
        "publication_evidence.jsonl",
        "publication_audit.json",
        "research_theme_profile.json",
    },
    "lab-profile-synthesis": {
        "position_signals.json",
        "lab_summary_assessment.json",
        "lab_profile.json",
        "report.md",
        "lab_summary_audit.json",
    },
}

SAMPLE_NAME_MAP = {
    "lab_summary_manifest.json": "lab_summary_manifest.sample.json",
}


def _load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            return json.load(fh), []
    except Exception as exc:
        return None, [f"Failed to read {path.name}: {exc}"]


def validate_manifest(data: dict) -> list[str]:
    errors: list[str] = []

    # Required top-level fields
    for field in ("lab_id", "lab_name", "pi_name", "institution", "lab_url",
                  "input_mode", "steps", "overall_status"):
        if field not in data:
            errors.append(f"Missing required top-level field: {field}")

    if errors:
        return errors

    # input_mode
    if data["input_mode"] not in ALLOWED_INPUT_MODES:
        errors.append(f"input_mode={data['input_mode']!r} not in {ALLOWED_INPUT_MODES}")

    # overall_status
    if data["overall_status"] not in ALLOWED_OVERALL_STATUS:
        errors.append(f"overall_status={data['overall_status']!r} not in {ALLOWED_OVERALL_STATUS}")

    # steps
    steps = data.get("steps", [])
    if not isinstance(steps, list):
        errors.append("steps must be an array")
        return errors

    step_skills = [s.get("skill") for s in steps]
    if step_skills != EXPECTED_SKILLS:
        errors.append(f"steps must contain exactly {EXPECTED_SKILLS} in order, got {step_skills}")

    lab_id = data.get("lab_id", "")
    expected_prefix = f"lab_summaries/{lab_id}/"

    site_audit_fail = False
    pub_audit_fail = False

    for i, step in enumerate(steps):
        prefix = f"steps[{i}] ({step.get('skill', '?')})"

        # Required fields
        for field in ("skill", "status", "artifacts"):
            if field not in step:
                errors.append(f"{prefix}: missing required field {field}")

        skill = step.get("skill", "")
        status = step.get("status", "")

        if status not in ALLOWED_STEP_STATUS:
            errors.append(f"{prefix}: status={status!r} not in {ALLOWED_STEP_STATUS}")

        # Track audit failures
        if skill == "lab-site-evidence-extraction" and step.get("audit_status") == "fail":
            site_audit_fail = True
        if skill == "lab-publication-profile" and step.get("audit_status") == "fail":
            pub_audit_fail = True

        # Per-step validation depends on whether the step is skipped
        if status == "skipped":
            # Skipped step: audit_status must be "skipped", artifacts must be empty
            if "audit_status" in step and step["audit_status"] != "skipped":
                errors.append(f"{prefix}: skipped step must have audit_status='skipped', got {step['audit_status']!r}")
            if "artifacts" in step and step.get("artifacts") != {}:
                errors.append(f"{prefix}: skipped step must have empty artifacts")
        else:
            # Non-skipped step: audit_status required and must be pass/partial/fail
            if "audit_status" not in step:
                errors.append(f"{prefix}: missing required audit_status")
            elif step["audit_status"] not in {"pass", "partial", "fail"}:
                errors.append(f"{prefix}: audit_status={step['audit_status']!r} not in pass/partial/fail")

            # audit_status consistency with step status
            if step.get("audit_status") == "fail" and status == "completed":
                errors.append(f"{prefix}: audit_status=fail but step status=completed")

            # Artifact paths
            artifacts = step.get("artifacts", {})
            if not isinstance(artifacts, dict):
                errors.append(f"{prefix}: artifacts must be an object")
                continue

            expected = EXPECTED_ARTIFACTS.get(skill, set())
            actual = set(artifacts.keys())
            missing = expected - actual
            extra = actual - expected
            if missing:
                errors.append(f"{prefix}: missing artifacts: {sorted(missing)}")
            if extra:
                errors.append(f"{prefix}: unexpected artifacts: {sorted(extra)}")

            for filename, path_str in artifacts.items():
                if not isinstance(path_str, str) or not path_str.startswith(expected_prefix):
                    errors.append(f"{prefix}: artifact {filename} path must start with {expected_prefix!r}, got {path_str!r}")

    # Stop condition consistency
    if site_audit_fail:
        for step in steps:
            if step.get("skill") == "lab-publication-profile" and step.get("status") != "skipped":
                errors.append("site audit failed but publication-profile step is not skipped")
            if step.get("skill") == "lab-profile-synthesis" and step.get("status") != "skipped":
                errors.append("site audit failed but lab-profile-synthesis step is not skipped")

    if pub_audit_fail:
        for step in steps:
            if step.get("skill") == "lab-profile-synthesis" and step.get("status") != "skipped":
                errors.append("publication audit failed but lab-profile-synthesis step is not skipped")

    # overall_status consistency
    step_statuses = [s.get("status") for s in steps]
    if data["overall_status"] == "completed":
        if not all(s in ("completed", "partial") for s in step_statuses):
            errors.append("overall_status=completed but not all steps are completed/partial")
    if data["overall_status"] == "failed":
        if "failed" not in step_statuses:
            errors.append("overall_status=failed but no step has status=failed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", nargs="?", help="Path to manifest directory or file")
    parser.add_argument("--examples", action="store_true",
                        help="Validate sample files from examples/ directory")
    args = parser.parse_args()

    if args.examples:
        examples_dir = Path(__file__).resolve().parent.parent / "examples"
        sample_file = examples_dir / SAMPLE_NAME_MAP["lab_summary_manifest.json"]
        if not sample_file.exists():
            print(f"FAIL: sample not found: {sample_file}", file=sys.stderr)
            return 1
        data, load_errors = _load_json(sample_file)
        if load_errors:
            for e in load_errors:
                print(f"FAIL: {e}", file=sys.stderr)
            return 1
        errors = validate_manifest(data)
        if errors:
            print(f"INVALID: {sample_file}", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print(f"VALID: synthetic examples")
        return 0

    if not args.manifest_path:
        parser.error("manifest_path is required when --examples is not used")

    target = Path(args.manifest_path)
    if target.is_dir():
        manifest_file = target / "lab_summary_manifest.json"
    else:
        manifest_file = target

    if not manifest_file.exists():
        print(f"FAIL: manifest not found: {manifest_file}", file=sys.stderr)
        return 1

    data, load_errors = _load_json(manifest_file)
    if load_errors:
        for e in load_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    errors = validate_manifest(data)
    if errors:
        print(f"INVALID: {manifest_file}", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"VALID: {manifest_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate lab-site-evidence-extraction artifacts.

Checks lab_summary_input.json, lab_site_plan.json, lab_pages.jsonl,
lab_site_evidence.jsonl, and lab_site_audit.json against the contract.
No network calls, no file mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ALLOWED_CLAIM_TYPES = {
    "research_direction", "pi_info", "lab_member",
    "publication_ref", "position_signal", "lab_url",
    "facility", "other",
}

ALLOWED_EVIDENCE_QUALITY = {
    "research_description", "profile_snippet", "link_text_only", "none",
}

ALLOWED_EXTRACTION_STATUS = {
    "extracted", "partial", "unavailable", "skipped",
}

ALLOWED_AUDIT_STATUS = {"pass", "partial", "fail"}

ALLOWED_CONFIDENCE = {"high", "medium", "low", "unknown"}


def _is_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            return json.load(fh), []
    except Exception as exc:
        return None, [f"Failed to read {path.name}: {exc}"]


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return [], [f"File not found: {path.name}"]
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            for i, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    errors.append(f"{path.name} line {i}: JSON decode error: {exc}")
    except Exception as exc:
        errors.append(f"Failed to read {path.name}: {exc}")
    return rows, errors


def _validate_lab_summary_input(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["lab_summary_input.json must be a JSON object."]
    for field in ("lab_id", "lab_name", "pi_name", "institution", "lab_url"):
        if field not in data:
            errors.append(f"lab_summary_input.json missing required field: {field}")
    if "lab_url" in data and not _is_url(data["lab_url"]):
        errors.append("lab_summary_input.json lab_url must be an http(s) URL.")
    return errors


def _validate_lab_site_plan(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["lab_site_plan.json must be a JSON object."]
    for field in ("lab_url", "allowed_domains", "entry_urls", "crawl_limits"):
        if field not in data:
            errors.append(f"lab_site_plan.json missing required field: {field}")
    if "lab_url" in data and not _is_url(data["lab_url"]):
        errors.append("lab_site_plan.json lab_url must be an http(s) URL.")
    if "entry_urls" in data:
        urls = data["entry_urls"]
        if not isinstance(urls, list) or not all(_is_url(u) for u in urls):
            errors.append("lab_site_plan.json entry_urls must be a list of http(s) URLs.")
    crawl_limits = data.get("crawl_limits")
    if isinstance(crawl_limits, dict):
        for key in ("max_pages", "max_depth"):
            if not isinstance(crawl_limits.get(key), int) or crawl_limits[key] <= 0:
                errors.append(f"lab_site_plan.json crawl_limits.{key} must be a positive integer.")
    return errors


def _validate_lab_pages(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for i, row in enumerate(rows):
        row_label = f"lab_pages.jsonl row {i + 1}"
        for field in ("page_id", "url", "depth"):
            if field not in row:
                errors.append(f"{row_label} missing required field: {field}")
        if "url" in row and not _is_url(row["url"]):
            errors.append(f"{row_label} url must be an http(s) URL.")
        if "depth" in row and not isinstance(row["depth"], int):
            errors.append(f"{row_label} depth must be an integer.")
    return errors


def _validate_lab_site_evidence(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    has_research_direction = False
    for i, row in enumerate(rows):
        row_label = f"lab_site_evidence.jsonl row {i + 1}"
        for field in ("evidence_id", "lab_id", "source_url", "snippet",
                      "claim_type", "evidence_quality", "extraction_status"):
            if field not in row:
                errors.append(f"{row_label} missing required field: {field}")
        if "source_url" in row and not _is_url(row["source_url"]):
            errors.append(f"{row_label} source_url must be an http(s) URL.")
        if row.get("claim_type") and row["claim_type"] not in ALLOWED_CLAIM_TYPES:
            errors.append(f"{row_label} invalid claim_type: {row['claim_type']}")
        if row.get("evidence_quality") and row["evidence_quality"] not in ALLOWED_EVIDENCE_QUALITY:
            errors.append(f"{row_label} invalid evidence_quality: {row['evidence_quality']}")
        if row.get("extraction_status") and row["extraction_status"] not in ALLOWED_EXTRACTION_STATUS:
            errors.append(f"{row_label} invalid extraction_status: {row['extraction_status']}")
        if row.get("confidence") and row["confidence"] not in ALLOWED_CONFIDENCE:
            errors.append(f"{row_label} invalid confidence: {row['confidence']}")
        if row.get("claim_type") == "research_direction" and row.get("extraction_status") == "extracted":
            has_research_direction = True
    if rows and not has_research_direction:
        errors.append("lab_site_evidence.jsonl: missing research_direction evidence")
    return errors


def _validate_lab_site_audit(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["lab_site_audit.json must be a JSON object."]
    for field in ("status", "metrics", "blocking_failures", "warnings"):
        if field not in data:
            errors.append(f"lab_site_audit.json missing required field: {field}")
    if data.get("status") and data["status"] not in ALLOWED_AUDIT_STATUS:
        errors.append(f"lab_site_audit.json invalid status: {data['status']}")
    if "blocking_failures" in data and not isinstance(data["blocking_failures"], list):
        errors.append("lab_site_audit.json blocking_failures must be a list.")
    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("lab_site_audit.json warnings must be a list.")
    return errors


SAMPLE_NAME_MAP = {
    "lab_summary_input.json": "lab_summary_input.sample.json",
    "lab_site_plan.json": "lab_site_plan.sample.json",
    "lab_pages.jsonl": "lab_pages.sample.jsonl",
    "lab_site_evidence.jsonl": "lab_site_evidence.sample.jsonl",
    "lab_site_audit.json": "lab_site_audit.sample.json",
}


def validate_dir(artifact_dir: Path, sample_names: bool = False) -> list[str]:
    errors: list[str] = []

    for canonical, sample in SAMPLE_NAME_MAP.items():
        filename = sample if sample_names else canonical
        if canonical == "lab_summary_input.json":
            data, read_errors = _load_json(artifact_dir / filename)
            errors.extend(read_errors)
            if data is not None:
                errors.extend(_validate_lab_summary_input(data))
        elif canonical == "lab_site_plan.json":
            plan, read_errors = _load_json(artifact_dir / filename)
            errors.extend(read_errors)
            if plan is not None:
                errors.extend(_validate_lab_site_plan(plan))
        elif canonical == "lab_pages.jsonl":
            pages, read_errors = _load_jsonl(artifact_dir / filename)
            errors.extend(read_errors)
            if pages:
                errors.extend(_validate_lab_pages(pages))
        elif canonical == "lab_site_evidence.jsonl":
            evidence, read_errors = _load_jsonl(artifact_dir / filename)
            errors.extend(read_errors)
            if evidence:
                errors.extend(_validate_lab_site_evidence(evidence))
        elif canonical == "lab_site_audit.json":
            audit, read_errors = _load_json(artifact_dir / filename)
            errors.extend(read_errors)
            if audit is not None:
                errors.extend(_validate_lab_site_audit(audit))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate lab-site-evidence-extraction artifacts."
    )
    parser.add_argument(
        "artifact_dir",
        type=Path,
        nargs="?",
        help="Directory containing the artifact files to validate.",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Validate the synthetic example files from examples/.",
    )
    args = parser.parse_args(argv)

    if args.examples:
        examples_dir = Path(__file__).resolve().parent.parent / "examples"
        artifact_dir = examples_dir
        label = "synthetic examples"
        sample_names = True
    else:
        artifact_dir = args.artifact_dir
        label = str(artifact_dir)
        sample_names = False

    errors = validate_dir(artifact_dir, sample_names=sample_names)
    if errors:
        print(f"INVALID: {label}")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"VALID: {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

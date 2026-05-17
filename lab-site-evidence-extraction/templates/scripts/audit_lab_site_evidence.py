"""Copyable template to audit lab-site-evidence-extraction artifacts and write lab_site_audit.json.

This template is stdlib-only and does not perform network requests.
For real runs, copy into <run>/tools/ and adapt the audit logic if needed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ALLOWED_EVIDENCE_QUALITY = {
    "research_description", "profile_snippet", "link_text_only", "none",
}

ALLOWED_CLAIM_TYPES = {
    "research_direction", "pi_info", "lab_member",
    "publication_ref", "position_signal", "lab_url",
    "facility", "other",
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def audit(artifact_dir: Path) -> dict[str, Any]:
    plan = read_json(artifact_dir / "lab_site_plan.json", {})
    pages = read_jsonl(artifact_dir / "lab_pages.jsonl")
    evidence = read_jsonl(artifact_dir / "lab_site_evidence.jsonl")

    claim_type_counts = Counter(item.get("claim_type", "unknown") for item in evidence)
    quality_counts = Counter(item.get("evidence_quality", "unknown") for item in evidence)

    pages_fetched = len(pages)
    successful_pages = sum(1 for p in pages if p.get("status_code") == 200)
    evidence_items = len(evidence)
    research_items = claim_type_counts.get("research_direction", 0)
    hiring_items = claim_type_counts.get("position_signal", 0)
    pi_info_items = claim_type_counts.get("pi_info", 0)

    weak_count = quality_counts.get("link_text_only", 0)
    none_count = quality_counts.get("none", 0)
    weak_ratio = round(weak_count / evidence_items, 2) if evidence_items else 0.0

    pi_info_complete = pi_info_items > 0

    blocking: list[str] = []
    warnings: list[str] = []
    repair_hints: list[dict[str, str]] = []

    if not pages:
        blocking.append("No pages were fetched from the lab site.")
    if not evidence:
        blocking.append("No evidence items were extracted.")
    if research_items == 0 and evidence_items > 0:
        blocking.append("No research direction evidence found.")

    hiring_link_text_only = [
        item for item in evidence
        if item.get("claim_type") == "position_signal"
        and item.get("evidence_quality") == "link_text_only"
    ]
    if hiring_link_text_only:
        warnings.append(
            f"{len(hiring_link_text_only)} position signal(s) based on link-text-only evidence; "
            "do not treat as current hiring confirmation."
        )

    if weak_ratio > 0.5 and evidence_items > 0:
        warnings.append(f"High weak evidence ratio: {weak_ratio}")
        repair_hints.append({
            "field": "extraction_focus",
            "suggestion": "Prioritize pages with substantive research descriptions over listing pages.",
        })

    unavailable_items = [
        item for item in evidence
        if item.get("extraction_status") in ("unavailable", "skipped")
    ]
    if unavailable_items:
        warnings.append(
            f"{len(unavailable_items)} evidence item(s) have unavailable/skipped extraction status."
        )

    generic_hiring = [
        item for item in evidence
        if item.get("claim_type") == "position_signal"
        and item.get("evidence_quality") == "link_text_only"
        and any(
            phrase in (item.get("snippet") or "").lower()
            for phrase in ("join our", "join us", "join the", "we are hiring")
        )
    ]
    if generic_hiring:
        warnings.append(
            f"{len(generic_hiring)} position signal(s) use generic join-us language only."
        )
        repair_hints.append({
            "field": "position_signal",
            "suggestion": "Look for specific position descriptions, deadlines, or application instructions before confirming hiring.",
        })

    if not pi_info_complete:
        warnings.append("PI info is missing from extracted evidence.")

    if blocking:
        status = "fail"
    elif warnings:
        status = "partial"
    else:
        status = "pass"

    return {
        "status": status,
        "metrics": {
            "pages_fetched": pages_fetched,
            "successful_pages": successful_pages,
            "evidence_items": evidence_items,
            "research_direction_items": research_items,
            "position_signal_items": hiring_items,
            "pi_info_items": pi_info_items,
            "weak_evidence_ratio": weak_ratio,
            "pi_info_complete": pi_info_complete,
            "quality_counts": dict(quality_counts),
            "claim_type_counts": dict(claim_type_counts),
        },
        "blocking_failures": blocking,
        "warnings": warnings,
        "repair_hints": repair_hints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit lab-site-evidence-extraction artifacts."
    )
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    report = audit(args.artifact_dir)
    write_json(args.artifact_dir / "lab_site_audit.json", report)
    print(f"Audit {report['status']}: wrote {args.artifact_dir / 'lab_site_audit.json'}")
    return 0 if report["status"] in {"pass", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

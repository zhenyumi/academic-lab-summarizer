#!/usr/bin/env python3
"""Check migration-specific policy invariants for academic-lab-summarizer."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [
    "lab-site-evidence-extraction",
    "lab-publication-profile",
    "lab-profile-synthesis",
    "academic-lab-summarizer",
]
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".json", ".jsonl", ".sh"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def check_publication_priority(errors: list[str]) -> None:
    text = read(ROOT / "lab-publication-profile" / "SKILL.md")
    contract = read(ROOT / "lab-publication-profile" / "references" / "publication-profile-contract.md")
    combined = text + "\n" + contract
    required = [
        "OpenAlex",
        "Semantic Scholar",
        "PubMed",
        "Crossref",
        "bioRxiv",
        "medRxiv",
        "arXiv",
        "lab_website",
        "Tier 0",
        "Tier 1",
        "Tier 2",
        "primary_context",
        "publication_search_plan.json",
    ]
    for token in required:
        if token not in combined:
            errors.append(f"publication priority policy missing token: {token}")


def check_position_contract(errors: list[str]) -> None:
    sample_path = ROOT / "lab-profile-synthesis" / "examples" / "position_signals.sample.json"
    data = json.loads(read(sample_path))
    if "signals" not in data:
        errors.append("position_signals.sample.json missing signals")
        return
    for sig in data["signals"]:
        for field in (
            "source_url",
            "snippet",
            "position_category",
            "signal_strength",
            "evidence_refs",
            "confidence",
            "last_observed_or_posted_date",
        ):
            if field not in sig:
                errors.append(f"position signal {sig.get('signal_id', '?')} missing {field}")
        if sig.get("position_category") in {"other", "none"} and sig.get("signal_strength") == "confirmed_opening":
            errors.append("generic/none position category was labeled confirmed_opening")

    report_text = read(ROOT / "lab-profile-synthesis" / "examples" / "report.sample.md")
    for section in (
        "## Position Signals",
        "## Important Recent Publications",
        "## Methods and Approaches",
        "## Funding/Resource Indicators",
        "## Limitations",
    ):
        if section not in report_text:
            errors.append(f"report.sample.md missing required section: {section}")


def check_old_names(errors: list[str]) -> None:
    forbidden = [
        "Postdoc Finder",
        "postdoc-finder",
        "institution-crawl-report",
        "lab-result-curation",
        "postdoc-deep-dive-workflow",
        "lab-postdoc-fit-assessment",
        "reports/finder",
        "reports/deep-dive",
        "deep_dive_manifest",
        "deep_dive_input",
        "postdoc_fit_assessment",
        "postdoc_fit_audit",
    ]
    self_path = Path(__file__).resolve()
    roots = [ROOT / d for d in SCAN_DIRS] + [
        ROOT / "install-common.sh",
        ROOT / "install-codex.sh",
        ROOT / "install-claude.sh",
        ROOT / "install-opencode.sh",
        ROOT / "install-openclaw.sh",
    ]
    for root in roots:
        files = [root] if root.is_file() else list(root.rglob("*"))
        for path in files:
            if path.resolve() == self_path or not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            try:
                text = read(path)
            except UnicodeDecodeError:
                continue
            for token in forbidden:
                if token in text:
                    errors.append(f"old migration name found in {path.relative_to(ROOT)}: {token}")


def main() -> int:
    errors: list[str] = []
    check_publication_priority(errors)
    check_position_contract(errors)
    check_old_names(errors)
    if errors:
        print("INVALID: migration policy")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("VALID: migration policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

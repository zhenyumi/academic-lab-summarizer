#!/usr/bin/env python3
"""Smoke test canonical lab summary report outputs.

Writes only to a temporary directory. Verifies that the report builder creates
report.html, report.md, report_manifest.json, and that the index discovers the
new report manifest under reports/lab-summaries/.
"""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_lab_summary_examples(target_dir: Path) -> None:
    examples = REPO_ROOT / "lab-profile-synthesis" / "examples"
    mapping = {
        "lab_summary_input.sample.json": "lab_summary_input.json",
        "position_signals.sample.json": "position_signals.json",
        "lab_summary_assessment.sample.json": "lab_summary_assessment.json",
        "lab_profile.sample.json": "lab_profile.json",
        "lab_summary_audit.sample.json": "lab_summary_audit.json",
        "report.sample.md": "report.md",
        "lab_site_evidence.sample.jsonl": "lab_site_evidence.jsonl",
        "publications.curated.sample.json": "publications.curated.json",
        "publication_evidence.sample.jsonl": "publication_evidence.jsonl",
        "research_theme_profile.sample.json": "research_theme_profile.json",
        "publication_candidates.sample.jsonl": "publication_candidates.jsonl",
    }
    target_dir.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in mapping.items():
        shutil.copy2(examples / src_name, target_dir / dst_name)
    shutil.copy2(
        REPO_ROOT / "lab-site-evidence-extraction" / "examples" / "lab_site_audit.sample.json",
        target_dir / "lab_site_audit.json",
    )
    shutil.copy2(
        REPO_ROOT / "lab-publication-profile" / "examples" / "publication_audit.sample.json",
        target_dir / "publication_audit.json",
    )
    shutil.copy2(
        REPO_ROOT / "academic-lab-summarizer" / "examples" / "lab_summary_manifest.sample.json",
        target_dir / "lab_summary_manifest.json",
    )


def require(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"Missing expected path: {path}")


def main() -> int:
    report_builder = load_module(
        REPO_ROOT / "lab-profile-synthesis" / "templates" / "scripts" / "build_lab_summary_html.py",
        "build_lab_summary_html",
    )
    index_builder = load_module(
        REPO_ROOT / "academic-lab-summarizer" / "templates" / "scripts" / "build_report_index.py",
        "build_report_index",
    )

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        summary_dir = workspace / "lab_summaries" / "example-lab-001"
        copy_lab_summary_examples(summary_dir)

        report_dir = report_builder.build(summary_dir)
        require(report_dir / "report.html")
        require(report_dir / "report.md")
        require(report_dir / "report_manifest.json")
        require(report_dir / "artifacts" / "lab_profile.json")

        html_text = (report_dir / "report.html").read_text(encoding="utf-8")
        if 'class="pi-author"' not in html_text:
            raise AssertionError("Report HTML missing PI author highlight (.pi-author)")
        if 'class="pub-authors"' not in html_text:
            raise AssertionError("Report HTML missing publication authors (.pub-authors)")
        if "all-publications" not in html_text:
            raise AssertionError("Report HTML missing all-publications section")

        tiered_dir = workspace / "lab_summaries" / "example-lab-tiered"
        copy_lab_summary_examples(tiered_dir)
        tiered_src = REPO_ROOT / "lab-profile-synthesis" / "examples" / "publications.curated.tiered.sample.json"
        shutil.copy2(tiered_src, tiered_dir / "publications.curated.json")

        tiered_report_dir = report_builder.build(tiered_dir)
        require(tiered_report_dir / "report.html")
        tiered_html = (tiered_report_dir / "report.html").read_text(encoding="utf-8")
        if 'class="pi-author"' not in tiered_html:
            raise AssertionError("Tiered-curated report HTML missing PI author highlight")
        if "all-publications" not in tiered_html:
            raise AssertionError("Tiered-curated report HTML missing all-publications section")

        reports_dir = index_builder.build(workspace)
        require(reports_dir / "index.html")
        index_text = (reports_dir / "index.html").read_text(encoding="utf-8")
        if "Doe Neural Development Lab" not in index_text:
            raise AssertionError("Report index did not include generated lab summary report")

    print("VALID: lab summary report output smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

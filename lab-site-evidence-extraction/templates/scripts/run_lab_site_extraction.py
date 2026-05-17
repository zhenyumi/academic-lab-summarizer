"""Copyable template to run lab-site-evidence-extraction from synthetic fixtures or real HTML.

This template is stdlib-only and does not perform network requests.
For real runs, copy into <run>/tools/ and adapt the crawl logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_lab_site_plan(input_data: dict[str, Any]) -> dict[str, Any]:
    lab_url = input_data.get("lab_url", "")
    parsed = urlparse(lab_url)
    domain = parsed.netloc.lower().removeprefix("www.")
    return {
        "lab_url": lab_url,
        "allowed_domains": [domain] if domain else [],
        "entry_urls": [lab_url] if lab_url else [],
        "crawl_limits": {
            "max_pages": 30,
            "max_depth": 2,
            "request_delay_seconds": 0.5,
        },
        "extraction_focus": [
            "research_direction",
            "pi_info",
            "lab_member",
            "publication_ref",
            "position_signal",
        ],
        "known_risks": [],
    }


def extract_from_fixtures(
    fixture_dir: Path,
    input_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    lab_id = input_data.get("lab_id", "unknown")
    page_id = 0

    fixture_pages_path = fixture_dir / "lab_pages.jsonl"
    if not fixture_pages_path.exists():
        fixture_pages_path = fixture_dir / "lab_pages.sample.jsonl"
    fixture_evidence_path = fixture_dir / "lab_site_evidence.jsonl"
    if not fixture_evidence_path.exists():
        fixture_evidence_path = fixture_dir / "lab_site_evidence.sample.jsonl"

    fixture_pages = read_jsonl(fixture_pages_path)
    fixture_evidence = read_jsonl(fixture_evidence_path)

    for fp in fixture_pages:
        page_id += 1
        pages.append({
            "page_id": page_id,
            "url": fp.get("url", ""),
            "depth": fp.get("depth", 0),
            "status_code": fp.get("status_code", 200),
            "title": fp.get("title", ""),
            "text_length": fp.get("text_length", 0),
            "links": fp.get("links", []),
            "fetched_at": fp.get("fetched_at", ""),
        })

    for i, fe in enumerate(fixture_evidence, 1):
        evidence.append({
            "evidence_id": i,
            "lab_id": lab_id,
            "source_url": fe.get("source_url", ""),
            "snippet": fe.get("snippet", ""),
            "claim_type": fe.get("claim_type", "other"),
            "evidence_quality": fe.get("evidence_quality", "none"),
            "extraction_status": fe.get("extraction_status", "skipped"),
            "confidence": fe.get("confidence", "unknown"),
        })

    return pages, evidence


def run(input_path: Path, output_dir: Path, fixture_dir: Path | None = None) -> None:
    input_data = read_json(input_path, {})
    plan = build_lab_site_plan(input_data)
    write_json(output_dir / "lab_site_plan.json", plan)

    if fixture_dir is not None:
        pages, evidence = extract_from_fixtures(fixture_dir, input_data)
    else:
        pages = []
        evidence = []

    write_jsonl(output_dir / "lab_pages.jsonl", pages)
    write_jsonl(output_dir / "lab_site_evidence.jsonl", evidence)

    print(f"Wrote {len(pages)} pages and {len(evidence)} evidence items to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run lab-site-evidence-extraction from synthetic fixtures or HTML."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to lab_summary_input.json.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for artifacts.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Directory with synthetic fixture files (lab_pages.jsonl, lab_site_evidence.jsonl).",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    run(args.input, args.out, args.fixtures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

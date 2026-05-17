"""Copyable template to audit lab-publication-profile artifacts and write publication_audit.json.

This template is stdlib-only and does not perform network requests.
For real runs, copy into <run>/tools/ and adapt the audit logic if needed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


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


_FALLBACK_SOURCE_META: dict[str, dict[str, Any]] = {
    "lab_website": {"tier": 0, "role": "primary_context"},
    "openalex": {"tier": 1, "role": "primary"},
    "semantic_scholar": {"tier": 1, "role": "supplementary"},
    "pubmed": {"tier": 1, "role": "conditional_primary"},
}


def audit(artifact_dir: Path) -> dict[str, Any]:
    plan = read_json(artifact_dir / "publication_search_plan.json", {})
    candidates = read_jsonl(artifact_dir / "publication_candidates.jsonl")
    curated = read_json(artifact_dir / "publications.curated.json", {})
    pub_evidence = read_jsonl(artifact_dir / "publication_evidence.jsonl")
    themes = read_json(artifact_dir / "research_theme_profile.json", {})

    tier_counts = curated.get("tier_counts", {})
    confirmed = tier_counts.get("confirmed", 0)
    likely = tier_counts.get("likely", 0)
    ambiguous = tier_counts.get("ambiguous", 0)
    rejected = tier_counts.get("rejected", 0)

    source_db_counts = Counter(c.get("source_db", "unknown") for c in candidates)
    pub_type_counts = Counter(c.get("publication_type", "unknown") for c in candidates)
    distinct_sources = sorted(source_db_counts.keys())

    sources_returning = [s for s in distinct_sources if source_db_counts.get(s, 0) > 0]
    plan_sources = {s.get("source") for s in plan.get("search_sources", []) if isinstance(s, dict)}
    sources_no_results = sorted(plan_sources - set(sources_returning))

    candidate_provenance_ok = sum(
        1 for c in candidates
        if c.get("source_db") and c.get("source_id")
        and (c.get("source_url") or c.get("doi"))
    )
    evidence_provenance_ok = sum(
        1 for e in pub_evidence
        if e.get("evidence_id") and e.get("source_url") and e.get("evidence_type")
    )

    prov_ratio = round(candidate_provenance_ok / len(candidates), 2) if candidates else 0.0
    ev_prov_ratio = round(evidence_provenance_ok / len(pub_evidence), 2) if pub_evidence else 0.0
    confirmed_likely_ratio = round((confirmed + likely) / len(candidates), 2) if candidates else 0.0

    sufficient = confirmed >= 1 or likely >= 2
    tier1_sufficient = sufficient

    source_status = read_json(artifact_dir / "publication_audit.json", {}).get("source_status", {})
    if not source_status:
        sources_list = []
        for source, count in source_db_counts.items():
            meta = _FALLBACK_SOURCE_META.get(source, {"tier": 2, "role": "supplementary"})
            sources_list.append({
                "source": source, "tier": meta["tier"], "role": meta["role"],
                "activated": True, "activation_reason": "default",
                "outcome": "found_sufficient" if count > 0 else "no_results",
                "candidates": count,
            })
        tier0_available = any(
            s["source"] == "lab_website" and s["activated"] for s in sources_list
        )
        tier1_has_results = any(
            s["source"] != "lab_website" and s["tier"] == 1 and s.get("candidates", 0) > 0
            for s in sources_list
        )
        if tier0_available and tier1_sufficient:
            stop_reason = "tier0_plus_tier1_sufficient" if tier1_has_results else "tier0_sufficient"
        elif tier1_sufficient:
            stop_reason = "tier1_sufficient"
        else:
            stop_reason = "insufficient_tier1"
        source_status = {
            "tier0_available": tier0_available,
            "tier1_sufficient": tier1_sufficient,
            "tier2_attempted": not tier1_sufficient,
            "stop_reason": stop_reason,
            "sources": sources_list,
        }

    blocking: list[str] = []
    warnings: list[str] = []
    repair_hints: list[dict[str, str]] = []

    if not candidates:
        blocking.append("No publication candidates found from any source.")
    if confirmed == 0 and likely == 0:
        blocking.append("No confirmed or likely publications found.")
    if ambiguous > 0:
        warnings.append(
            f"{ambiguous} ambiguous publication(s) excluded from research summaries."
        )
    if not sufficient:
        warnings.append(
            "Tier 1 sources produced insufficient confirmed/likely publications. "
            "Consider activating Tier 2 sources."
        )
        repair_hints.append({
            "field": "source_tier",
            "suggestion": "Activate Tier 2 sources (Crossref, preprint servers) to resolve ambiguous candidates.",
        })

    bio = plan.get("biomedical_relevant", False)
    if bio and "pubmed" not in sources_returning:
        warnings.append("PubMed returned 0 candidates for this biomedical lab.")

    if pub_type_counts.get("unknown", 0) > 0:
        warnings.append(
            f"{pub_type_counts['unknown']} candidate(s) have unknown publication type."
        )

    status = "fail" if blocking else ("partial" if warnings else "pass")

    return {
        "status": status,
        "metrics": {
            "total_candidates": len(candidates),
            "confirmed": confirmed,
            "likely": likely,
            "ambiguous": ambiguous,
            "rejected": rejected,
            "peer_reviewed": pub_type_counts.get("peer_reviewed", 0),
            "preprint": pub_type_counts.get("preprint", 0),
            "unknown_type": pub_type_counts.get("unknown", 0),
            "sources_used": distinct_sources,
            "sources_returning_results": sources_returning,
            "sources_returning_no_results": sources_no_results,
            "provenance_complete_ratio": prov_ratio,
            "evidence_provenance_complete_ratio": ev_prov_ratio,
            "confirmed_likely_ratio": confirmed_likely_ratio,
            "sufficient": sufficient,
        },
        "source_status": source_status,
        "blocking_failures": blocking,
        "warnings": warnings,
        "repair_hints": repair_hints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit lab-publication-profile artifacts."
    )
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    report = audit(args.artifact_dir)
    write_json(args.artifact_dir / "publication_audit.json", report)
    print(f"Audit {report['status']}: wrote {args.artifact_dir / 'publication_audit.json'}")
    return 0 if report["status"] in {"pass", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

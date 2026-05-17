#!/usr/bin/env python3
"""Validate lab-publication-profile artifacts.

Checks publication_search_plan.json, publication_candidates.jsonl,
publications.curated.json, publication_evidence.jsonl, publication_audit.json,
and research_theme_profile.json against the contract.
No network calls, no file mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_DB = {
    "openalex", "semantic_scholar", "pubmed", "crossref",
    "arxiv", "biorxiv", "medrxiv", "lab_website",
}

ALLOWED_PUBLICATION_TYPE = {"peer_reviewed", "preprint", "unknown"}

ALLOWED_MATCH_TIER = {"confirmed", "likely", "ambiguous", "rejected"}

ALLOWED_AFFILIATION_MATCH = {"confirmed", "likely", "unknown", "partial"}

ALLOWED_EVIDENCE_TYPE = {
    "affiliation_match", "topic_overlap", "coauthor_overlap",
    "lab_page_overlap", "doi_match", "ambiguous_name_match", "other",
}

ALLOWED_SOURCE_ROLE = {"primary", "supplementary", "conditional_primary", "verification", "primary_context"}

ALLOWED_SOURCE_TIER = {0, 1, 2}

ALLOWED_OUTCOME = {
    "found_sufficient", "found_insufficient", "no_results",
    "error", "skipped", "not_activated",
}

ALLOWED_AUDIT_STATUS = {"pass", "partial", "fail"}

ALLOWED_STOP_REASON = {
    "tier0_sufficient", "tier0_plus_tier1_sufficient", "tier1_sufficient",
    "insufficient_tier1",
    "tier1_plus_tier2_sufficient", "tier1_plus_tier2_insufficient",
    "all_tiers_insufficient",
}


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


def _validate_search_plan(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["publication_search_plan.json must be a JSON object."]
    for field in ("lab_name", "pi_name", "institution", "search_sources"):
        if field not in data:
            errors.append(f"publication_search_plan.json missing required field: {field}")
    sources = data.get("search_sources")
    if not isinstance(sources, list):
        errors.append("publication_search_plan.json search_sources must be a list.")
        return errors
    for i, src in enumerate(sources):
        label = f"publication_search_plan.json search_sources[{i}]"
        for field in ("source", "tier", "role", "rationale"):
            if field not in src:
                errors.append(f"{label} missing required field: {field}")
        if src.get("tier") not in ALLOWED_SOURCE_TIER:
            errors.append(f"{label} invalid tier: {src.get('tier')}")
        if src.get("role") not in ALLOWED_SOURCE_ROLE:
            errors.append(f"{label} invalid role: {src.get('role')}")
    tier0_sources = {s["source"] for s in sources if s.get("tier") == 0 and "source" in s}
    tier1_sources = {s["source"] for s in sources if s.get("tier") == 1 and "source" in s}
    tier2_sources = {s["source"] for s in sources if s.get("tier") == 2 and "source" in s}
    if not tier1_sources:
        errors.append("publication_search_plan.json must have at least one tier 1 source.")
    for s in sources:
        if s.get("tier") == 0 and s.get("role") != "primary_context":
            errors.append(
                f"publication_search_plan.json: tier 0 source {s.get('source')} must have role 'primary_context'."
            )
    if data.get("biomedical_relevant") and "pubmed" not in tier1_sources:
        errors.append(
            "publication_search_plan.json: biomedical_relevant=true but PubMed not in tier 1 sources."
        )
    return errors


def _validate_candidates(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[int] = set()
    for i, row in enumerate(rows):
        label = f"publication_candidates.jsonl row {i + 1}"
        for field in ("candidate_id", "title", "authors", "year", "source_db",
                      "source_id", "publication_type", "match_evidence"):
            if field not in row:
                errors.append(f"{label} missing required field: {field}")
        cid = row.get("candidate_id")
        if isinstance(cid, int):
            if cid in seen_ids:
                errors.append(f"{label} duplicate candidate_id: {cid}")
            seen_ids.add(cid)
        if row.get("source_db") and row["source_db"] not in ALLOWED_SOURCE_DB:
            errors.append(f"{label} invalid source_db: {row['source_db']}")
        if row.get("publication_type") and row["publication_type"] not in ALLOWED_PUBLICATION_TYPE:
            errors.append(f"{label} invalid publication_type: {row['publication_type']}")
        if "authors" in row and not isinstance(row["authors"], list):
            errors.append(f"{label} authors must be a list.")
        me = row.get("match_evidence")
        if isinstance(me, dict):
            if "affiliation_match" in me and me["affiliation_match"] not in ALLOWED_AFFILIATION_MATCH:
                errors.append(
                    f"{label} match_evidence.affiliation_match invalid: {me['affiliation_match']}"
                )
        elif me is not None:
            errors.append(f"{label} match_evidence must be an object.")
    return errors


def _validate_curated(data: Any, candidates: list[dict[str, Any]] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["publications.curated.json must be a JSON object."]
    for field in ("lab_id", "publications", "tier_counts"):
        if field not in data:
            errors.append(f"publications.curated.json missing required field: {field}")
    pubs = data.get("publications")
    if not isinstance(pubs, list):
        errors.append("publications.curated.json publications must be a list.")
        return errors
    seen_ids: set[int] = set()
    for i, pub in enumerate(pubs):
        label = f"publications.curated.json publications[{i}]"
        for field in ("candidate_id", "title", "authors", "year", "match_tier",
                      "match_rationale", "source_db"):
            if field not in pub:
                errors.append(f"{label} missing required field: {field}")
        cid = pub.get("candidate_id")
        if isinstance(cid, int):
            if cid in seen_ids:
                errors.append(f"{label} duplicate candidate_id in curated: {cid}")
            seen_ids.add(cid)
        if pub.get("match_tier") and pub["match_tier"] not in ALLOWED_MATCH_TIER:
            errors.append(f"{label} invalid match_tier: {pub['match_tier']}")
        if pub.get("source_db") and pub["source_db"] not in ALLOWED_SOURCE_DB:
            errors.append(f"{label} invalid source_db: {pub['source_db']}")
    tier_counts = data.get("tier_counts")
    if isinstance(tier_counts, dict):
        for tier in ("confirmed", "likely", "ambiguous", "rejected"):
            if tier not in tier_counts:
                errors.append(f"publications.curated.json tier_counts missing key: {tier}")
        actual_counts: dict[str, int] = {}
        for pub in pubs:
            t = pub.get("match_tier", "unknown")
            actual_counts[t] = actual_counts.get(t, 0) + 1
        for tier in ("confirmed", "likely", "ambiguous", "rejected"):
            expected = tier_counts.get(tier, 0)
            actual = actual_counts.get(tier, 0)
            if expected != actual:
                errors.append(
                    f"publications.curated.json tier_counts.{tier}={expected} "
                    f"but actual count is {actual}"
                )
    return errors


def _validate_evidence(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[int] = set()
    for i, row in enumerate(rows):
        label = f"publication_evidence.jsonl row {i + 1}"
        for field in ("evidence_id", "lab_id", "candidate_id", "evidence_type",
                      "description", "source_url"):
            if field not in row:
                errors.append(f"{label} missing required field: {field}")
        eid = row.get("evidence_id")
        if isinstance(eid, int):
            if eid in seen_ids:
                errors.append(f"{label} duplicate evidence_id: {eid}")
            seen_ids.add(eid)
        if row.get("evidence_type") and row["evidence_type"] not in ALLOWED_EVIDENCE_TYPE:
            errors.append(f"{label} invalid evidence_type: {row['evidence_type']}")
    return errors


def _validate_audit(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["publication_audit.json must be a JSON object."]
    for field in ("status", "metrics", "source_status", "blocking_failures", "warnings"):
        if field not in data:
            errors.append(f"publication_audit.json missing required field: {field}")
    if data.get("status") and data["status"] not in ALLOWED_AUDIT_STATUS:
        errors.append(f"publication_audit.json invalid status: {data['status']}")
    if "blocking_failures" in data and not isinstance(data["blocking_failures"], list):
        errors.append("publication_audit.json blocking_failures must be a list.")
    if "warnings" in data and not isinstance(data["warnings"], list):
        errors.append("publication_audit.json warnings must be a list.")
    ss = data.get("source_status")
    if isinstance(ss, dict):
        for field in ("tier0_available", "tier1_sufficient", "tier2_attempted", "stop_reason", "sources"):
            if field not in ss:
                errors.append(f"publication_audit.json source_status missing field: {field}")
        if ss.get("stop_reason") and ss["stop_reason"] not in ALLOWED_STOP_REASON:
            errors.append(f"publication_audit.json source_status invalid stop_reason: {ss['stop_reason']}")
        sources = ss.get("sources")
        if isinstance(sources, list):
            for i, src in enumerate(sources):
                label = f"publication_audit.json source_status.sources[{i}]"
                for field in ("source", "tier", "role", "activated", "outcome"):
                    if field not in src:
                        errors.append(f"{label} missing required field: {field}")
                if src.get("tier") not in ALLOWED_SOURCE_TIER:
                    errors.append(f"{label} invalid tier: {src.get('tier')}")
                if src.get("role") and src["role"] not in ALLOWED_SOURCE_ROLE:
                    errors.append(f"{label} invalid role: {src['role']}")
                if src.get("outcome") and src["outcome"] not in ALLOWED_OUTCOME:
                    errors.append(f"{label} invalid outcome: {src['outcome']}")
    return errors


def _validate_themes(data: Any, curated: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["research_theme_profile.json must be a JSON object."]
    for field in ("lab_id", "research_themes", "peer_reviewed_publication_count",
                  "preprint_count", "ambiguous_excluded_count"):
        if field not in data:
            errors.append(f"research_theme_profile.json missing required field: {field}")
    themes = data.get("research_themes")
    if not isinstance(themes, list):
        errors.append("research_theme_profile.json research_themes must be a list.")
        return errors
    for i, theme in enumerate(themes):
        label = f"research_theme_profile.json research_themes[{i}]"
        for field in ("theme_id", "name", "description", "supporting_publications", "confidence"):
            if field not in theme:
                errors.append(f"{label} missing required field: {field}")
        pubs_ref = theme.get("supporting_publications")
        if isinstance(pubs_ref, list) and not all(isinstance(p, int) for p in pubs_ref):
            errors.append(f"{label} supporting_publications must be a list of integer candidate IDs.")
    if curated and isinstance(curated.get("publications"), list):
        pub_ids = {p.get("candidate_id") for p in curated["publications"] if isinstance(p.get("candidate_id"), int)}
        ambiguous_ids = {
            p.get("candidate_id") for p in curated["publications"]
            if p.get("match_tier") == "ambiguous" and isinstance(p.get("candidate_id"), int)
        }
        rejected_ids = {
            p.get("candidate_id") for p in curated["publications"]
            if p.get("match_tier") == "rejected" and isinstance(p.get("candidate_id"), int)
        }
        all_theme_pub_ids: set[int] = set()
        for theme in themes:
            for pid in theme.get("supporting_publications", []):
                all_theme_pub_ids.add(pid)
                if pid in ambiguous_ids:
                    errors.append(
                        f"research_theme_profile.json: ambiguous candidate {pid} "
                        "used in theme supporting_publications."
                    )
                if pid in rejected_ids:
                    errors.append(
                        f"research_theme_profile.json: rejected candidate {pid} "
                        "used in theme supporting_publications."
                    )
                if pid not in pub_ids:
                    errors.append(
                        f"research_theme_profile.json: candidate {pid} "
                        "in theme but not in curated publications."
                    )
        excluded = data.get("ambiguous_publications_excluded")
        if isinstance(excluded, list):
            for pid in excluded:
                if pid not in ambiguous_ids:
                    errors.append(
                        f"research_theme_profile.json: ambiguous_publications_excluded "
                        f"contains {pid} but it is not ambiguous in curated."
                    )
    return errors


SAMPLE_NAME_MAP = {
    "publication_search_plan.json": "publication_search_plan.sample.json",
    "publication_candidates.jsonl": "publication_candidates.sample.jsonl",
    "publications.curated.json": "publications.curated.sample.json",
    "publication_evidence.jsonl": "publication_evidence.sample.jsonl",
    "publication_audit.json": "publication_audit.sample.json",
    "research_theme_profile.json": "research_theme_profile.sample.json",
}


def validate_dir(artifact_dir: Path, sample_names: bool = False) -> list[str]:
    errors: list[str] = []

    search_plan_path = artifact_dir / (
        SAMPLE_NAME_MAP["publication_search_plan.json"]
        if sample_names else "publication_search_plan.json"
    )
    plan_data, read_errors = _load_json(search_plan_path)
    errors.extend(read_errors)
    if plan_data is not None:
        errors.extend(_validate_search_plan(plan_data))

    candidates_path = artifact_dir / (
        SAMPLE_NAME_MAP["publication_candidates.jsonl"]
        if sample_names else "publication_candidates.jsonl"
    )
    candidates, read_errors = _load_jsonl(candidates_path)
    errors.extend(read_errors)
    if candidates:
        errors.extend(_validate_candidates(candidates))

    curated_path = artifact_dir / (
        SAMPLE_NAME_MAP["publications.curated.json"]
        if sample_names else "publications.curated.json"
    )
    curated_data, read_errors = _load_json(curated_path)
    errors.extend(read_errors)
    if curated_data is not None:
        errors.extend(_validate_curated(curated_data, candidates if candidates else None))

    evidence_path = artifact_dir / (
        SAMPLE_NAME_MAP["publication_evidence.jsonl"]
        if sample_names else "publication_evidence.jsonl"
    )
    evidence_rows, read_errors = _load_jsonl(evidence_path)
    errors.extend(read_errors)
    if evidence_rows:
        errors.extend(_validate_evidence(evidence_rows))

    audit_path = artifact_dir / (
        SAMPLE_NAME_MAP["publication_audit.json"]
        if sample_names else "publication_audit.json"
    )
    audit_data, read_errors = _load_json(audit_path)
    errors.extend(read_errors)
    if audit_data is not None:
        errors.extend(_validate_audit(audit_data))

    themes_path = artifact_dir / (
        SAMPLE_NAME_MAP["research_theme_profile.json"]
        if sample_names else "research_theme_profile.json"
    )
    themes_data, read_errors = _load_json(themes_path)
    errors.extend(read_errors)
    if themes_data is not None:
        errors.extend(_validate_themes(themes_data, curated_data))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate lab-publication-profile artifacts."
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

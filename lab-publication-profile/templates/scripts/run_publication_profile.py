"""Copyable template to run lab-publication-profile from synthetic fixtures or real API adapters.

This template is stdlib-only and does not perform network requests.
For real runs, copy into <run>/tools/ and add source adapters for OpenAlex,
Semantic Scholar, PubMed, Crossref, etc. using the same output schema.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_TIERS: dict[str, dict[str, Any]] = {
    "openalex": {"tier": 1, "role": "primary", "always_activate": True},
    "semantic_scholar": {"tier": 1, "role": "supplementary", "always_activate": True},
    "pubmed": {"tier": 1, "role": "conditional_primary", "always_activate": False, "requires": "biomedical_relevant"},
    "crossref": {"tier": 2, "role": "verification", "always_activate": False},
    "arxiv": {"tier": 2, "role": "supplementary", "always_activate": False},
    "biorxiv": {"tier": 2, "role": "supplementary", "always_activate": False},
    "medrxiv": {"tier": 2, "role": "supplementary", "always_activate": False},
    "lab_website": {"tier": 0, "role": "primary_context", "always_activate": False, "requires": "publication_ref_in_site_evidence"},
}


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


def build_search_plan(input_data: dict[str, Any]) -> dict[str, Any]:
    lab_name = input_data.get("lab_name", "")
    pi_name = input_data.get("pi_name", "")
    institution = input_data.get("institution", "")
    biomedical = input_data.get("biomedical_relevant", False)
    year_range = [2020, 2026]

    sources = []
    for source, meta in SOURCE_TIERS.items():
        if meta["tier"] == 0:
            sources.append({
                "source": source, "tier": 0, "role": meta["role"],
                "rationale": "Lab site evidence contains publication references; PI-curated publication list provides authoritative attribution.",
            })
        elif meta["tier"] == 1 and meta.get("always_activate"):
            sources.append({
                "source": source, "tier": 1, "role": meta["role"],
                "rationale": "Default primary search source.",
            })
        elif meta["tier"] == 1 and meta.get("requires") == "biomedical_relevant" and biomedical:
            sources.append({
                "source": source, "tier": 1, "role": meta["role"],
                "rationale": "Biomedical lab; PubMed is required.",
            })
        elif meta["tier"] == 2:
            sources.append({
                "source": source, "tier": 2, "role": meta["role"],
                "rationale": "Tier 2; activated if Tier 1 insufficient.",
            })

    return {
        "lab_name": lab_name,
        "pi_name": pi_name,
        "institution": institution,
        "biomedical_relevant": biomedical,
        "year_range": year_range,
        "search_sources": sources,
        "excluded_sources": [
            {"source": "google_scholar", "reason": "Not recommended as automated primary source."}
        ],
    }


def _source_tier(source_db: str) -> int:
    return SOURCE_TIERS.get(source_db, {}).get("tier", 2)


def _tier1_sufficient(confirmed: int, likely: int) -> bool:
    return confirmed >= 1 or likely >= 2


def _build_source_status(
    source_db_counts: dict[str, int],
    tier1_sufficient: bool,
    tier2_attempted: bool,
    biomedical: bool,
) -> dict[str, Any]:
    tier0_activated = source_db_counts.get("lab_website", 0) > 0
    sources = []
    for source, meta in SOURCE_TIERS.items():
        tier = meta["tier"]
        role = meta["role"]
        count = source_db_counts.get(source, 0)
        activated = False
        activation_reason = "not_activated"
        outcome = "skipped"

        if tier == 0:
            activated = tier0_activated
            activation_reason = "publication_ref_in_site_evidence" if tier0_activated else "no_publication_ref"
            if tier0_activated:
                outcome = "found_sufficient" if count > 0 else "no_results"
            else:
                outcome = "skipped"
        elif tier == 1:
            if meta.get("always_activate"):
                activated = True
                activation_reason = "default"
            elif meta.get("requires") == "biomedical_relevant" and biomedical:
                activated = True
                activation_reason = "biomedical_relevant"
            if activated:
                outcome = "found_sufficient" if count > 0 else "no_results"
        elif tier == 2 and tier2_attempted:
            activated = True
            activation_reason = "tier1_insufficient"
            outcome = "found_sufficient" if count > 0 else "no_results"

        sources.append({
            "source": source, "tier": tier, "role": role,
            "activated": activated, "activation_reason": activation_reason,
            "outcome": outcome, "candidates": count,
        })

    tier1_has_results = any(
        source_db_counts.get(s, 0) > 0
        for s, m in SOURCE_TIERS.items()
        if m["tier"] == 1
        and (m.get("always_activate") or (m.get("requires") == "biomedical_relevant" and biomedical))
    )
    if tier0_activated and tier1_sufficient:
        stop_reason = "tier0_plus_tier1_sufficient" if tier1_has_results else "tier0_sufficient"
    elif tier1_sufficient:
        stop_reason = "tier1_sufficient"
    elif tier2_attempted:
        stop_reason = "tier1_plus_tier2_sufficient"
    else:
        stop_reason = "insufficient_tier1"

    return {
        "tier0_available": tier0_activated,
        "tier1_sufficient": tier1_sufficient,
        "tier2_attempted": tier2_attempted,
        "stop_reason": stop_reason,
        "sources": sources,
    }


def _human_readable_rationale(candidate: dict[str, Any]) -> str:
    me = candidate.get("match_evidence", {})
    parts = []
    pi_match = me.get("pi_name_match")
    if pi_match in ("confirmed", "partial"):
        parts.append(f"PI name {pi_match} as author")
    aff_match = me.get("affiliation_match")
    if aff_match in ("confirmed", "likely"):
        parts.append(f"affiliation {aff_match}")
    if me.get("topic_overlap"):
        parts.append("topic overlaps with lab research")
    if not parts:
        return "Match evidence insufficient for confident classification."
    return "; ".join(parts) + "."


TOPIC_KEYWORDS: dict[str, list[str]] = {
    "neurogenesis_stem_cells": [
        "neurogenesis", "neural stem", "neural precursor", "hippocampal precursor",
        "neurosphere", "neural progenitor", "adult brain", "neuron production",
    ],
    "exercise_cognition_ageing": [
        "exercise", "fitness", "cardiorespiratory", "ageing", "aging", "cognition",
        "cognitive", "older adults", "physical activity", "sport",
    ],
    "platelet_immune_factors": [
        "platelet", "cxcl", "extracellular vesicle", "exerkine", "xcl1",
        "neutrophil", "immune", "blood-brain", "crosstalk",
    ],
    "neurodegeneration_disease": [
        "alzheimer", "dementia", "neurodegenerat", "ferroptosis", "stroke",
        "motor neurone", "disease", "cognitive decline", "neuroprotect",
    ],
    "molecular_mechanisms": [
        "selenium", "muscarinic", "receptor", "signaling", "pathway",
        "molecular", "mechanism", "method", "culture", "isolation",
    ],
}


def _classify_pub_topic(candidate: dict[str, Any]) -> str:
    text = (candidate.get("title", "") + " " + candidate.get("abstract", "")).lower()
    best_topic = "other_research"
    best_score = 0
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic if best_score > 0 else "other_research"


def _match_site_evidence_to_topics(
    site_evidence: list[dict[str, Any]],
) -> dict[str, list[int]]:
    topic_to_site_ids: dict[str, list[int]] = {}
    for ev in site_evidence:
        if ev.get("claim_type") != "research_direction":
            continue
        snippet = ev.get("snippet", "")
        if not snippet:
            continue
        pseudo = {"title": snippet, "abstract": ""}
        topic = _classify_pub_topic(pseudo)
        ev_id = ev.get("evidence_id")
        if isinstance(ev_id, int):
            topic_to_site_ids.setdefault(topic, []).append(ev_id)
    return topic_to_site_ids


def build_curated_and_themes(
    candidates: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    input_data: dict[str, Any],
    site_evidence: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    lab_id = input_data.get("lab_id", "unknown")
    tier_counts = {"confirmed": 0, "likely": 0, "ambiguous": 0, "rejected": 0}

    for c in candidates:
        me = c.get("match_evidence", {})
        tier = "ambiguous"
        if me.get("affiliation_match") == "confirmed" and me.get("topic_overlap"):
            tier = "confirmed"
        elif me.get("affiliation_match") in ("confirmed", "likely") or me.get("topic_overlap"):
            tier = "likely"
        elif me.get("pi_name_match") == "partial" or me.get("affiliation_match") == "unknown":
            tier = "ambiguous"
        c["_derived_tier"] = tier
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    curated_pubs = []
    for c in candidates:
        curated_pubs.append({
            "candidate_id": c.get("candidate_id"),
            "title": c.get("title", ""),
            "authors": c.get("authors", []),
            "year": c.get("year"),
            "doi": c.get("doi"),
            "venue": c.get("venue"),
            "abstract": c.get("abstract", ""),
            "publication_type": c.get("publication_type", "unknown"),
            "match_tier": c.get("_derived_tier", "ambiguous"),
            "match_rationale": _human_readable_rationale(c),
            "source_db": c.get("source_db", "unknown"),
        })

    curated = {"lab_id": lab_id, "publications": curated_pubs, "tier_counts": tier_counts}

    confirmed_likely = [c for c in candidates if c.get("_derived_tier") in ("confirmed", "likely")]
    ambiguous = [c for c in candidates if c.get("_derived_tier") == "ambiguous"]
    peer_reviewed_count = sum(1 for c in confirmed_likely if c.get("publication_type") == "peer_reviewed")
    preprint_count = sum(1 for c in confirmed_likely if c.get("publication_type") == "preprint")
    insufficient = tier_counts["confirmed"] == 0 and tier_counts["likely"] < 2

    TOPIC_DISPLAY: dict[str, tuple[str, str]] = {
        "neurogenesis_stem_cells": (
            "Adult neurogenesis and neural stem cells",
            "Research on mechanisms governing adult hippocampal neurogenesis and neural precursor cell regulation.",
        ),
        "exercise_cognition_ageing": (
            "Exercise, cognition, and ageing",
            "Studies on exercise-induced neuroprotection, cardiorespiratory fitness, and cognitive function in ageing.",
        ),
        "platelet_immune_factors": (
            "Platelet and immune signaling in brain health",
            "Investigations of platelet-derived factors, extracellular vesicles, and immune crosstalk affecting neurogenesis.",
        ),
        "neurodegeneration_disease": (
            "Neurodegeneration and disease mechanisms",
            "Research on ferroptosis, Alzheimer's disease, and neuroprotective strategies.",
        ),
        "molecular_mechanisms": (
            "Molecular mechanisms and methods",
            "Studies on molecular pathways (selenium, muscarinic receptors) and experimental methods for neural cell research.",
        ),
        "other_research": (
            "Other research directions",
            "Publications not matching primary topic clusters.",
        ),
    }

    topic_groups: dict[str, list[int]] = {}
    for c in confirmed_likely:
        topic = _classify_pub_topic(c)
        topic_groups.setdefault(topic, []).append(c.get("candidate_id"))

    site_topic_map = _match_site_evidence_to_topics(site_evidence or [])

    themes = []
    if confirmed_likely:
        if len(topic_groups) <= 1 or len(confirmed_likely) < 3:
            site_ids_all = sorted({sid for ids in site_topic_map.values() for sid in ids})
            themes.append({
                "theme_id": 1,
                "name": "Lab research directions",
                "description": "Derived from confirmed and likely publications.",
                "supporting_publications": [c.get("candidate_id") for c in confirmed_likely],
                "supporting_site_evidence_ids": site_ids_all,
                "confidence": "high" if tier_counts["confirmed"] > 0 else "medium",
            })
        else:
            tid = 0
            for topic_key in sorted(topic_groups.keys()):
                tid += 1
                display_name, display_desc = TOPIC_DISPLAY.get(
                    topic_key, ("Research cluster " + topic_key, "Grouped by keyword overlap.")
                )
                site_ids = site_topic_map.get(topic_key, [])
                themes.append({
                    "theme_id": tid,
                    "name": display_name,
                    "description": display_desc,
                    "supporting_publications": topic_groups[topic_key],
                    "supporting_site_evidence_ids": site_ids,
                    "confidence": "high" if len(topic_groups[topic_key]) >= 2 else "medium",
                })

    theme_profile = {
        "lab_id": lab_id,
        "research_themes": themes,
        "peer_reviewed_publication_count": peer_reviewed_count,
        "preprint_count": preprint_count,
        "ambiguous_excluded_count": len(ambiguous),
        "ambiguous_publications_excluded": [c.get("candidate_id") for c in ambiguous],
        "insufficient_evidence": insufficient,
        "notes": "Research themes are derived from confirmed and likely publications only."
        + (" No confirmed publications found." if insufficient and tier_counts["confirmed"] == 0 else ""),
    }

    publication_evidence = []
    ev_id = 0
    for c in candidates:
        cid = c.get("candidate_id")
        me = c.get("match_evidence", {})
        if me.get("affiliation_match") in ("confirmed", "likely"):
            ev_id += 1
            publication_evidence.append({
                "evidence_id": ev_id, "lab_id": lab_id, "candidate_id": cid,
                "evidence_type": "affiliation_match",
                "description": f"Affiliation match status: {me['affiliation_match']}",
                "source_url": c.get("source_url", ""), "confidence": "high",
            })
        if me.get("topic_overlap"):
            ev_id += 1
            publication_evidence.append({
                "evidence_id": ev_id, "lab_id": lab_id, "candidate_id": cid,
                "evidence_type": "topic_overlap",
                "description": "Topic overlaps with lab research direction.",
                "source_url": c.get("source_url", ""), "confidence": "medium",
            })
        if me.get("pi_name_match") == "partial":
            ev_id += 1
            publication_evidence.append({
                "evidence_id": ev_id, "lab_id": lab_id, "candidate_id": cid,
                "evidence_type": "ambiguous_name_match",
                "description": "Author initials match PI but full name not confirmed.",
                "source_url": c.get("source_url", ""), "confidence": "low",
            })

    return curated, theme_profile, publication_evidence


def run(input_path: Path, output_dir: Path, fixture_dir: Path | None = None) -> None:
    input_data = read_json(input_path, {})
    plan = build_search_plan(input_data)
    write_json(output_dir / "publication_search_plan.json", plan)

    if fixture_dir is not None:
        candidates_path = fixture_dir / "publication_candidates.jsonl"
        if not candidates_path.exists():
            candidates_path = fixture_dir / "publication_candidates.sample.jsonl"
        evidence_in_path = fixture_dir / "publication_evidence.jsonl"
        if not evidence_in_path.exists():
            evidence_in_path = fixture_dir / "publication_evidence.sample.jsonl"
        candidates = read_jsonl(candidates_path)
        evidence_in = read_jsonl(evidence_in_path)
    else:
        candidates = []
        evidence_in = []

    site_evidence_path = input_path.parent / "lab_site_evidence.jsonl"
    if not site_evidence_path.exists():
        site_evidence_path = input_path.parent / "lab_site_evidence.sample.jsonl"
    site_evidence = read_jsonl(site_evidence_path)

    lab_id = input_data.get("lab_id", "unknown")
    for i, c in enumerate(candidates):
        c["candidate_id"] = i + 1
    for j, e in enumerate(evidence_in):
        e["evidence_id"] = j + 1
        e["lab_id"] = lab_id

    write_jsonl(output_dir / "publication_candidates.jsonl", candidates)

    curated, theme_profile, pub_evidence = build_curated_and_themes(
        candidates, evidence_in, input_data, site_evidence,
    )
    write_json(output_dir / "publications.curated.json", curated)
    write_jsonl(output_dir / "publication_evidence.jsonl", pub_evidence)

    source_db_counts: dict[str, int] = {}
    for c in candidates:
        db = c.get("source_db", "unknown")
        source_db_counts[db] = source_db_counts.get(db, 0) + 1

    tier_counts = curated.get("tier_counts", {})
    confirmed = tier_counts.get("confirmed", 0)
    likely = tier_counts.get("likely", 0)
    tier1_sufficient = _tier1_sufficient(confirmed, likely)
    tier2_attempted = not tier1_sufficient
    biomedical = input_data.get("biomedical_relevant", False)

    source_status = _build_source_status(
        source_db_counts, tier1_sufficient, tier2_attempted, biomedical,
    )

    blocking: list[str] = []
    warnings: list[str] = []
    if not candidates:
        blocking.append("No publication candidates found from any source.")
    if confirmed == 0 and likely == 0:
        blocking.append("No confirmed or likely publications found.")
    ambiguous_count = tier_counts.get("ambiguous", 0)
    if ambiguous_count > 0:
        warnings.append(
            f"{ambiguous_count} ambiguous publication(s) excluded from research summaries."
        )
    if not tier1_sufficient:
        warnings.append(
            "Tier 1 sources produced insufficient confirmed/likely publications. "
            "Consider activating Tier 2 sources."
        )

    status = "fail" if blocking else ("partial" if warnings else "pass")
    sufficient = tier1_sufficient

    sources_returning = sorted(s for s, c in source_db_counts.items() if c > 0)
    plan_sources = {s.get("source") for s in plan.get("search_sources", []) if isinstance(s, dict)}
    sources_no_results = sorted(plan_sources - set(sources_returning))

    audit = {
        "status": status,
        "metrics": {
            "total_candidates": len(candidates),
            "confirmed": confirmed,
            "likely": likely,
            "ambiguous": tier_counts.get("ambiguous", 0),
            "rejected": tier_counts.get("rejected", 0),
            "peer_reviewed": sum(
                1 for c in candidates if c.get("publication_type") == "peer_reviewed"
            ),
            "preprint": sum(
                1 for c in candidates if c.get("publication_type") == "preprint"
            ),
            "unknown_type": sum(
                1 for c in candidates if c.get("publication_type") == "unknown"
            ),
            "sources_used": sorted(source_db_counts.keys()),
            "sources_returning_results": sources_returning,
            "sources_returning_no_results": sources_no_results,
            "provenance_complete_ratio": round(
                sum(
                    1 for c in candidates
                    if c.get("source_db") and c.get("source_id")
                    and (c.get("source_url") or c.get("doi"))
                ) / len(candidates), 2,
            ) if candidates else 0.0,
            "confirmed_likely_ratio": round(
                (confirmed + likely) / len(candidates), 2,
            ) if candidates else 0.0,
            "sufficient": sufficient,
        },
        "source_status": source_status,
        "blocking_failures": blocking,
        "warnings": warnings,
        "repair_hints": [],
    }

    write_json(output_dir / "publication_audit.json", audit)
    write_json(output_dir / "research_theme_profile.json", theme_profile)

    print(
        f"Wrote {len(candidates)} candidates, {len(pub_evidence)} evidence, "
        f"audit status={audit['status']}, tier1_sufficient={tier1_sufficient}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run lab-publication-profile from synthetic fixtures or real API adapters."
    )
    parser.add_argument(
        "--input", type=Path, required=True,
        help="Path to lab_summary_input.json.",
    )
    parser.add_argument(
        "--out", type=Path, required=True,
        help="Output directory for artifacts.",
    )
    parser.add_argument(
        "--fixtures", type=Path, default=None,
        help="Directory with synthetic fixture files.",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    run(args.input, args.out, args.fixtures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

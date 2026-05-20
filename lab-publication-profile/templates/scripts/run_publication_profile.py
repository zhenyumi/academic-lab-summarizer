"""Copyable template to run lab-publication-profile from synthetic fixtures or real API adapters.

This template is stdlib-only and does not perform network requests.
For real runs, copy into <run>/tools/ and add source adapters for OpenAlex,
Semantic Scholar, PubMed, Crossref, etc. using the same output schema.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def reconstruct_openalex_abstract(abstract_inverted_index: dict[str, list[int | None]] | None) -> str:
    """Reconstruct abstract text from OpenAlex abstract_inverted_index format.

    OpenAlex stores abstracts as an inverted index mapping each word to a list
    of positions where it appears. This function reconstructs the original text
    by placing words at their correct positions.

    Args:
        abstract_inverted_index: Dict mapping words to lists of integer positions.
            Example: {"The": [0], "cat": [1], "sat": [2]}

    Returns:
        Reconstructed abstract text, or empty string if input is None/empty.
    """
    if not abstract_inverted_index:
        return ""
    max_pos = -1
    for positions in abstract_inverted_index.values():
        for pos in positions:
            if isinstance(pos, int) and pos > max_pos:
                max_pos = pos
    if max_pos < 0:
        return ""
    words: list[str] = [""] * (max_pos + 1)
    for word, positions in abstract_inverted_index.items():
        for pos in positions:
            if isinstance(pos, int) and 0 <= pos <= max_pos:
                words[pos] = word
    return " ".join(w for w in words if w)


def normalize_doi(doi: str | None) -> str:
    """Normalize a DOI string to lowercase with common prefixes stripped.

    Args:
        doi: Raw DOI string, possibly with URL prefix or 'doi:' prefix.

    Returns:
        Normalized lowercase DOI, or empty string if input is None/empty.
    """
    if not doi:
        return ""
    doi = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.lower()


def validate_source_record(
    candidate: dict[str, Any],
    fetched_record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate that a fetched source record matches the candidate's DOI/title.

    Args:
        candidate: The publication candidate dict with doi, source_id, source_db.
        fetched_record: The fetched record from the source API, or None if 404.

    Returns:
        Dict with 'valid' (bool) and 'issues' (list of str).
    """
    issues: list[str] = []
    if fetched_record is None:
        issues.append("Source ID not found (404)")
        return {"valid": False, "issues": issues}

    cand_doi = normalize_doi(candidate.get("doi"))
    fetched_doi_raw = fetched_record.get("doi", "")
    fetched_doi = normalize_doi(fetched_doi_raw)

    if cand_doi and fetched_doi and cand_doi != fetched_doi:
        issues.append(f"DOI mismatch: candidate={cand_doi}, fetched={fetched_doi}")

    cand_source_id = candidate.get("source_id", "")
    fetched_id = fetched_record.get("id", "")
    if cand_source_id and fetched_id and cand_source_id != fetched_id:
        issues.append(f"Source ID mismatch: candidate={cand_source_id}, fetched={fetched_id}")

    cand_title = (candidate.get("title", "") or "").strip().lower()
    fetched_title = (fetched_record.get("title", "") or "").strip().lower()
    if cand_title and fetched_title:
        cand_norm = re.sub(r"\s+", " ", cand_title)
        fetch_norm = re.sub(r"\s+", " ", fetched_title)
        if cand_norm != fetch_norm and not cand_norm.startswith(fetch_norm[:50]):
            issues.append(f"Title mismatch: candidate='{cand_title[:60]}', fetched='{fetched_title[:60]}'")

    return {"valid": len(issues) == 0, "issues": issues}


def candidate_needs_abstract(candidate: dict[str, Any]) -> bool:
    """Check if a candidate publication needs abstract enrichment.

    A candidate needs enrichment if:
    - Its abstract is empty or missing
    - Its abstract is identical to its title (not real content)
    - Its abstract is too short (< 50 chars)

    Args:
        candidate: Publication candidate dict.

    Returns:
        True if the candidate needs abstract enrichment.
    """
    abstract = candidate.get("abstract", "")
    if not abstract or len(abstract.strip()) < 50:
        return True
    title = (candidate.get("title", "") or "").strip().rstrip(".").lower()
    abstract_norm = abstract.strip().rstrip(".").lower()
    if abstract_norm == title:
        return True
    return False


def compute_abstract_coverage(
    candidates: list[dict[str, Any]],
    tiers: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Compute abstract coverage metrics for candidates.

    Args:
        candidates: List of publication candidate dicts.
        tiers: If provided, only count candidates whose match_tier is in this set.

    Returns:
        Dict with 'total', 'with_abstract', 'coverage_ratio', 'missing_abstract_ids'.
    """
    filtered = candidates
    if tiers is not None:
        filtered = [c for c in candidates if c.get("match_tier", "") in tiers]

    total = len(filtered)
    with_abstract = 0
    missing_ids: list[int] = []
    for c in filtered:
        if not candidate_needs_abstract(c):
            with_abstract += 1
        else:
            cid = c.get("candidate_id")
            if cid is not None:
                missing_ids.append(cid)

    ratio = round(with_abstract / total, 2) if total > 0 else 0.0
    return {
        "total": total,
        "with_abstract": with_abstract,
        "coverage_ratio": ratio,
        "missing_abstract_ids": missing_ids,
    }


def compute_source_validation_metrics(
    candidates: list[dict[str, Any]],
    validation_results: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Compute source validation metrics from validation results.

    Args:
        candidates: List of publication candidate dicts.
        validation_results: Dict mapping candidate_id to validation result dict.

    Returns:
        Dict with 'total', 'valid', 'invalid', 'unverifiable', 'invalid_source_id_count',
        'invalid_details'.
    """
    total = len(candidates)
    valid = 0
    invalid = 0
    unverifiable = 0
    invalid_details: list[dict[str, Any]] = []

    for c in candidates:
        cid = c.get("candidate_id")
        vr = validation_results.get(cid, {})
        if not vr:
            unverifiable += 1
            continue
        if vr.get("valid"):
            valid += 1
        else:
            invalid += 1
            invalid_details.append({
                "candidate_id": cid,
                "doi": c.get("doi", ""),
                "source_id": c.get("source_id", ""),
                "issues": vr.get("issues", []),
            })

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "unverifiable": unverifiable,
        "invalid_source_id_count": invalid,
        "invalid_details": invalid_details,
    }


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
        c["match_tier"] = tier
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
    repair_hints: list[dict[str, str]] = []
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
        repair_hints.append({
            "field": "source_tier",
            "suggestion": "Activate Tier 2 sources (Crossref, preprint servers) to resolve ambiguous candidates.",
        })

    abstract_cov_all = compute_abstract_coverage(candidates)
    abstract_cov_cl = compute_abstract_coverage(candidates, tiers=("confirmed", "likely"))
    if abstract_cov_cl["coverage_ratio"] < 0.5 and abstract_cov_cl["total"] > 0:
        warnings.append(
            f"Abstract coverage is low: {abstract_cov_cl['with_abstract']}/{abstract_cov_cl['total']} "
            f"confirmed/likely publications have abstracts."
        )
        repair_hints.append({
            "field": "abstract",
            "suggestion": "Enrich publication metadata: use DOI-based lookup from OpenAlex, PubMed, "
            "Semantic Scholar, or Crossref to retrieve missing abstracts. "
            "Do not fabricate summaries from titles alone.",
        })

    sources_returning = sorted(s for s, c in source_db_counts.items() if c > 0)
    plan_sources = {s.get("source") for s in plan.get("search_sources", []) if isinstance(s, dict)}
    sources_no_results = sorted(plan_sources - set(sources_returning))

    bio = input_data.get("biomedical_relevant", False)
    if bio and "pubmed" not in sources_returning:
        warnings.append("PubMed returned 0 candidates for this biomedical lab.")
        repair_hints.append({
            "field": "pubmed",
            "suggestion": "For biomedical labs, verify PubMed search terms and try PMID/DOI-based lookup "
            "for confirmed candidates to retrieve abstracts.",
        })

    status = "fail" if blocking else ("partial" if warnings else "pass")
    sufficient = tier1_sufficient

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
            "abstract_coverage_ratio": abstract_cov_all["coverage_ratio"],
            "confirmed_likely_abstract_coverage_ratio": abstract_cov_cl["coverage_ratio"],
            "sufficient": sufficient,
        },
        "source_status": source_status,
        "blocking_failures": blocking,
        "warnings": warnings,
        "repair_hints": repair_hints,
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

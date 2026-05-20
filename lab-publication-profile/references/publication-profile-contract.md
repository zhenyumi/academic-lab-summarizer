# Publication Profile Contract

## Purpose

`publication_search_plan.json`, `publication_candidates.jsonl`, `publications.curated.json`, `publication_evidence.jsonl`, `publication_audit.json`, and `research_theme_profile.json` define the inputs, candidates, curation, evidence, audit, and research themes for lab publication profiling.

## Input

Lab identity fields and optional `lab_site_evidence.jsonl` from `lab-site-evidence-extraction`.

### `lab_summary_input.json`

```json
{
  "lab_id": "example-lab-001",
  "lab_name": "Doe Neural Development Lab",
  "pi_name": "Jane Doe",
  "institution": "Example University",
  "lab_url": "https://example.edu/doe-lab",
  "input_mode": "from_lab_url",
  "biomedical_relevant": true,
  "previous_run_artifacts": {
    "lab_site_evidence_jsonl": "lab_summaries/example-lab-001/lab_site_evidence.jsonl"
  }
}
```

Required:
- `lab_id`, `lab_name`, `pi_name`, `institution`, `lab_url`

Optional:
- `biomedical_relevant`: Boolean; defaults to false. If true, PubMed is required.
- `input_mode`: `from_lab_url`.
- `previous_run_artifacts`: Paths to artifacts from previous lab-summary steps.

## Output: `publication_search_plan.json`

```json
{
  "lab_name": "Doe Neural Development Lab",
  "pi_name": "Jane Doe",
  "institution": "Example University",
  "lab_type": "biomedical",
  "biomedical_relevant": true,
  "year_range": [2020, 2026],
  "search_sources": [
    {
      "source": "lab_website",
      "tier": 0,
      "role": "primary_context",
      "rationale": "Lab site evidence contains publication references; PI-curated publication list provides authoritative attribution."
    },
    {
      "source": "openalex",
      "tier": 1,
      "role": "primary",
      "rationale": "Default structured starting point for author/works lookup."
    },
    {
      "source": "semantic_scholar",
      "tier": 1,
      "role": "supplementary",
      "rationale": "Enrichment, ranking, and cross-checking."
    },
    {
      "source": "pubmed",
      "tier": 1,
      "role": "conditional_primary",
      "rationale": "Lab is neuroscience; PubMed is required for biomedical labs."
    },
    {
      "source": "crossref",
      "tier": 2,
      "role": "verification",
      "rationale": "Activated if Tier 1 metadata incomplete or no confirmed publications."
    },
    {
      "source": "biorxiv",
      "tier": 2,
      "role": "supplementary",
      "rationale": "Activated if lab is life-science and recent preprints expected."
    }
  ],
  "excluded_sources": [
    {
      "source": "google_scholar",
      "reason": "Not recommended as automated primary source."
    }
  ]
}
```

### Required Fields

- `lab_name`, `pi_name`, `institution`: Lab identity.
- `search_sources`: Array with `source`, `tier`, `role`, and `rationale` for each selected source.
- `biomedical_relevant`: Boolean; if true, PubMed is required.
- `year_range`: Search year range.
- `excluded_sources`: Array with `source` and `reason` for excluded sources.

## Output: `publication_candidates.jsonl`

One JSON object per line:

```json
{
  "candidate_id": 1,
  "title": "Neural crest migration patterns in zebrafish",
  "authors": ["Jane Doe", "John Smith"],
  "year": 2024,
  "doi": "10.1234/example.2024.001",
  "source_db": "openalex",
  "source_id": "W1234567890",
  "source_url": "https://openalex.org/works/W1234567890",
  "venue": "Developmental Biology",
  "publication_type": "peer_reviewed",
  "match_evidence": {
    "pi_name_match": true,
    "affiliation_match": "confirmed",
    "topic_overlap": true,
    "coauthor_overlap": false,
    "lab_page_overlap": false
  }
}
```

### Required Fields

- `candidate_id`: Unique integer ID.
- `title`: Publication title.
- `authors`: Array of author names.
- `year`: Publication year.
- `source_db`: Source database (`openalex`, `semantic_scholar`, `pubmed`, `crossref`, `arxiv`, `biorxiv`, `medrxiv`, `lab_website`).
- `source_id`: ID in the source database.
- `publication_type`: `peer_reviewed`, `preprint`, or `unknown`.
- `match_evidence`: Object describing match indicators.

### Optional Fields

- `doi`: DOI if available.
- `source_url`: URL in the source database.
- `venue`: Journal or conference name.
- `abstract`: Abstract or summary text from the source database when available.
- `match_tier`: Derived match tier (`confirmed`, `likely`, `ambiguous`, `rejected`) set during curation.
- `online_date`, `preprint_date`, `metadata_date`: Supplementary dates when available.

## Output: `publications.curated.json`

```json
{
  "lab_id": "example-lab-001",
  "publications": [
    {
      "candidate_id": 1,
      "title": "Neural crest migration patterns in zebrafish",
      "authors": ["Jane Doe", "John Smith"],
      "year": 2024,
      "doi": "10.1234/example.2024.001",
      "venue": "Developmental Biology",
      "match_tier": "confirmed",
      "match_rationale": "PI is author, affiliation confirmed, topic matches lab site research direction.",
      "source_db": "openalex"
    },
    {
      "candidate_id": 5,
      "title": "CRISPR screening in model organisms",
      "authors": ["J. Doe", "Alice Brown"],
      "year": 2023,
      "match_tier": "ambiguous",
      "match_rationale": "Author initials match PI but full name not confirmed; no affiliation data.",
      "source_db": "semantic_scholar"
    }
  ],
  "tier_counts": {
    "confirmed": 3,
    "likely": 2,
    "ambiguous": 1,
    "rejected": 0
  }
}
```

### Required Fields

- `lab_id`: Lab identifier.
- `publications`: Array with `candidate_id`, `title`, `authors`, `year`, `match_tier`, `match_rationale`, `source_db`.
- `tier_counts`: Summary counts per match tier.
- Optional per-publication fields: `doi`, `venue`, `abstract`, `publication_type`.

### Match Tier Rules

- `confirmed`: PI is author + affiliation matches + topic/lab overlap verified.
- `likely`: Strong but incomplete match.
- `ambiguous`: Partial match with same-name ambiguity or weak overlap. Must not appear in research summaries.
- `rejected`: Not a match after review.

## Output: `publication_evidence.jsonl`

One JSON object per line linking publications to the lab:

```json
{
  "evidence_id": 1,
  "lab_id": "example-lab-001",
  "candidate_id": 1,
  "evidence_type": "affiliation_match",
  "description": "Author affiliation listed as Example University, Department of Biology.",
  "source_url": "https://openalex.org/works/W1234567890",
  "confidence": "high"
}
```

### Required Fields

- `evidence_id`, `lab_id`, `candidate_id`, `evidence_type`, `description`, `source_url`.

## Output: `publication_audit.json`

```json
{
  "status": "partial",
  "metrics": {
    "total_candidates": 15,
    "confirmed": 3,
    "likely": 2,
    "ambiguous": 1,
    "rejected": 9,
    "peer_reviewed": 10,
    "preprint": 3,
    "unknown_type": 2,
    "sources_used": ["openalex", "semantic_scholar", "pubmed"],
    "sources_returning_results": ["openalex", "semantic_scholar"],
    "sources_returning_no_results": ["pubmed"],
    "provenance_complete_ratio": 0.93,
    "evidence_provenance_complete_ratio": 0.95,
    "confirmed_likely_ratio": 0.33,
    "abstract_coverage_ratio": 0.4,
    "confirmed_likely_abstract_coverage_ratio": 0.6,
    "sufficient": true
  },
  "source_status": {
    "tier0_available": true,
    "tier1_sufficient": true,
    "tier2_attempted": false,
    "stop_reason": "tier0_plus_tier1_sufficient",
    "sources": [
      {"source": "lab_website", "tier": 0, "role": "primary_context", "activated": true, "activation_reason": "publication_ref_in_site_evidence", "outcome": "found_sufficient", "candidates": 8},
      {"source": "openalex", "tier": 1, "role": "primary", "activated": true, "activation_reason": "default", "outcome": "found_sufficient", "candidates": 8, "rate_limit_state": {"request_count": 3, "retry_count": 0, "last_delay_seconds": 0, "failure_reason": null}},
      {"source": "semantic_scholar", "tier": 1, "role": "supplementary", "activated": true, "activation_reason": "default", "outcome": "found_sufficient", "candidates": 5, "rate_limit_state": {"request_count": 2, "retry_count": 1, "last_delay_seconds": 2, "failure_reason": null}},
      {"source": "pubmed", "tier": 1, "role": "conditional_primary", "activated": true, "activation_reason": "biomedical_relevant", "outcome": "no_results", "candidates": 0, "rate_limit_state": {"request_count": 1, "retry_count": 0, "last_delay_seconds": 0, "failure_reason": null}}
    ]
  },
  "blocking_failures": [],
  "warnings": [
    "One ambiguous publication could not be resolved; it is excluded from research summaries."
  ],
  "repair_hints": []
}
```

### Required Fields

- `status`: `pass`, `partial`, or `fail`.
- `metrics`: Including tier counts, publication type counts, provenance completeness, and abstract coverage ratios (`abstract_coverage_ratio`, `confirmed_likely_abstract_coverage_ratio`).
- `source_status`: Tiered search status with `tier0_available`, `tier1_sufficient`, `tier2_attempted`, `stop_reason`, and per-source details including `rate_limit_state` when applicable.
- `blocking_failures`, `warnings`, `repair_hints`.

## Output: `research_theme_profile.json`

```json
{
  "lab_id": "example-lab-001",
  "research_themes": [
    {
      "theme_id": 1,
      "name": "Neural crest cell migration",
      "description": "Mechanisms of neural crest cell migration in vertebrate development.",
      "supporting_publications": [1, 3],
      "supporting_site_evidence_ids": [1, 2],
      "confidence": "high"
    }
  ],
  "peer_reviewed_publication_count": 3,
  "preprint_count": 1,
  "ambiguous_excluded_count": 1,
  "ambiguous_publications_excluded": [5],
  "insufficient_evidence": false,
  "notes": "Research themes are derived from confirmed and likely publications only. Ambiguous publications are excluded."
}
```

### Required Fields

- `lab_id`, `research_themes`, counts with peer-reviewed/preprint/ambiguous separation.
- Each theme: `theme_id`, `name`, `description`, `supporting_publications` (candidate IDs), `confidence`.
- `ambiguous_excluded_count` and `ambiguous_publications_excluded`: list of candidate IDs excluded from themes.
- `insufficient_evidence`: boolean; true when no confirmed or likely publications were found.

## Tiered Source Search Policy

Publication-source search must follow a tiered priority model. Sources are searched sequentially, not simultaneously. Agents must not re-implement source adapters from scratch on each invocation.

### Tier 0 — Lab Context (zero API cost, always first)

| Source | Role | Activation |
|---|---|---|
| Lab website | PI-curated publication list, lab-level attribution | When `lab_site_evidence.jsonl` contains `claim_type: "publication_ref"` |

Tier 0 is checked before any API call. It has zero network cost beyond what the prior `lab-site-evidence-extraction` step already fetched. Lab website publications are PI-curated and authoritative for attribution, but typically lack abstracts and citation metadata.

If `lab_site_evidence.jsonl` does not contain `claim_type: "publication_ref"`, skip Tier 0 and proceed directly to Tier 1.

### Tier 1 — Primary Search (structured API sources)

| Source | Role | Activation |
|---|---|---|
| OpenAlex | Default structured starting point for author/institution/works lookup | Always |
| Semantic Scholar | Supplementary enrichment, ranking, abstracts, citations, cross-check | Always |
| PubMed | Required for biomedical/life-science/neuroscience/clinical labs | When `biomedical_relevant: true` |

### Tier 2 — Enrichment / Fallback (only when Tier 0 + Tier 1 insufficient)

| Source | Role | Activation |
|---|---|---|
| Crossref | DOI, publication date, venue, publisher metadata verification | When Tier 1 metadata incomplete or no confirmed publications |
| bioRxiv / medRxiv | Preprint discovery | When lab is life-science/clinical or recent preprints expected |
| arXiv | Preprint discovery | When lab is CS/physics/math or recent preprints expected |

### Manual Fallback

- Google Scholar: manual-only fallback, never automated primary source.

### Search Flow Rules

1. Check Tier 0: scan `lab_site_evidence.jsonl` for `claim_type: "publication_ref"`. If found, extract publication references and add to candidates. Track `source_status` per source.
2. Search Tier 1 sources sequentially. Track `source_status` per source, including rate limit state.
3. Evaluate sufficiency after each tier: ≥ 1 confirmed publication OR ≥ 2 likely publications = sufficient.
4. If Tier 0 + Tier 1 is insufficient, activate Tier 2 sources with `activation_reason`.
5. If all tiers are still insufficient, set `stop_reason: "all_tiers_insufficient"` and `sufficient_for_profile: false`.
6. Agents must not proceed to theme synthesis when `sufficient_for_profile: false` unless explicitly marked `insufficient_evidence: true` in `research_theme_profile.json`.

### Stop Reason Values

The `source_status.stop_reason` field uses these values:

| Stop Reason | Meaning |
|---|---|
| `tier0_plus_tier1_sufficient` | Tier 0 was activated (lab website had publication references) and combined Tier 0 + Tier 1 results are sufficient |
| `tier1_sufficient` | Tier 0 was not activated (no publication references in site evidence) and Tier 1 alone is sufficient |
| `insufficient_tier1` | Tier 0 + Tier 1 produced insufficient results; Tier 2 has not yet been attempted |
| `tier1_plus_tier2_sufficient` | Tier 2 was activated and combined results across all tiers are sufficient |
| `tier1_plus_tier2_insufficient` | All tiers attempted but results are still insufficient |
| `all_tiers_insufficient` | All tiers exhausted, no confirmed or likely publications found |

### `tier0_available` Semantics

`tier0_available` is `true` when actual Tier 0 publication candidates from the lab website exist in the output (i.e., `source_db_counts["lab_website"] > 0`). It is `false` when no lab website candidates were produced, even if `lab_website` appears in the search plan.

### Source Adapter Reuse Rule

Source adapters (API clients, query builders, response parsers) should be written as reusable components in `<run>/tools/`. Agents must not re-implement the same API client from scratch on each invocation. When a real API adapter exists in `<run>/tools/`, use it; otherwise use the template runner's fixture-based approach until an adapter is built.

## API Rate Limiting

All external API sources (Tier 1 and Tier 2) must respect rate limits. Lab website (Tier 0) is exempt from API rate limiting but must respect `robots.txt` and `Crawl-Delay`.

### Rules

1. **Inter-request delay**: Minimum 1 second between consecutive requests to the same service (configurable per source).
2. **Exponential backoff**: On HTTP 429 (rate limit) or 503 (service unavailable), retry with exponential backoff: 2s, 4s, 8s, up to a maximum of 30 seconds per retry.
3. **Skip after 3 failures**: After 3 consecutive failures for the same source, mark that source as `"skipped"` with `activation_reason: "rate_limited"` and proceed to the next source.
4. **Per-source timeout**: 60 seconds total per source. If a source cannot complete within this window, mark it `"timeout"` and proceed.
5. **Rate limit state logging**: Record retry count, last delay, and failure reason in `source_status.sources[].rate_limit_state` for audit trail.

### Rate Limit State Schema

```json
{
  "rate_limit_state": {
    "request_count": 3,
    "retry_count": 1,
    "last_delay_seconds": 2,
    "failure_reason": null
  }
}
```

When a source is skipped due to rate limiting, `failure_reason` is set to `"rate_limited"` or `"timeout"`.

## Provenance Rules

- Every publication candidate must retain `source_db`, `source_id`, and `source_url` (or DOI).
- Publication matching must consider author identity, affiliation, coauthor overlap, topic overlap, lab publications page overlap, DOI/title cross-source match, and same-name ambiguity.
- Preprints must be labeled separately from peer-reviewed publications.

## Date Rules

- Publication dates must distinguish `year` (primary), `online_date`, `preprint_date`, and `metadata_date` when available.
- Current-year research summaries must separate peer-reviewed, preprints, lab news, and uncertain records.

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
    "sufficient": true
  },
  "source_status": {
    "tier1_sufficient": true,
    "tier2_attempted": false,
    "stop_reason": "tier1_sufficient",
    "sources": [
      {"source": "openalex", "tier": 1, "role": "primary", "activated": true, "activation_reason": "default", "outcome": "found_sufficient", "candidates": 8},
      {"source": "semantic_scholar", "tier": 1, "role": "supplementary", "activated": true, "activation_reason": "default", "outcome": "found_sufficient", "candidates": 5},
      {"source": "pubmed", "tier": 1, "role": "conditional_primary", "activated": true, "activation_reason": "biomedical_relevant", "outcome": "no_results", "candidates": 0}
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
- `metrics`: Including tier counts, publication type counts, and provenance completeness.
- `source_status`: Tiered search status with `tier1_sufficient`, `tier2_attempted`, `stop_reason`, and per-source details.
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

Publication-source search must follow a tiered priority model. Agents must not search all sources simultaneously or re-implement source adapters from scratch on every invocation.

### Tier 1 — Primary Search

Always search first:

| Source | Role | Activation |
|---|---|---|
| OpenAlex | Default structured starting point for author/institution/works lookup | Always |
| Semantic Scholar | Supplementary enrichment, ranking, abstracts, citations, cross-check | Always |
| PubMed | Required for biomedical/life-science/neuroscience/clinical labs | When `biomedical_relevant: true` |

### Tier 2 — Enrichment / Fallback

Activated only when Tier 1 does not produce sufficient confirmed or likely publications:

| Source | Role | Activation |
|---|---|---|
| Crossref | DOI, publication date, venue, publisher metadata verification | When Tier 1 metadata incomplete or no confirmed publications |
| bioRxiv / medRxiv | Preprint discovery | When lab is life-science/clinical or recent preprints expected |
| arXiv | Preprint discovery | When lab is CS/physics/math or recent preprints expected |
| Lab website | Lab-level attribution, publications page cross-check | When Tier 1 has ambiguous candidates needing lab-level confirmation |

### Manual Fallback

- Google Scholar: manual-only fallback, never automated primary source.

### Search Flow Rules

1. Search Tier 1 first. Track `source_status` per source.
2. Evaluate Tier 1 sufficiency: ≥ 1 confirmed publication OR ≥ 2 likely publications = sufficient.
3. If Tier 1 is insufficient, activate Tier 2 sources with `activation_reason`.
4. If Tier 1 + Tier 2 are still insufficient, set `stop_reason: "tier1_plus_tier2_insufficient"` and `sufficient_for_profile: false`.
5. Agents must not proceed to theme synthesis when `sufficient_for_profile: false` unless explicitly marked `insufficient_evidence: true` in `research_theme_profile.json`.

### Source Adapter Reuse Rule

Source adapters (API clients, query builders, response parsers) should be written as reusable components in `<run>/tools/`. Agents must not re-implement the same API client from scratch on each invocation. When a real API adapter exists in `<run>/tools/`, use it; otherwise use the template runner's fixture-based approach until an adapter is built.

## Provenance Rules

- Every publication candidate must retain `source_db`, `source_id`, and `source_url` (or DOI).
- Publication matching must consider author identity, affiliation, coauthor overlap, topic overlap, lab publications page overlap, DOI/title cross-source match, and same-name ambiguity.
- Preprints must be labeled separately from peer-reviewed publications.

## Date Rules

- Publication dates must distinguish `year` (primary), `online_date`, `preprint_date`, and `metadata_date` when available.
- Current-year research summaries must separate peer-reviewed, preprints, lab news, and uncertain records.

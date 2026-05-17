---
name: lab-publication-profile
description: "Use when an agent needs to search recent publications for a known lab, audit PI/lab attribution, and build research themes: given lab identity fields and optional lab site evidence, search structured sources (OpenAlex, Semantic Scholar, PubMed, Crossref, preprint servers), produce candidate publications with provenance, curate into confirmed/likely/ambiguous/rejected tiers, and output a research theme profile. Do not reopen institution-level lab discovery. Trigger when lab-summary publication profiling is requested after lab site evidence extraction or when building a publication-backed lab profile."
---

# Lab Publication Profile

## Core Rule

Every publication candidate must preserve source provenance. Publication matching must not rely on PI name alone. Ambiguous publications must remain separate from confirmed or likely publications. When search results are insufficient, stop and report clearly rather than proceeding with unreliable data.

Publication profiling is a core v1 capability of `academic-lab-summarizer`, not a future extension. Preserve the tiered source policy, provenance fields, match tiers, audit artifacts, and research theme synthesis whenever this skill is migrated or adapted.

## Inputs

- `lab_summary_input.json` (recommended): Aggregated lab-summary input with `lab_id`, `lab_name`, `pi_name`, `institution`, `lab_url`, optional `biomedical_relevant`.
- Lab identity fields (required): `lab_name`, `pi_name`, `institution`.
- `lab_site_evidence.jsonl` (optional): Site evidence from `lab-site-evidence-extraction`.

## Outputs

- `publication_search_plan.json`: Search strategy with tiered source selection rationale.
- `publication_candidates.jsonl`: Raw candidates with full provenance.
- `publications.curated.json`: Curated publications with match tier.
- `publication_evidence.jsonl`: Evidence linking publications to the lab.
- `publication_audit.json`: Audit of matching quality, coverage, and source status.
- `research_theme_profile.json`: Synthesized research themes from confirmed and likely publications.

All outputs are written under `lab_summaries/<lab_id>/`.

## Hard Constraints

- Do not reopen institution-level lab discovery.
- Do not treat a paper as lab output solely because the PI name matches.
- Separate confirmed, likely, ambiguous, and rejected publication matches.
- Do not summarize ambiguous publications as lab research output.
- Current-year research summaries must separate peer-reviewed, preprints, lab news, and uncertain records.
- Google Scholar must not be used as an automated primary source.

## Tiered Source Search Policy

Publication-source search follows a tiered priority model. Sources are searched sequentially, not simultaneously. Do not re-implement source adapters from scratch on each invocation.

### Tier 0 — Lab Context (zero API cost, always first)

| Source | Role | Activation |
|---|---|---|
| Lab website | PI-curated publication list, lab-level attribution | When `lab_site_evidence.jsonl` contains `claim_type: "publication_ref"` |

Tier 0 is checked before any API call. It has zero network cost beyond what the prior `lab-site-evidence-extraction` step already fetched. Lab website publications are PI-curated and authoritative for attribution, but typically lack abstracts and citation metadata. When Tier 0 produces candidates, they are merged with Tier 1 results during curation.

If `lab_site_evidence.jsonl` does not contain `claim_type: "publication_ref"`, skip Tier 0 and proceed directly to Tier 1.

### Tier 1 — Primary Search (structured API sources)

| Source | Role | Activation |
|---|---|---|
| OpenAlex | Default structured starting point for author/institution/works lookup | Always |
| Semantic Scholar | Enrichment, ranking, abstracts, cross-check | Always |
| PubMed | Required for biomedical/life-science/neuroscience/clinical | When `biomedical_relevant: true` |

### Tier 2 — Enrichment / Fallback (only when Tier 0 + Tier 1 insufficient)

| Source | Role | Activation |
|---|---|---|
| Crossref | DOI/date/venue metadata verification | Tier 1 metadata incomplete or no confirmed publications |
| bioRxiv / medRxiv | Preprint discovery | Life-science/clinical labs with recent preprints |
| arXiv | Preprint discovery | CS/physics/math labs |

### Search Flow

1. Check Tier 0: scan `lab_site_evidence.jsonl` for `claim_type: "publication_ref"`. If found, extract publication references from site evidence and add to candidates. Track `source_status` per source.
2. Search Tier 1 sources sequentially. Track `source_status` per source, including rate limit state.
3. Evaluate sufficiency after each tier: ≥ 1 confirmed OR ≥ 2 likely = sufficient.
4. If Tier 0 + Tier 1 insufficient, activate Tier 2 with `activation_reason`.
5. If all tiers still insufficient, set `stop_reason: "all_tiers_insufficient"` and `sufficient_for_profile: false`.
6. Do not proceed to theme synthesis when `sufficient_for_profile: false` unless explicitly marked `insufficient_evidence: true`.

### Source Adapter Reuse

Source adapters (API clients, query builders, response parsers) should be reusable components in `<run>/tools/`. Do not re-implement the same API client from scratch on each invocation. Use the template runner's fixture-based approach until real adapters are built.

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

## Source Priority

| Source | Role | Priority |
|---|---|---|
| Lab website | PI-curated publications page, lab-level attribution, research direction | Primary context (Tier 0) |
| OpenAlex | Default structured starting point for author/institution/works lookup | Primary |
| Semantic Scholar | Supplementary enrichment, ranking, abstracts, citations, cross-check | Supplementary |
| PubMed | Required for biomedical/life-science/neuroscience/clinical labs | Conditional primary |
| Crossref | DOI, publication date, venue, publisher metadata verification | Verification |
| arXiv/bioRxiv/medRxiv | Preprint sources; must be labeled separately from peer-reviewed | Supplementary |
| Google Scholar | Not recommended as automated primary source; manual fallback only | Not automated |

### Source Policy Rules

1. Lab website is checked first (Tier 0) when publication references are available from site evidence.
2. OpenAlex is the default structured starting point (Tier 1).
3. Semantic Scholar supplements for enrichment, ranking, and cross-checking.
4. PubMed is required when the lab is biomedical/clinical/life-science/neuroscience.
5. Crossref is for DOI/date/venue verification, not primary discovery.
6. arXiv/bioRxiv/medRxiv preprints must be clearly labeled and not merged with peer-reviewed without a status field.
7. Lab website evidence provides authoritative attribution but typically lacks abstracts; API sources supplement with metadata.
8. Every publication candidate must retain source database, source URL/ID, DOI, title, year, authors, and match evidence.

## Match Tiers

| Tier | Meaning |
|---|---|
| `confirmed` | PI is author, affiliation matches, topic/lab overlap verified |
| `likely` | Strong but incomplete match (e.g., PI name + topic match but affiliation unclear) |
| `ambiguous` | Partial match; same-name ambiguity or weak overlap; must not appear in research summaries |
| `rejected` | Not a match after review |

## Date Handling

Publication dates must distinguish:
- Publication year
- Online date
- Preprint date
- Metadata deposit/update date

When these differ, use publication year as primary and store others as supplementary.

## Workflow

1. Read lab identity and any site evidence.
2. Check Tier 0: scan `lab_site_evidence.jsonl` for publication references on the lab website.
3. Create `publication_search_plan.json` with tiered source selection rationale.
4. Search Tier 1 sources sequentially, collect candidates into `publication_candidates.jsonl`.
5. Evaluate sufficiency. If insufficient, activate Tier 2 sources.
6. Audit PI/lab attribution and classify into match tiers → `publications.curated.json`.
7. Write `publication_evidence.jsonl` linking publications to the lab.
8. Produce `publication_audit.json` with matching quality metrics and source status.
9. If `sufficient_for_profile: true`, synthesize confirmed and likely publications into `research_theme_profile.json`.
10. If insufficient, set `insufficient_evidence: true` in theme profile and report clearly.

## Validation

```bash
python lab-publication-profile/scripts/validate_publication_profile_artifacts.py --examples
python lab-publication-profile/scripts/validate_publication_profile_artifacts.py <artifact_dir>
```

## Template-First Execution

The skill ships portable runner templates. For real runs, copy them into the run directory first, then adapt the copies when site-specific handling is needed:

```bash
mkdir -p <run>/tools
cp lab-publication-profile/templates/scripts/run_publication_profile.py <run>/tools/
cp lab-publication-profile/templates/scripts/audit_publication_profile.py <run>/tools/
```

### Synthetic fixture run

```bash
python lab-publication-profile/templates/scripts/run_publication_profile.py \
  --input lab-publication-profile/examples/lab_summary_input.sample.json \
  --out /tmp/publication-profile-test \
  --fixtures lab-publication-profile/examples

python lab-publication-profile/templates/scripts/audit_publication_profile.py /tmp/publication-profile-test
```

### Real run (after copying to `<run>/tools/`)

```bash
python <run>/tools/run_publication_profile.py \
  --input lab_summaries/<lab_id>/lab_summary_input.json \
  --out lab_summaries/<lab_id>

python <run>/tools/audit_publication_profile.py lab_summaries/<lab_id>
```

Adapt the copied `run_publication_profile.py` to add real API adapters (e.g., OpenAlex, Semantic Scholar, PubMed, Crossref) following the same output schema. The template runner only processes synthetic fixtures by default.

## Implementation Priority

During the initial implementation phase, focus on:
- Tiered source priority rules with stop/return behavior
- Source adapter reuse pattern
- Structured candidate records with provenance
- Author/lab match auditing
- Separation of confirmed, likely, ambiguous, and rejected

Polished narrative summaries should not be prioritized before publication matching is reliable.

## Abstract Preservation

When searching and curating publications, preserve the `abstract` field whenever available:

- **OpenAlex**: Returns `abstract_inverted_index` (a word→position map). Convert to plain text by sorting words by position before concatenation. Store the result in the `abstract` field.
- **Semantic Scholar**: Returns `abstract` as a plain text string. Store directly.
- **PubMed**: Returns `Abstract` as structured text (may contain labeled sections). Flatten to plain text and store in the `abstract` field.
- The `abstract` field must be propagated from `publication_candidates.jsonl` through `publications.curated.json` to downstream consumers. Do not drop it during curation.
- When no abstract is available from any source, leave the field as an empty string rather than omitting it.

### Abstract Quality Rules

- **Never use the paper title as the abstract.** If the API returns `abstract` identical to `title` or shorter than 50 characters, treat it as a missing abstract and store an empty string.
- OpenAlex `abstract_inverted_index` conversion must produce the **full** reconstructed abstract text, not a truncated version. The conversion algorithm: collect all `(position, word)` pairs from the inverted index, sort by position, join with spaces.
- If OpenAlex returns an empty or null `abstract_inverted_index`, check Semantic Scholar as a fallback before concluding no abstract exists.
- The downstream `publication_overview` system detects invalid abstracts (title-as-abstract, extremely short abstracts) and falls back to title-only mode. Ensure the raw `abstract` field is clean so detection works correctly.

## Research Theme Quality

When synthesizing `research_theme_profile.json`, produce meaningful, specific themes:

- When confirmed + likely publications total **3 or more**, generate **at least 2 distinct research themes**. A single catch-all "Lab research directions" theme is only acceptable when there are fewer than 3 confirmed/likely publications.
- Each theme must have:
  - A **specific name** describing a research direction (e.g., "Platelet-mediated brain rejuvenation"), not a generic label (e.g., "Lab research directions").
  - A **description** of 1-2 sentences explaining the scientific content of that research direction.
- Themes should be derived from the **content** of the publications (topics, methods, findings), not just venue names or author lists.
- The deterministic runner provides a keyword-based baseline grouping. **The AI agent must refine these into meaningful, specific themes** using its understanding of the publication content and lab site evidence.
- Associate `supporting_site_evidence_ids` where site evidence corroborates a theme.

## Match Rationale Quality

The `match_rationale` field in `publications.curated.json` must be **human-readable natural language**:

- **Required format**: A concise sentence explaining why this publication matches the lab. Example: "PI name confirmed as author; affiliation matches; topic overlaps with lab's exercise-neurogenesis research."
- **Prohibited**: Raw Python dict strings like `Derived from match_evidence: {'pi_name_match': 'confirmed', ...}`.
- The rationale should combine all available match evidence (PI name match, affiliation match, topic overlap) into a readable explanation.
- The deterministic runner generates a baseline rationale from `match_evidence` fields. The AI agent should refine it with contextual understanding.

## References

- `references/publication-profile-contract.md`: Input/output field contracts, provenance rules, tiered source policy, and validation rules.

# Lab Publication Profile Usage Guide

## Invocation

Codex:

```text
Use $lab-publication-profile at /absolute/path/to/lab-publication-profile to search recent publications for <pi_name> at <institution> and build a research theme profile.
```

OpenCode or another agent:

```text
Read /absolute/path/to/lab-publication-profile/SKILL.md and follow it to search structured publication sources, curate candidates into match tiers, and produce a research theme profile.
```

## Operating Model

The agent should search structured publication databases (OpenAlex, Semantic Scholar, PubMed, Crossref, preprint servers) using lab identity fields. Every publication candidate must preserve source provenance. Publication matching must not rely on PI name alone — consider affiliation, coauthor overlap, topic overlap, and same-name ambiguity.

Ambiguous publications must remain separate from confirmed or likely publications and must not appear in research summaries.

Google Scholar must not be used as an automated primary source.

For detailed guidance on how a real source adapter should conform to the existing schema (per-source identifiers, dedup key precedence, failure classification, and PubMed/Google-Scholar rules), see `references/publication-profile-contract.md` → "Adapter Roadmap (not yet implemented)".

## Tiered Source Search

Publication search follows a tiered priority model:

1. **Tier 0** (always first, zero API cost): Lab website publication page (when site evidence contains `publication_ref`)
2. **Tier 1** (structured API search): OpenAlex, Semantic Scholar, PubMed (if biomedical-relevant)
3. **Tier 2** (only if Tier 0 + Tier 1 insufficient): Crossref, bioRxiv/medRxiv, arXiv

The agent should check Tier 0 (lab website publications) first, then evaluate Tier 1 sufficiency before expanding to Tier 2. If no source produces reliable results, stop and report clearly.

## Template-First Scripts

| Script | Purpose |
| --- | --- |
| `lab-publication-profile/templates/scripts/run_publication_profile.py` | Produces search plan, candidates, curated publications, evidence, audit, and themes from fixtures or adapted API adapters |
| `lab-publication-profile/templates/scripts/audit_publication_profile.py` | Audits artifacts and writes `publication_audit.json` |
| `lab-publication-profile/scripts/validate_publication_profile_artifacts.py` | Validates artifacts against contract (no mutation) |

## Quick Validation

```bash
python lab-publication-profile/scripts/validate_publication_profile_artifacts.py --examples
```

## End-to-End Synthetic Run

```bash
python lab-publication-profile/templates/scripts/run_publication_profile.py \
  --input lab-publication-profile/examples/lab_summary_input.sample.json \
  --out /tmp/publication-profile-test \
  --fixtures lab-publication-profile/examples

python lab-publication-profile/templates/scripts/audit_publication_profile.py /tmp/publication-profile-test

python lab-publication-profile/scripts/validate_publication_profile_artifacts.py /tmp/publication-profile-test
```

## Minimal Run Shape

1. Read lab identity and optional site evidence.
2. Create `publication_search_plan.json` with tiered source selection rationale.
3. Check Tier 0 (lab website) first, then search Tier 1 sources, collect candidates.
4. Evaluate Tier 1 sufficiency. If insufficient, activate Tier 2.
5. Audit PI/lab attribution and classify into match tiers.
6. Write `publication_audit.json` and verify status.
7. If sufficient, synthesize confirmed and likely publications into `research_theme_profile.json`.
8. If insufficient, report clearly and do not fabricate themes.

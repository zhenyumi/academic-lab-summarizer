---
name: lab-site-evidence-extraction
description: "Use when an agent needs to extract structured evidence from one known academic lab website: research directions, PI info, members, publication references, facilities, and open-position/recruitment signals. Produce a lab site plan, fetched pages, structured evidence items, and a site audit. Do not search external publication databases or synthesize the final lab profile."
---

# Lab Site Evidence Extraction

## Core Rule

Extract only what the lab website actually contains. Every evidence item must include `source_url`, `snippet`, `claim_type`, `evidence_quality`, and `extraction_status`. Do not invent, infer, or hallucinate content that is not present on the site.

## Inputs

- `lab_url` (required): Official lab website URL.
- `lab_name` (required): Lab name from curated discovery.
- `pi_name` (required): PI name from curated discovery.
- `institution` (required): Institution name.
- Optional: `labs.curated.json`, `evidence.jsonl`, `pages.jsonl` from a previous institution crawl run, or manually supplied lab identity evidence.

## Outputs

- `lab_site_plan.json`: Crawl plan scoped to a single lab website.
- `lab_pages.jsonl`: Pages fetched from the lab site.
- `lab_site_evidence.jsonl`: Structured evidence items.
- `lab_site_audit.json`: Site-level evidence quality audit.

All outputs are written under `lab_summaries/<lab_id>/`.

## Hard Constraints

- Do not search external publication databases (OpenAlex, Semantic Scholar, PubMed, Crossref, Google Scholar).
- Do not synthesize final lab profile judgments.
- Treat link-text-only evidence as weak (`evidence_quality: link_text_only`).
- Every evidence item must include `source_url`, `snippet`, `claim_type`, `evidence_quality`, and `extraction_status`.
- Do not modify existing crawl or report artifacts.

## Evidence Quality Tiers

| `evidence_quality` | Meaning |
|---|---|
| `research_description` | Substantive description of research direction or projects from the lab site |
| `profile_snippet` | Brief profile or bio text about PI or lab members |
| `link_text_only` | Only anchor text such as "Visit X Lab website" — weak, do not summarize research from this |
| `none` | No usable evidence found |

## Claim Types

Allowed `claim_type` values:

- `research_direction`: Research area or project description.
- `pi_info`: PI name, title, contact, or bio.
- `lab_member`: Lab member name, role, or profile.
- `publication_ref`: Publication mentioned on the lab site.
- `position_signal`: Job opening, recruitment, or join-us language.
- `lab_url`: External link to related resource.
- `facility`: Equipment, facility, or resource description.
- `other`: Any other evidence type.

## Extraction Status

Allowed `extraction_status` values:

- `extracted`: Successfully extracted with supporting snippet.
- `partial`: Partially extracted; some fields are missing or uncertain.
- `unavailable`: Target information does not exist on the page.
- `skipped`: Extraction was not attempted for this item.

## Workflow

1. Read input parameters and any previous crawl artifacts.
2. Create a scoped `lab_site_plan.json` targeting the single lab website.
3. Crawl the lab site pages and store as `lab_pages.jsonl`.
4. Extract structured evidence items into `lab_site_evidence.jsonl`.
5. Run site-level audit and write `lab_site_audit.json`.

## Audit Focus

- Evidence coverage: does the site provide substantive research descriptions or only link text?
- PI info completeness: is PI name, title, and contact extractable?
- Position signals: are any PhD, postdoc, student, RA, staff, technician, lab manager, or other openings present, and are they generic or role-specific?
- Contamination: are email fragments, navigation text, or card fragments polluting evidence?
- Weak evidence ratio: what fraction of evidence is link-text-only?

### Page Prioritization and Cleanup

When crawling a real lab site, prioritize pages in this order: about/research > people/publications > join-us/openings > other. Strip navigation, footer, cookie banners, and sidebar content before extracting evidence. See "Crawler Roadmap" in the contract for full guidance on robots.txt, sitemaps, PDF handling, and failure retry.

## Validation

```bash
python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py --examples
python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py <artifact_dir>
```

## Template-First Execution

The skill ships portable runner templates. For real runs, copy them into the run directory first, then adapt the copies when site-specific handling is needed:

```bash
mkdir -p <run>/tools
cp lab-site-evidence-extraction/templates/scripts/run_lab_site_extraction.py <run>/tools/
cp lab-site-evidence-extraction/templates/scripts/audit_lab_site_evidence.py <run>/tools/
```

### Synthetic fixture run

```bash
python lab-site-evidence-extraction/templates/scripts/run_lab_site_extraction.py \
  --input lab-site-evidence-extraction/examples/lab_summary_input.sample.json \
  --out /tmp/lab-site-test \
  --fixtures lab-site-evidence-extraction/examples

python lab-site-evidence-extraction/templates/scripts/audit_lab_site_evidence.py /tmp/lab-site-test
```

### Real run (after copying to `<run>/tools/`)

```bash
python <run>/tools/run_lab_site_extraction.py \
  --input lab_summaries/<lab_id>/lab_summary_input.json \
  --out lab_summaries/<lab_id>

python <run>/tools/audit_lab_site_evidence.py lab_summaries/<lab_id>
```

Adapt the copied `run_lab_site_extraction.py` to add real crawl logic (e.g., `requests` + `beautifulsoup4`) for the target lab site. The template runner only processes synthetic fixtures by default.

## References

- `references/lab-site-evidence-contract.md`: Input/output field contracts and validation rules.

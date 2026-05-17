# Lab Site Evidence Extraction Usage Guide

## Invocation

Codex:

```text
Use $lab-site-evidence-extraction at /absolute/path/to/lab-site-evidence-extraction to extract structured evidence from the lab website for <lab_name> at <lab_url>.
```

OpenCode or another agent:

```text
Read /absolute/path/to/lab-site-evidence-extraction/SKILL.md and follow it to extract structured evidence from a lab website, producing a site plan, evidence items, and site-level audit.
```

## Operating Model

The agent should crawl only the single lab website, not the broader institution site. Evidence items must include source URLs, snippets, claim types, and quality tiers. The output is a set of artifacts under `lab_summaries/<lab_id>/` for downstream publication profiling and fit assessment.

Do not search external publication databases. Do not synthesize the final lab profile.

## Minimal Run Shape

1. Prepare `lab_summary_input.json` with lab identity fields.
2. Create `lab_site_plan.json` scoped to the lab website.
3. Crawl the lab site and extract evidence.
4. Run site-level audit.
5. Verify `lab_site_audit.json` status before passing artifacts to `lab-publication-profile`.

## Template-First Scripts

Runner and audit templates live under `templates/scripts/`. For a real run, copy them into `<run>/tools/` and adapt the copies for the target site. Shared templates should stay general-purpose.

| Script | Purpose |
| --- | --- |
| `templates/scripts/run_lab_site_extraction.py` | Produces `lab_site_plan.json`, `lab_pages.jsonl`, `lab_site_evidence.jsonl` from fixtures or adapted crawl logic |
| `templates/scripts/audit_lab_site_evidence.py` | Audits artifacts and writes `lab_site_audit.json` |
| `scripts/validate_lab_site_artifacts.py` | Validates all artifact files against the contract (no mutation) |

### Quick validation

```bash
python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py --examples
```

### End-to-end synthetic run

```bash
python lab-site-evidence-extraction/templates/scripts/run_lab_site_extraction.py \
  --input lab-site-evidence-extraction/examples/lab_summary_input.sample.json \
  --out /tmp/lab-site-test \
  --fixtures lab-site-evidence-extraction/examples

python lab-site-evidence-extraction/templates/scripts/audit_lab_site_evidence.py /tmp/lab-site-test

python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py /tmp/lab-site-test
```

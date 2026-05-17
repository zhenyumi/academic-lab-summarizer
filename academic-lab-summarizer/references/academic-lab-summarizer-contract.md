# Academic Lab Summarizer Contract

## Purpose

`lab_summary_manifest.json` records the status and artifact paths for one full academic lab summary run.

## Required Input

`lab_summary_input.json`:

```json
{
  "lab_id": "example-lab-001",
  "lab_name": "Doe Neural Development Lab",
  "pi_name": "Jane Doe",
  "institution": "Example University",
  "lab_url": "https://example.edu/doe-lab",
  "input_mode": "from_lab_url",
  "biomedical_relevant": true
}
```

Required fields: `lab_id`, `lab_name`, `pi_name`, `institution`, `lab_url`.

## Manifest Steps

Steps must appear in this exact order:

1. `lab-site-evidence-extraction`
2. `lab-publication-profile`
3. `lab-profile-synthesis`

Each non-skipped step needs `status`, `audit_status`, and expected `artifacts`.

## Expected Artifacts

Site step:

- `lab_site_plan.json`
- `lab_pages.jsonl`
- `lab_site_evidence.jsonl`
- `lab_site_audit.json`

Publication step:

- `publication_search_plan.json`
- `publication_candidates.jsonl`
- `publications.curated.json`
- `publication_evidence.jsonl`
- `publication_audit.json`
- `research_theme_profile.json`

Synthesis step:

- `position_signals.json`
- `lab_summary_assessment.json`
- `lab_profile.json`
- `report.md`
- `lab_summary_audit.json`

All artifact paths must be relative paths under `lab_summaries/<lab_id>/`.

## Stop Conditions

- Site audit `fail` skips publication and synthesis.
- Publication audit `fail` skips synthesis.
- Synthesis audit `fail` marks the workflow failed.
- Skipped steps use `status: "skipped"`, `audit_status: "skipped"`, and `artifacts: {}`.

## Report Output

After worker artifacts and `lab_summary_manifest.json` exist, `build_lab_summary_html.py` writes:

```text
reports/lab-summaries/<task_id>/
  report.html
  report.md
  report_manifest.json
  assets/
  artifacts/
```

`build_report_index.py` scans only `reports/lab-summaries/*/report_manifest.json`.

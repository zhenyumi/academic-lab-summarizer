---
name: academic-lab-summarizer
description: "Use when an agent needs to run a full academic lab summary workflow for one known lab, PI profile, or lab homepage. Orchestrates lab-site-evidence-extraction, lab-publication-profile, and lab-profile-synthesis to produce publication analysis, open-position/recruitment signals, evidence-backed lab profile artifacts, and script-generated HTML/Markdown reports. Keep this workflow thin and do not reopen institution-level discovery."
---

# Academic Lab Summarizer

## Core Rule

Keep this skill as orchestration only. Read or invoke the worker skills for detailed rules:

1. `lab-site-evidence-extraction`
2. `lab-publication-profile`
3. `lab-profile-synthesis`

## Input

Start from one known lab. Required fields:

- `lab_url`
- `lab_name`
- `pi_name`
- `institution`

Optional:

- `biomedical_relevant`: Set true when PubMed should be a required Tier 1 publication source.

## Outputs

- `lab_summary_manifest.json`
- `reports/lab-summaries/<task_id>/report.html`
- `reports/lab-summaries/<task_id>/report.md`
- `reports/lab-summaries/<task_id>/report_manifest.json`

Worker artifacts are written under `lab_summaries/<lab_id>/`.

## Workflow

1. Create or read `lab_summary_input.json`.
2. Run `lab-site-evidence-extraction` and audit `lab_site_audit.json`.
3. Run `lab-publication-profile`; preserve the required source priority policy and audit `publication_audit.json`.
4. Run `lab-profile-synthesis`; require `position_signals.json`, `lab_summary_assessment.json`, `lab_profile.json`, `report.md`, and `lab_summary_audit.json`.
5. Write `lab_summary_manifest.json` with one step entry per worker.
6. Build the report package with `build_lab_summary_html.py`.
7. Refresh `reports/index.html` with `build_report_index.py`.

## Stop Conditions

- If site audit fails, skip publication profile and synthesis.
- If publication audit fails, skip synthesis.
- If synthesis audit fails, mark the workflow failed.
- Skipped steps must use `status: "skipped"`, `audit_status: "skipped"`, and `artifacts: {}`.

## Manifest Artifacts

The synthesis step must list:

- `position_signals.json`
- `lab_summary_assessment.json`
- `lab_profile.json`
- `report.md`
- `lab_summary_audit.json`

## Validation

```bash
python academic-lab-summarizer/scripts/validate_lab_summary_manifest.py --examples
python academic-lab-summarizer/scripts/smoke_report_outputs.py
```

## Template-First Execution

```bash
cp academic-lab-summarizer/templates/scripts/run_academic_lab_summarizer.py <run>/tools/

python <run>/tools/run_academic_lab_summarizer.py \
  --input <run>/lab_summaries/<lab_id>/lab_summary_input.json \
  --out <run>/lab_summaries/<lab_id> \
  --site-fixtures <run>/lab_summaries/<lab_id> \
  --pub-fixtures <run>/lab_summaries/<lab_id> \
  --fit-fixtures <run>/lab_summaries/<lab_id>
```

## References

- `references/academic-lab-summarizer-contract.md`: Manifest contract and data flow.

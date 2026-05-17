# Lab Profile Synthesis Usage Guide

Use this skill after site evidence extraction and publication profiling are complete.

## Minimal Flow

1. Read `lab_site_evidence.jsonl`, `publications.curated.json`, `publication_evidence.jsonl`, and `research_theme_profile.json`.
2. Build required `position_signals.json`.
3. Build `lab_summary_assessment.json`, `lab_profile.json`, and `report.md`.
4. Run `audit_lab_summary.py`.
5. Validate with `validate_lab_summary_artifacts.py`.
6. Build HTML/Markdown report package with `build_lab_summary_html.py`.

## Scripts

| Script | Purpose |
|---|---|
| `templates/scripts/run_lab_profile_synthesis.py` | Produces position signals, lab summary assessment, lab profile, report, and audit |
| `templates/scripts/audit_lab_summary.py` | Audits synthesis artifacts |
| `templates/scripts/build_lab_summary_html.py` | Builds `reports/lab-summaries/<task_id>/` |
| `scripts/validate_lab_summary_artifacts.py` | Validates artifact contracts |

## Quick Validation

```bash
python lab-profile-synthesis/scripts/validate_lab_summary_artifacts.py --examples
```

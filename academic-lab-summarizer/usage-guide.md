# Academic Lab Summarizer Usage Guide

Recommended direct invocation:

```text
/academic-lab-summarizer <lab-homepage-or-profile-url>
```

Use this for one known academic lab homepage, PI profile, or lab profile page.

## Operating Model

The workflow connects:

1. `lab-site-evidence-extraction`
2. `lab-publication-profile`
3. `lab-profile-synthesis`

Publication profiling and position signal analysis are required v1 outputs.

## Quick Validation

```bash
python academic-lab-summarizer/scripts/validate_lab_summary_manifest.py --examples
python academic-lab-summarizer/scripts/smoke_report_outputs.py
```

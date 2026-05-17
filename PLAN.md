# Academic Lab Summarizer Plan

## Summary

This repository is the standalone successor to the lab deep-dive portion of the older tool collection. It does not preserve Finder workflows or legacy report scanning. The new package focuses on one known academic lab at a time.

## Architecture

- `academic-lab-summarizer` is the thin workflow entry point.
- `lab-site-evidence-extraction` gathers source-backed website evidence.
- `lab-publication-profile` performs publication discovery, attribution review, curation, audit, and theme synthesis.
- `lab-profile-synthesis` creates the final profile, required position signals, report, and audit.

## Required Capabilities

- Publication source priority ships in v1 and must stay in the publication profile contract.
- Position analysis is mandatory and must cover PhD, masters, undergraduate, postdoc, research assistant, technician, lab manager, staff scientist, other explicit roles, and no-signal cases.
- Reports are generated from artifacts, not handwritten in the agent context.
- No Finder or legacy output compatibility is included.

## Validation Commands

```bash
python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py --examples
python lab-publication-profile/scripts/validate_publication_profile_artifacts.py --examples
python lab-profile-synthesis/scripts/validate_lab_summary_artifacts.py --examples
python academic-lab-summarizer/scripts/validate_lab_summary_manifest.py --examples
python academic-lab-summarizer/scripts/smoke_report_outputs.py
python academic-lab-summarizer/scripts/check_migration_policy.py
```

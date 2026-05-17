---
name: lab-profile-synthesis
description: "Use when an agent needs to synthesize an evidence-backed academic lab profile from already-collected lab site evidence and curated publication evidence. This skill must produce required open-position/recruitment analysis for PhD, postdoc, student, RA/research staff, technician, lab manager, staff scientist, and other explicit roles; it also summarizes recent publication themes and limitations. Do not perform new crawls or publication searches."
---

# Lab Profile Synthesis

## Core Rule

Synthesize only from existing artifacts. Every user-facing claim must trace to `evidence_refs`. Position availability is a required section: if no role-specific opening is found, write `none` or `unknown` with evidence limitations instead of omitting the topic.

## Inputs

- `lab_site_evidence.jsonl` from `lab-site-evidence-extraction`.
- `publications.curated.json`, `publication_evidence.jsonl`, and `research_theme_profile.json` from `lab-publication-profile`.
- Optional `lab_summary_input.json` with lab identity fields.

## Outputs

- `position_signals.json`: Required structured open-position/recruitment analysis.
- `lab_summary_assessment.json`: Evidence-backed assessment across research, publications, positions, methods, activity, and funding.
- `lab_profile.json`: Aggregated lab profile with evidence references.
- `report.md`: Human-readable report.
- `lab_summary_audit.json`: Quality audit.
- `reports/lab-summaries/<task_id>/report.html`, `report.md`, and `report_manifest.json`: Script-generated user-facing report package.

Worker artifacts are written under `lab_summaries/<lab_id>/`.

## Required Position Analysis

`position_signals.json` is mandatory, even when no openings are found.

Allowed `position_category` values:

- `phd`
- `masters`
- `undergraduate`
- `postdoc`
- `research_assistant`
- `technician`
- `lab_manager`
- `staff_scientist`
- `other`
- `none`

Allowed `signal_strength` values:

- `confirmed_opening`: Explicit role-specific opening with application details, deadline, start date, or clear availability.
- `likely_opening`: Role-specific recruitment language without enough details to confirm a current opening.
- `generic_recruitment`: Generic "join us" / "contact us" language without role specificity.
- `closed_or_past`: Filled, closed, or clearly past opportunity.
- `none`: No position signal found.
- `unknown`: Evidence is too unclear to classify.

Every signal must include `source_url`, `snippet`, `evidence_refs`, `confidence`, and `last_observed_or_posted_date` when available. Generic recruitment language must not be upgraded to `confirmed_opening`.

## Assessment Dimensions

`lab_summary_assessment.json` must cover:

- `research_focus`
- `publication_profile`
- `position_availability`
- `lab_activity_and_trajectory`
- `methods_and_approaches`
- `funding_indicators`

Each dimension includes `assessment`, `confidence`, `status`, `evidence_refs`, and `limitations`.

## Publication Overview

Use only confirmed and likely publications for research themes and important-publication summaries. Ambiguous or rejected publications may appear only in exclusions/limitations.

For important publications, preserve the structured `publication_overview` object:

- `one_line`
- `research_question`
- `key_finding`
- `methods`
- `significance`

Enhance empty fields only from abstracts, match rationale, publication evidence, or research themes. Do not fabricate methods or findings.

## Report Structure

The report must include:

```markdown
# Lab Profile: [lab_name]
## PI: [pi_name]
## Institution: [institution]
## Research Themes
## Important Recent Publications (Last 3-5 Years)
## Recent Publications
## Position Signals
## Lab Summary Assessment
## Methods and Approaches
## Funding/Resource Indicators
## Limitations
```

## Validation

```bash
python lab-profile-synthesis/scripts/validate_lab_summary_artifacts.py --examples
python lab-profile-synthesis/scripts/validate_lab_summary_artifacts.py /path/to/lab_summaries/<lab_id>
```

## Template-First Execution

```bash
mkdir -p <run>/tools
cp lab-profile-synthesis/templates/scripts/run_lab_profile_synthesis.py <run>/tools/
cp lab-profile-synthesis/templates/scripts/audit_lab_summary.py <run>/tools/
cp lab-profile-synthesis/templates/scripts/build_lab_summary_html.py <run>/tools/

python <run>/tools/run_lab_profile_synthesis.py \
  --input <run>/lab_summaries/<lab_id>/lab_summary_input.json \
  --out <run>/lab_summaries/<lab_id>

python <run>/tools/audit_lab_summary.py <run>/lab_summaries/<lab_id>
python <run>/tools/build_lab_summary_html.py <run>/lab_summaries/<lab_id>
```

## References

- `references/lab-profile-synthesis-contract.md`: Artifact schema and validation rules.

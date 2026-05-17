# Lab Profile Synthesis Contract

## Purpose

Defines the required synthesis outputs for one academic lab summary. This skill consumes already-collected site evidence and curated publication evidence. It does not crawl or search.

## Required Inputs

- `lab_site_evidence.jsonl`
- `publications.curated.json`
- `publication_evidence.jsonl`
- `research_theme_profile.json`

## Required Outputs

- `position_signals.json`
- `lab_summary_assessment.json`
- `lab_profile.json`
- `report.md`
- `lab_summary_audit.json`

## `position_signals.json`

Required even when no openings are found.

Allowed `position_category`:

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

Allowed `signal_strength`:

- `confirmed_opening`
- `likely_opening`
- `generic_recruitment`
- `closed_or_past`
- `none`
- `unknown`

Each signal object must include:

- `signal_id`
- `source_url`
- `snippet`
- `position_category`
- `signal_strength`
- `details`
- `evidence_refs`
- `confidence`
- `last_observed_or_posted_date` when available, otherwise `""`

Generic recruitment language can be reported as `generic_recruitment`, but must not be labeled `confirmed_opening`.

## `lab_summary_assessment.json`

Required dimensions:

- `research_focus`
- `publication_profile`
- `position_availability`
- `lab_activity_and_trajectory`
- `methods_and_approaches`
- `funding_indicators`

Each dimension must include `description`, `assessment`, `confidence`, `evidence_refs`, `status`, and `limitations`.

Allowed `overall_assessment`:

- `strong_profile`
- `usable_profile`
- `limited_profile`
- `insufficient_evidence`
- `unknown`

## `lab_profile.json`

Required top-level fields:

- `lab_id`, `lab_name`, `pi_name`, `institution`, `lab_url`
- `research_themes`
- `important_publications`
- `confirmed_publication_count`
- `likely_publication_count`
- `position_signal`
- `overall_assessment`
- `evidence_summary`
- `limitations`

Research themes and important publication summaries must use only confirmed and likely publications. Ambiguous and rejected publications may appear only in exclusions or limitations.

## `report.md`

Required sections:

1. `# Lab Profile: [lab_name]`
2. `## PI: [pi_name]`
3. `## Institution: [institution]`
4. `## Research Themes`
5. `## Important Recent Publications (Last 3-5 Years)`
6. `## Recent Publications`
7. `## Position Signals`
8. `## Lab Summary Assessment`
9. `## Methods and Approaches`
10. `## Funding/Resource Indicators`
11. `## Limitations`

## `lab_summary_audit.json`

Required fields:

- `lab_id`
- `status`: `pass`, `partial`, or `fail`
- `metrics`
- `blocking`
- `warnings`
- `repair_hints`

The audit must warn when generic recruitment language is present and must fail if there is no site evidence or no confirmed/likely publication evidence.

# Lab Site Evidence Contract

## Purpose

`lab_site_plan.json`, `lab_pages.jsonl`, `lab_site_evidence.jsonl`, and `lab_site_audit.json` define the inputs, fetched pages, evidence items, and quality audit for a single-lab site extraction.

## Input: `lab_summary_input.json`

```json
{
  "lab_id": "example-lab-001",
  "lab_name": "Doe Neural Development Lab",
  "pi_name": "Jane Doe",
  "institution": "Example University",
  "lab_url": "https://example.edu/doe-lab",
  "input_mode": "from_lab_url"
}
```

### Required Fields

- `lab_id`: Unique identifier for the lab in this lab summary.
- `lab_name`: Lab name.
- `pi_name`: PI name.
- `institution`: Institution name.
- `lab_url`: Official lab website URL.

### Optional Fields

- `input_mode`: `from_lab_url`.

## Output: `lab_site_plan.json`

```json
{
  "lab_url": "https://example.edu/doe-lab",
  "allowed_domains": ["example.edu"],
  "entry_urls": ["https://example.edu/doe-lab"],
  "crawl_limits": {
    "max_pages": 30,
    "max_depth": 2,
    "request_delay_seconds": 0.5
  },
  "extraction_focus": [
    "research_direction",
    "pi_info",
    "lab_member",
    "publication_ref",
    "position_signal"
  ],
  "known_risks": ["Lab site may have minimal content"]
}
```

### Required Fields

- `lab_url`: The lab website URL.
- `allowed_domains`: Domains permitted for crawling.
- `entry_urls`: Starting URLs for the lab site crawl.
- `crawl_limits`: Conservative page/depth limits.

## Output: `lab_pages.jsonl`

One JSON object per line representing a fetched page from the lab site:

```json
{
  "page_id": 1,
  "url": "https://example.edu/doe-lab",
  "depth": 0,
  "status_code": 200,
  "title": "Doe Neural Development Lab",
  "text_length": 3420,
  "links": [
    "https://example.edu/doe-lab/people",
    "https://example.edu/doe-lab/publications"
  ],
  "fetched_at": "2026-05-15T10:30:00Z"
}
```

### Required Fields

- `page_id`: Unique integer ID within this extraction.
- `url`: Absolute URL of the fetched page.
- `depth`: Crawl depth from entry URL (0 for entry page).

### Optional Fields

- `status_code`: HTTP status code.
- `title`: Page title extracted from `<title>`.
- `text_length`: Length of extracted text content in characters.
- `links`: List of absolute URLs found on the page.
- `fetched_at`: ISO 8601 timestamp of when the page was fetched.

## Output: `lab_site_evidence.jsonl`

One JSON object per line:

```json
{
  "evidence_id": 1,
  "lab_id": "example-lab-001",
  "source_url": "https://example.edu/doe-lab",
  "snippet": "The Doe Lab studies neural crest cell migration in zebrafish.",
  "claim_type": "research_direction",
  "evidence_quality": "research_description",
  "extraction_status": "extracted",
  "confidence": "high"
}
```

### Required Fields

- `evidence_id`: Unique integer ID within this extraction.
- `lab_id`: Lab identifier.
- `source_url`: Page URL where the evidence was found.
- `snippet`: Exact or closely paraphrased text from the page.
- `claim_type`: One of `research_direction`, `pi_info`, `lab_member`, `publication_ref`, `position_signal`, `lab_url`, `facility`, `other`.
- `evidence_quality`: One of `research_description`, `profile_snippet`, `link_text_only`, `none`.
- `extraction_status`: One of `extracted`, `partial`, `unavailable`, `skipped`.

At least one extracted `research_direction` evidence item is required for downstream profile synthesis. If no research-direction evidence can be extracted, the artifact is invalid rather than silently passing with only metadata or PI-info rows.

### Optional Fields

- `confidence`: `high`, `medium`, `low`, or `unknown`.

## Output: `lab_site_audit.json`

```json
{
  "status": "partial",
  "metrics": {
    "pages_fetched": 5,
    "evidence_items": 8,
    "research_direction_items": 2,
    "position_signal_items": 1,
    "weak_evidence_ratio": 0.25,
    "pi_info_complete": true
  },
  "blocking_failures": [],
  "warnings": [
    "One position signal is based on generic join-us language."
  ],
  "repair_hints": []
}
```

### Required Fields

- `status`: `pass`, `partial`, or `fail`.
- `metrics`: Object with numeric quality indicators.
- `blocking_failures`: Array of failure descriptions (empty if passing).
- `warnings`: Array of non-blocking quality concerns.

## Traceability Rules

- Every evidence item must have `source_url` and `snippet`.
- Evidence with `evidence_quality: link_text_only` must not be used to summarize research direction.
- Evidence with `extraction_status: unavailable` or `skipped` must not be treated as supporting any claim.

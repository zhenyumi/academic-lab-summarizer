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

#### Optional Provenance Fields

The following optional fields may appear on `lab_site_evidence.jsonl` items to improve provenance traceability. All are default-absent. Existing artifacts without them remain valid. The template runner does not populate them. Future crawlers and extractors may populate them.

| Field | Type | Purpose |
|---|---|---|
| `page_title` | string or null | Title of the page where the evidence was found |
| `fetched_at` | ISO 8601 string or null | Timestamp when the page was fetched |
| `content_hash` | string or null | Hash of the page content at fetch time (for change detection) |
| `selector_or_offset` | string or null | CSS selector or character offset locating the snippet within the page |
| `language` | string or null | Detected language of the snippet (e.g., `"en"`, `"zh"`) |
| `evidence_rationale` | string or null | Brief explanation of why this snippet was classified under this `claim_type` |

## Crawler Roadmap (not yet implemented)

> **Status**: This section documents future design intent. No crawler ships in the current package. The template runner processes synthetic fixtures only. Future adapters must implement these behaviors when building real crawl logic.

### robots.txt and Crawl-Delay Compliance

Future crawlers must fetch and parse `robots.txt` before crawling. Respect `Crawl-delay` directives. If `Crawl-delay` is specified, use it as the minimum delay between requests. If `robots.txt` disallows a path, skip it.

### Sitemap Discovery

Check for `sitemap.xml` or `Sitemap` directives in `robots.txt`. Use sitemaps to discover pages that may not be reachable from the navigation. Prioritize sitemap URLs that match known lab-relevant paths.

### Canonical URL Resolution

Resolve `<link rel="canonical">` tags to avoid fetching duplicate pages under different URL variants (trailing slash, query parameters, `www` vs non-`www`).

### Page-Type Prioritization

Prioritize crawling in this order:

1. **About / Research**: `about`, `research`, `projects`, `focus` — highest value for research direction extraction.
2. **People / Publications**: `people`, `team`, `members`, `publications`, `papers` — PI info, lab members, publication references.
3. **Join Us / Openings**: `join`, `openings`, `positions`, `recruitment`, `opportunities` — position signals.
4. **Other pages**: Lower priority; crawl if depth and page limits allow.

### Content Cleanup

Strip the following from extracted text before evidence extraction:

- Navigation bars and menus
- Page footers (copyright, contact info, social links)
- Cookie consent banners
- Sidebar widgets (recent posts, tag clouds, social feeds)

### PDF Link Handling

Detect links ending in `.pdf` or with `Content-Type: application/pdf`. Record them as potential evidence sources but do not attempt inline extraction. Note the PDF URL in the evidence item's `source_url` with a `snippet` indicating the PDF exists.

### Failure Retry

On HTTP errors (4xx/5xx), retry with exponential backoff: 1s, 2s, 4s. Maximum 3 retries per page. After 3 failures, record the page with `status_code` set to the error code and continue.

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

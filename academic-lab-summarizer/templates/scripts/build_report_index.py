"""Build the Academic Lab Summarizer report index.

The index only recognizes new-format reports under:

    reports/lab-summaries/*/report_manifest.json

It intentionally scans only new Academic Lab Summarizer report manifests.
"""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
from typing import Any
import json


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def rel(path: Path, base: Path) -> str:
    return Path(os.path.relpath(path.resolve(), base.resolve())).as_posix()


def scan_lab_summary_reports(reports_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    base = reports_dir / "lab-summaries"
    if not base.is_dir():
        return results
    for manifest_path in sorted(base.glob("*/report_manifest.json")):
        task_dir = manifest_path.parent
        data = read_json(manifest_path, {})
        if not isinstance(data, dict):
            continue
        report_path = task_dir / data.get("primary_report", "report.html")
        markdown_path = task_dir / data.get("markdown_report", "report.md")
        results.append({
            "id": data.get("task_id") or task_dir.name,
            "label": data.get("label") or task_dir.name,
            "href": rel(report_path, reports_dir),
            "markdown_href": rel(markdown_path, reports_dir) if markdown_path.exists() else "",
            "status": data.get("status", "unknown"),
            "audit_status": data.get("audit_status", "unknown"),
            "warnings_count": data.get("warnings_count", 0),
            "pi_name": data.get("pi_name", ""),
            "overall_assessment": data.get("overall_assessment", ""),
            "created_at": data.get("created_at", ""),
        })
    return results


def styles() -> str:
    return """
:root { color-scheme: light; --border: #d9e2ec; --muted: #52616b; --bg: #f7fafc; --ink: #1f2933; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
header { background: #fff; border-bottom: 1px solid var(--border); padding: 24px; }
main { max-width: 1120px; margin: 0 auto; padding: 24px; }
a { color: #0b5cad; overflow-wrap: anywhere; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }
.metric { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 14px; }
.metric strong { display: block; font-size: 24px; }
.status, .assessment { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #edf2f7; font-size: 12px; }
.status.fail { background: #fed7d7; }
.status.partial { background: #feebc8; }
.status.pass, .status.completed { background: #c6f6d5; }
.muted { color: var(--muted); }
.report-list { list-style: none; padding: 0; }
.report-item { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.report-item a { font-weight: 600; text-decoration: none; font-size: 16px; }
.report-item a:hover { text-decoration: underline; }
.report-meta { font-size: 13px; color: var(--muted); }
.sub-links a { font-size: 12px; font-weight: 500; margin-right: 10px; }
h2 { border-bottom: 1px solid var(--border); padding-bottom: 8px; }
""".strip() + "\n"


def render_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="muted">No lab summary reports found.</p>'
    html_items = ""
    for r in sorted(items, key=lambda item: (item.get("created_at", ""), item.get("id", "")), reverse=True):
        markdown_link = f'<a href="{e(r["markdown_href"])}">Markdown</a>' if r.get("markdown_href") else ""
        details = []
        if r.get("pi_name"):
            details.append(f"PI: {e(r['pi_name'])}")
        if r.get("warnings_count") not in ("", None):
            details.append(f"{e(r['warnings_count'])} warnings")
        details.append(e(r.get("id", "")))
        assessment = (
            f'<span class="assessment">{e(r.get("overall_assessment", ""))}</span>'
            if r.get("overall_assessment") else ""
        )
        html_items += f"""
        <li class="report-item">
          <div>
            <a href="{e(r['href'])}">{e(r['label'])}</a>
            <div class="report-meta">{' | '.join(details)}</div>
            <div class="sub-links">{markdown_link}</div>
          </div>
          <div>
            {assessment}
            <span class="status {e(r.get('status', 'unknown'))}" style="margin-left:4px">{e(r.get('status', 'unknown'))}</span>
          </div>
        </li>"""
    return '<ul class="report-list">' + html_items + '</ul>'


def build(workspace_dir: Path) -> Path:
    reports_dir = workspace_dir / "reports"
    assets_dir = reports_dir / "assets"
    reports_dir.mkdir(parents=True, exist_ok=True)

    lab_reports = scan_lab_summary_reports(reports_dir)
    write_text(assets_dir / "styles.css", styles())

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Academic Lab Summarizer Reports</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <header>
    <h1>Academic Lab Summarizer Reports</h1>
    <p class="muted">Unified index for lab summary reports stored under reports/lab-summaries/.</p>
  </header>
  <main>
    <section class="summary">
      <div class="metric"><strong>{len(lab_reports)}</strong><span>Lab summary reports</span></div>
    </section>

    <section>
      <h2>Lab Summary Reports</h2>
      {render_items(lab_reports)}
    </section>
  </main>
</body>
</html>
"""
    write_text(reports_dir / "index.html", html_doc)

    root_index = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Academic Lab Summarizer</title>
  <meta http-equiv="refresh" content="0; url=reports/index.html">
  <link rel="stylesheet" href="reports/assets/styles.css">
</head>
<body>
  <main>
    <p><a href="reports/index.html">Open Academic Lab Summarizer Reports</a></p>
  </main>
</body>
</html>
"""
    write_text(workspace_dir / "academic-lab-summarizer-reports.html", root_index)
    return reports_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Academic Lab Summarizer report index.")
    parser.add_argument("workspace_dir", type=Path, help="Workspace root containing reports/")
    args = parser.parse_args()
    reports_dir = build(args.workspace_dir)
    print(f"Report index written to {reports_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

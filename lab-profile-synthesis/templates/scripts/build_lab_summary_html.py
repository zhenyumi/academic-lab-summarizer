"""Copyable template to build Lab Summary reports from artifacts.

The canonical user-facing output lives under:

    reports/lab-summaries/<task_id>/
      report.html
      report.md
      report_manifest.json
      assets/
      artifacts/

Only the new Academic Lab Summarizer report package is generated.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str, fallback: str = "lab-summary") -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return text[:80] or fallback


def workspace_for_lab_summaries(lab_summaries_dir: Path) -> Path:
    resolved = lab_summaries_dir.resolve()
    if resolved.name == "artifacts" and len(resolved.parents) >= 4:
        if resolved.parents[1].name == "lab-summaries" and resolved.parents[2].name == "reports":
            return resolved.parents[3]
    if resolved.parent.name == "lab_summaries":
        if resolved.parent.parent.name == "runs":
            return resolved.parent.parent.parent
        return resolved.parent.parent
    return resolved.parent


def reserve_task_dir(base_dir: Path, preferred_task_id: str) -> Path:
    task_dir = base_dir / preferred_task_id
    if not task_dir.exists():
        return task_dir
    for i in range(2, 100):
        candidate = base_dir / f"{preferred_task_id}-{i:02d}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Unable to reserve report directory under {base_dir}")


def report_dir_for_lab_summaries(lab_summaries_dir: Path, profile: dict[str, Any], manifest: dict[str, Any]) -> Path:
    resolved = lab_summaries_dir.resolve()
    if resolved.name == "artifacts" and resolved.parent.parent.name == "lab-summaries":
        return resolved.parent
    workspace = workspace_for_lab_summaries(lab_summaries_dir)
    label = (
        profile.get("lab_name")
        or manifest.get("lab_name")
        or profile.get("pi_name")
        or manifest.get("pi_name")
        or urlparse(profile.get("lab_url") or manifest.get("lab_url") or "").netloc
        or lab_summaries_dir.name
    )
    task_id = f"{utc_timestamp()}-{slugify(str(label), lab_summaries_dir.name)}"
    return reserve_task_dir(workspace / "reports" / "lab-summaries", task_id)


def relpath(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def copy_artifacts(lab_summaries_dir: Path, artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(lab_summaries_dir.iterdir()) if lab_summaries_dir.exists() else []:
        if src.name in {"site", "assets"}:
            continue
        dst = artifacts_dir / src.name
        if src.is_file() and src.suffix in {".json", ".jsonl", ".md"}:
            shutil.copy2(src, dst)
        elif src.is_dir() and src.name == "tools" and not dst.exists():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )


def md_to_html(text: str) -> str:
    """Very simple markdown-to-HTML for the report sections."""
    lines = text.split("\n")
    out: list[str] = []
    in_table = False
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_table:
                continue
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("")
            continue
        if stripped.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{e(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{e(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{e(stripped[4:])}</h3>")
            continue
        if re.match(r"^\|[-\s|:]+\|$", stripped):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                out.append('<table class="md-table">')
                in_table = True
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            row = "".join(f"<td>{e(c)}</td>" for c in cells)
            out.append(f"<tr>{row}</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item_text = e(stripped[2:])
            item_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item_text)
            out.append(f"<li>{item_text}</li>")
            continue
        if stripped == "---":
            out.append("<hr>")
            continue
        text_line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", e(stripped))
        text_line = re.sub(r"\[(pub:\d+|site:\d+)\]", r'<span class="ref">[\1]</span>', text_line)
        out.append(f"<p>{text_line}</p>")
    if in_table:
        out.append("</table>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def styles() -> str:
    return """
:root {
  color-scheme: light;
  --ink: oklch(22% 0.02 190);
  --muted: oklch(50% 0.015 190);
  --border: oklch(88% 0.01 190);
  --bg: oklch(97% 0.005 190);
  --surface: oklch(99% 0.005 190);
  --accent: oklch(50% 0.13 190);
  --accent-hover: oklch(42% 0.14 190);
  --ok: oklch(55% 0.12 145);
  --ok-text: oklch(32% 0.08 145);
  --warn: oklch(80% 0.1 75);
  --warn-text: oklch(38% 0.1 75);
  --err: oklch(78% 0.08 25);
  --err-text: oklch(38% 0.12 25);
  --tint-bg: oklch(95% 0.008 190);
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.25rem;
  --text-xl: 1.5rem;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
}
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  font-size: var(--text-base);
  line-height: 1.5;
  color: var(--ink);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { text-wrap: balance; margin: 0; }
header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: var(--space-6);
}
header h1 {
  font-size: var(--text-xl);
  font-weight: 700;
  margin-bottom: var(--space-2);
  line-height: 1.3;
}
header p { margin: 0 0 var(--space-1); font-size: var(--text-sm); }
main {
  max-width: 72rem;
  margin: 0 auto;
  padding: var(--space-6);
}
a {
  color: var(--accent);
  overflow-wrap: anywhere;
  text-decoration: none;
}
a:hover { color: var(--accent-hover); text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-6) var(--space-8);
  padding: var(--space-4) 0;
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--border);
}
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-value {
  font-size: var(--text-lg);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.stat-label {
  font-size: var(--text-xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.muted { color: var(--muted); }
.status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: 0.02em;
  background: var(--tint-bg);
  color: var(--muted);
}
.status.pass, .status.completed, .status.review { background: var(--ok); color: var(--ok-text); }
.status.partial { background: var(--warn); color: var(--warn-text); }
.status.fail { background: var(--err); color: var(--err-text); }
.fit-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: var(--text-sm);
  font-weight: 600;
  background: var(--tint-bg);
  color: var(--muted);
}
.fit-badge.excellent, .fit-badge.promising { background: var(--ok); color: var(--ok-text); }
.fit-badge.possible { background: var(--warn); color: var(--warn-text); }
.fit-badge.unlikely { background: var(--err); color: var(--err-text); }
section { margin-bottom: var(--space-8); }
section h2 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: var(--space-4);
  line-height: 1.3;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: var(--space-4);
  margin-bottom: var(--space-3);
}
.card h3 {
  font-size: var(--text-base);
  font-weight: 600;
  margin-bottom: var(--space-2);
}
.theme { margin-bottom: var(--space-4); padding-bottom: var(--space-3); border-bottom: 1px solid var(--border); }
.theme:last-child { border-bottom: none; }
.theme-title { font-weight: 600; font-size: var(--text-sm); }
.theme-detail { font-size: var(--text-sm); color: var(--muted); margin-top: var(--space-1); }
.confidence {
  font-size: var(--text-xs);
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--tint-bg);
  color: var(--muted);
  margin-left: var(--space-2);
}
.confidence.high { background: var(--ok); color: var(--ok-text); }
.confidence.medium { background: var(--warn); color: var(--warn-text); }
.confidence.low { background: var(--err); color: var(--err-text); }
.ref {
  font-family: monospace;
  font-size: var(--text-xs);
  color: var(--accent);
}
.md-table {
  border-collapse: collapse;
  width: 100%;
  margin: var(--space-3) 0;
  font-size: var(--text-sm);
}
.md-table th, .md-table td {
  border: 1px solid var(--border);
  padding: var(--space-2) var(--space-3);
  text-align: left;
}
.md-table th {
  background: var(--tint-bg);
  font-weight: 600;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
}
.md-table td { vertical-align: top; }
.limitations {
  background: oklch(97% 0.01 25);
  border: 1px solid var(--err);
  border-radius: 6px;
  padding: var(--space-4);
}
.limitations h2 { color: var(--err-text); }
.limitations li { margin-bottom: var(--space-2); font-size: var(--text-sm); }
.audit-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-8);
}
.audit-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: var(--space-4);
}
.audit-card h3 { font-size: var(--text-sm); font-weight: 600; margin-bottom: var(--space-2); }
.audit-card .audit-metrics { font-size: var(--text-sm); }
.audit-card .audit-warnings { font-size: var(--text-sm); margin-top: var(--space-2); }
.artifacts { margin-bottom: var(--space-8); }
.artifacts a {
  display: block;
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}
.pub-overview { font-size: var(--text-sm); color: var(--muted); margin-top: 2px; }
.pub-overview-limited { font-size: var(--text-xs); font-style: italic; color: var(--muted); }
.pub-one-line { font-size: var(--text-sm); margin-top: var(--space-1); }
.pub-meta { font-size: var(--text-sm); color: var(--muted); margin-top: var(--space-1); }
.pub-refs { font-size: var(--text-xs); margin-top: var(--space-1); }
.position-detail { font-size: var(--text-sm); }
.position-refs { font-size: var(--text-xs); color: var(--muted); }
.fit-refs { font-size: var(--text-xs); }
.fit-status { margin-left: var(--space-2); }
.overall-status { margin-left: var(--space-2); }
@media (max-width: 640px) {
  header, main { padding: var(--space-4); }
  .stats { gap: var(--space-4); }
  .audit-section { grid-template-columns: 1fr; }
}
""".strip() + "\n"


def normalize_report_md(lab_summaries_dir: Path, profile: dict[str, Any]) -> str:
    report_md = read_text(lab_summaries_dir / "report.md")
    if report_md:
        return report_md
    lab_name = profile.get("lab_name", "Unknown Lab")
    pi_name = profile.get("pi_name", "Unknown PI")
    institution = profile.get("institution", "")
    return f"# Lab Profile: {lab_name}\n\n## PI: {pi_name}\n\n## Institution: {institution}\n\nNo report.md was available.\n"


def render_html(
    lab_summaries_dir: Path,
    report_md: str,
    profile: dict[str, Any],
    fit_assessment: dict[str, Any],
    positions: dict[str, Any],
    site_audit: dict[str, Any],
    pub_audit: dict[str, Any],
    fit_audit: dict[str, Any],
    manifest: dict[str, Any],
    artifact_prefix: str,
    asset_prefix: str,
) -> str:
    lab_name = profile.get("lab_name", manifest.get("lab_name", "Unknown Lab"))
    pi_name = profile.get("pi_name", manifest.get("pi_name", "Unknown PI"))
    institution = profile.get("institution", manifest.get("institution", ""))
    lab_url = profile.get("lab_url", manifest.get("lab_url", ""))
    overall_assessment = profile.get("overall_assessment", "unknown")
    position_signal = profile.get("position_signal", "unknown")
    themes = profile.get("research_themes", [])
    limitations = profile.get("limitations", [])
    evidence_summary = profile.get("evidence_summary", {})
    overall_status = manifest.get("overall_status", "unknown")
    report_html = md_to_html(report_md) if report_md else "<p>No report available.</p>"

    themes_html = ""
    for t in themes:
        conf = t.get("confidence", "unknown")
        refs = t.get("evidence_refs", [])
        refs_str = " ".join(f'<span class="ref">[{e(r)}]</span>' for r in refs)
        themes_html += f"""
        <div class="theme">
          <div><span class="theme-title">{e(t.get("theme", ""))}</span><span class="confidence {e(conf)}">{e(conf)}</span></div>
          <div class="theme-detail">{refs_str}</div>
        </div>"""

    important_pubs_html = ""
    for pub in profile.get("important_publications", []):
        refs_str = " ".join(f'<span class="ref">[{e(r)}]</span>' for r in pub.get("evidence_refs", []))
        ov = pub.get("publication_overview", {})
        ov_parts = []
        if ov.get("research_question"):
            ov_parts.append(f"<strong>Research question:</strong> {e(ov['research_question'])}")
        if ov.get("key_finding"):
            ov_parts.append(f"<strong>Key finding:</strong> {e(ov['key_finding'])}")
        if ov.get("methods"):
            ov_parts.append(f"<strong>Methods:</strong> {e(ov['methods'])}")
        if ov.get("significance"):
            ov_parts.append(f"<strong>Significance:</strong> {e(ov['significance'])}")
        ov_detail_html = f'<div class="pub-overview">{"<br>".join(ov_parts)}</div>' if ov_parts else ""
        limited_html = '<div class="pub-overview-limited">[Overview limited: no abstract available]</div>' if ov and not any([ov.get("research_question"), ov.get("key_finding"), ov.get("methods")]) else ""
        overview_line = f'<div class="pub-one-line">{e(ov.get("one_line", ""))}</div>' if ov.get("one_line") else ""
        important_pubs_html += f"""
        <div class="theme">
          <div><span class="theme-title">{e(pub.get("title", "Untitled"))}</span> ({e(pub.get("year", "?"))})</div>
          <div class="pub-meta">{e(pub.get("venue", ""))} | {e(pub.get("publication_type", ""))} | {e(pub.get("match_tier", ""))}{" | theme: " + e(pub["theme"]) if pub.get("theme") else ""}</div>
          {overview_line}{ov_detail_html}{limited_html}
          <div class="pub-refs">{refs_str}</div>
        </div>"""
    if not important_pubs_html:
        important_pubs_html = '<p class="muted">No important recent publications available.</p>'

    positions_html = ""
    signals = positions.get("signals", []) if isinstance(positions, dict) else positions if isinstance(positions, list) else []
    for sig in signals:
        refs = sig.get("evidence_refs", [])
        refs_str = " ".join(f'<span class="ref">[{e(r)}]</span>' for r in refs)
        positions_html += f"""
        <div class="card">
          <div><strong>{e(sig.get("signal_strength", "unknown"))}</strong> | {e(sig.get("position_category", ""))}</div>
          <div class="position-detail">{e(sig.get("details", sig.get("snippet", "")))}</div>
          <div class="position-refs">{refs_str}</div>
        </div>"""
    if not positions_html:
        positions_html = '<p class="muted">No position signals detected.</p>'

    fit_html = ""
    dimensions = fit_assessment.get("dimensions", [])
    if isinstance(dimensions, dict):
        dimensions = [
            {"dimension": name, **data}
            for name, data in dimensions.items()
            if isinstance(data, dict)
        ]
    for dim in dimensions if isinstance(dimensions, list) else []:
        if not isinstance(dim, dict):
            continue
        dim_name = dim.get("dimension", "unknown")
        status_val = dim.get("status", "unknown")
        conf = dim.get("confidence", "unknown")
        assessment = dim.get("assessment", "")
        refs = dim.get("evidence_refs", [])
        refs_str = " ".join(f'<span class="ref">[{e(r)}]</span>' for r in refs)
        fit_html += f"""
        <tr>
          <td>{e(str(dim_name).replace("_", " ").title())}</td>
          <td><span class="status {e(status_val)}">{e(status_val)}</span></td>
          <td>{e(conf)}</td>
          <td>{e(assessment)}<br><span class="fit-refs">{refs_str}</span></td>
        </tr>"""

    def audit_card(title: str, audit_data: dict[str, Any]) -> str:
        st = audit_data.get("status", "unknown")
        metrics_items = list((audit_data.get("metrics") or {}).items())[:6]
        warnings = (audit_data.get("warnings") or [])[:3]
        metrics_html = " ".join(f'<span class="muted">{e(k)}: {e(v)}</span>' for k, v in metrics_items)
        warn_html = "".join(f"<li>{e(w)}</li>" for w in warnings)
        return f"""
        <div class="audit-card">
          <h3>{e(title)} <span class="status {e(st)}">{e(st)}</span></h3>
          <div class="audit-metrics">{metrics_html}</div>
          {"<ul class='audit-warnings'>" + warn_html + "</ul>" if warn_html else ""}
        </div>"""

    artifacts_html = ""
    json_files = sorted(lab_summaries_dir.glob("*.json")) + sorted(lab_summaries_dir.glob("*.jsonl"))
    for f in json_files:
        artifacts_html += f'<a href="{artifact_prefix}{e(f.name)}">{e(f.name)}</a>\n'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lab Summary: {e(lab_name)}</title>
  <link rel="stylesheet" href="{asset_prefix}assets/styles.css">
</head>
<body>
  <header>
    <h1>{e(lab_name)}</h1>
    <p>PI: {e(pi_name)} | Institution: {e(institution)}</p>
    {f'<p><a href="{e(lab_url)}">{e(lab_url)}</a></p>' if lab_url else ""}
    <p>
      <span class="fit-badge {e(overall_assessment)}">Assessment: {e(overall_assessment)}</span>
      <span class="status {e(overall_status)} overall-status">Overall: {e(overall_status)}</span>
    </p>
  </header>
  <main>
    <section class="stats" aria-label="Summary">
      <div class="stat"><span class="stat-value">{e(len(themes))}</span><span class="stat-label">Research themes</span></div>
      <div class="stat"><span class="stat-value">{e(profile.get("confirmed_publication_count", 0))}</span><span class="stat-label">Confirmed pubs</span></div>
      <div class="stat"><span class="stat-value">{e(profile.get("likely_publication_count", 0))}</span><span class="stat-label">Likely pubs</span></div>
      <div class="stat"><span class="stat-value">{e(evidence_summary.get("site_evidence_count", 0))}</span><span class="stat-label">Site evidence</span></div>
      <div class="stat"><span class="stat-value">{e(evidence_summary.get("publication_evidence_count", 0))}</span><span class="stat-label">Pub evidence</span></div>
      <div class="stat"><span class="stat-value">{e(position_signal)}</span><span class="stat-label">Position signal</span></div>
    </section>

    <section aria-label="Research Themes"><h2>Research Themes</h2>{themes_html if themes_html else '<p class="muted">No research themes available.</p>'}</section>
    <section aria-label="Important Publications"><h2>Important Recent Publications (Last 3-5 Years)</h2>{important_pubs_html}</section>
    <section aria-label="Position Signals"><h2>Position Signals</h2>{positions_html}</section>

    <section aria-label="Fit Assessment">
      <h2>Lab Summary Assessment</h2>
      {f'<div class="fit-badge {e(overall_assessment)}">Overall assessment: {e(overall_assessment)}</div>' if overall_assessment != "unknown" else ""}
      <table class="md-table">
        <thead><tr><th>Dimension</th><th>Status</th><th>Confidence</th><th>Assessment</th></tr></thead>
        <tbody>{fit_html}</tbody>
      </table>
    </section>

    <section aria-label="Full Report"><h2>Full Report</h2><div class="card">{report_html}</div></section>

    <section class="audit-section" aria-label="Audits">
      {audit_card("Site Audit", site_audit)}
      {audit_card("Publication Audit", pub_audit)}
      {audit_card("Lab Summary Audit", fit_audit)}
    </section>

    {f'<section class="limitations" aria-label="Limitations"><h2>Limitations</h2><ul>{"".join(f"<li>{e(lim)}</li>" for lim in limitations)}</ul></section>' if limitations else ""}

    <section class="artifacts" aria-label="Raw Artifacts">
      <h2>Raw Artifacts</h2>
      {artifacts_html}
    </section>
  </main>
</body>
</html>
"""


def build(lab_summaries_dir: Path) -> Path:
    profile = read_json(lab_summaries_dir / "lab_profile.json", {})
    fit_assessment = read_json(lab_summaries_dir / "lab_summary_assessment.json", {})
    positions = read_json(lab_summaries_dir / "position_signals.json", {})
    site_audit = read_json(lab_summaries_dir / "lab_site_audit.json", {})
    pub_audit = read_json(lab_summaries_dir / "publication_audit.json", {})
    fit_audit = read_json(lab_summaries_dir / "lab_summary_audit.json", {})
    manifest = read_json(lab_summaries_dir / "lab_summary_manifest.json", {})
    report_md = normalize_report_md(lab_summaries_dir, profile)

    report_dir = report_dir_for_lab_summaries(lab_summaries_dir, profile, manifest)
    artifacts_dir = report_dir / "artifacts"
    assets_dir = report_dir / "assets"
    copy_artifacts(lab_summaries_dir, artifacts_dir)
    write_text(assets_dir / "styles.css", styles())
    write_text(report_dir / "report.md", report_md)

    html_doc = render_html(
        lab_summaries_dir,
        report_md,
        profile,
        fit_assessment,
        positions,
        site_audit,
        pub_audit,
        fit_audit,
        manifest,
        artifact_prefix="artifacts/",
        asset_prefix="",
    )
    write_text(report_dir / "report.html", html_doc)

    workspace = workspace_for_lab_summaries(lab_summaries_dir)
    warnings_count = (
        len(site_audit.get("warnings", []))
        + len(pub_audit.get("warnings", []))
        + len(fit_audit.get("warnings", []))
    )
    report_manifest = {
        "task_id": report_dir.name,
        "task_type": "lab-summary",
        "label": profile.get("lab_name") or manifest.get("lab_name") or report_dir.name,
        "source_url": profile.get("lab_url") or manifest.get("lab_url", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "primary_report": "report.html",
        "markdown_report": "report.md",
        "artifact_dir": "artifacts",
        "status": manifest.get("overall_status", fit_audit.get("status", "unknown")),
        "audit_status": fit_audit.get("status", "unknown"),
        "warnings_count": warnings_count,
        "lab_id": profile.get("lab_id") or manifest.get("lab_id", ""),
        "pi_name": profile.get("pi_name") or manifest.get("pi_name", ""),
        "overall_assessment": profile.get("overall_assessment", "unknown"),
        "report_path": relpath(report_dir / "report.html", workspace),
        "markdown_path": relpath(report_dir / "report.md", workspace),
    }
    write_json(report_dir / "report_manifest.json", report_manifest)

    return report_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Lab Summary reports from artifacts.")
    parser.add_argument("lab_summaries_dir", type=Path)
    args = parser.parse_args()
    report_dir = build(args.lab_summaries_dir)
    print(f"Lab Summary report written to {report_dir / 'report.html'}")
    print(f"Markdown report written to {report_dir / 'report.md'}")
    print(f"Report manifest written to {report_dir / 'report_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

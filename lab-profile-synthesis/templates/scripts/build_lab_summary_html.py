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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.load(line) if False else json.loads(line))
    return items


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
  --ink: oklch(20% 0.018 250);
  --muted: oklch(48% 0.014 250);
  --border: oklch(90% 0.008 250);
  --bg: oklch(97.5% 0.004 250);
  --surface: oklch(99.5% 0.003 250);
  --accent: oklch(48% 0.15 260);
  --accent-hover: oklch(40% 0.17 260);
  --accent-subtle: oklch(94% 0.02 260);
  --ok: oklch(52% 0.13 150);
  --ok-text: oklch(28% 0.08 150);
  --ok-bg: oklch(95% 0.025 150);
  --warn: oklch(78% 0.11 80);
  --warn-text: oklch(35% 0.1 80);
  --warn-bg: oklch(96% 0.025 80);
  --err: oklch(72% 0.1 25);
  --err-text: oklch(35% 0.13 25);
  --err-bg: oklch(96% 0.025 25);
  --tint-bg: oklch(95% 0.008 250);
  --nav-bg: oklch(99% 0.004 250);
  --nav-shadow: oklch(80% 0.005 250 / 12%);

  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1.0625rem;
  --text-lg: 1.3125rem;
  --text-xl: 1.625rem;
  --text-2xl: 2rem;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  --nav-height: 48px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-full: 999px;
}

[data-text-size="sm"] {
  --text-xs: 0.6875rem;
  --text-sm: 0.8125rem;
  --text-base: 0.9375rem;
  --text-lg: 1.1875rem;
  --text-xl: 1.4375rem;
  --text-2xl: 1.75rem;
}
[data-text-size="lg"] {
  --text-xs: 0.8125rem;
  --text-sm: 0.9375rem;
  --text-base: 1.1875rem;
  --text-lg: 1.5rem;
  --text-xl: 1.875rem;
  --text-2xl: 2.375rem;
}

*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--ink);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-kerning: normal;
}
h1, h2, h3 { text-wrap: balance; margin: 0; }

.sticky-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--nav-bg);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 1px 3px var(--nav-shadow);
  height: var(--nav-height);
  display: flex;
  align-items: center;
  padding: 0 var(--space-6);
  gap: var(--space-2);
}
.sticky-nav .nav-links {
  display: flex;
  gap: var(--space-1);
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}
.sticky-nav .nav-links::-webkit-scrollbar { display: none; }
.sticky-nav a {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--muted);
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.sticky-nav a:hover { background: var(--tint-bg); color: var(--ink); }
.sticky-nav a:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.sticky-nav a.active { background: var(--accent-subtle); color: var(--accent); font-weight: 600; }

.font-toggle {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
}
.font-toggle button {
  border: none;
  background: transparent;
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  line-height: 1;
  font-family: inherit;
}
.font-toggle button:hover { background: var(--tint-bg); color: var(--ink); }
.font-toggle button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.font-toggle button.active { background: var(--accent); color: oklch(99% 0.003 260); }

header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: var(--space-8) var(--space-6);
}
header h1 {
  font-size: var(--text-2xl);
  font-weight: 700;
  margin-bottom: var(--space-2);
  line-height: 1.25;
  letter-spacing: -0.01em;
}
header p { margin: 0 0 var(--space-1); font-size: var(--text-base); color: var(--muted); }
header .lab-url { color: var(--accent); }

.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

main {
  max-width: 72rem;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
}

a {
  color: var(--accent);
  overflow-wrap: anywhere;
  text-decoration: none;
}
a:hover { color: var(--accent-hover); text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-4);
  padding: var(--space-5) 0;
  margin-bottom: var(--space-8);
  border-bottom: 1px solid var(--border);
}
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-value {
  font-size: var(--text-xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  color: var(--ink);
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
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.02em;
  background: var(--tint-bg);
  color: var(--muted);
}
.status.pass, .status.completed, .status.review, .status.assessed { background: var(--ok-bg); color: var(--ok-text); }
.status.partial { background: var(--warn-bg); color: var(--warn-text); }
.status.fail, .status.unavailable { background: var(--err-bg); color: var(--err-text); }
.status.unknown, .status.skipped { background: var(--tint-bg); color: var(--muted); }

.fit-badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 600;
  background: var(--tint-bg);
  color: var(--muted);
}
.fit-badge.strong_profile, .fit-badge.excellent, .fit-badge.promising { background: var(--ok-bg); color: var(--ok-text); }
.fit-badge.usable_profile, .fit-badge.possible { background: var(--warn-bg); color: var(--warn-text); }
.fit-badge.limited_profile, .fit-badge.unlikely { background: var(--err-bg); color: var(--err-text); }
.fit-badge.unknown { background: var(--tint-bg); color: var(--muted); }

section {
  margin-bottom: var(--space-10);
  scroll-margin-top: calc(var(--nav-height) + var(--space-4));
}
section h2 {
  font-size: var(--text-xl);
  font-weight: 700;
  margin-bottom: var(--space-5);
  line-height: 1.3;
  letter-spacing: -0.005em;
  padding-bottom: var(--space-2);
  border-bottom: 2px solid var(--border);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  margin-bottom: var(--space-3);
}
.card h3 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: var(--space-2);
}

.theme {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border);
}
.theme:last-child { border-bottom: none; }
.theme-title { font-weight: 600; font-size: var(--text-base); }
.theme-description { font-size: var(--text-sm); color: var(--text); margin-top: var(--space-1); line-height: 1.5; }
.theme-detail { font-size: var(--text-sm); color: var(--muted); margin-top: var(--space-1); }

.confidence {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--tint-bg);
  color: var(--muted);
  margin-left: var(--space-2);
  font-weight: 500;
}
.confidence.high { background: var(--ok-bg); color: var(--ok-text); }
.confidence.medium { background: var(--warn-bg); color: var(--warn-text); }
.confidence.low { background: var(--err-bg); color: var(--err-text); }

.ref {
  font-family: "SF Mono", "Cascadia Code", "Consolas", monospace;
  font-size: var(--text-xs);
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dashed var(--accent);
  transition: color 150ms, border-color 150ms;
}
.ref:hover { color: var(--accent-hover); border-bottom-style: solid; text-decoration: none; }
.ref:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-bottom: none; border-radius: 2px; }

.md-table {
  border-collapse: collapse;
  width: 100%;
  margin: var(--space-4) 0;
  font-size: var(--text-sm);
}
.md-table th, .md-table td {
  border: 1px solid var(--border);
  padding: var(--space-3) var(--space-4);
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
.md-table td { vertical-align: top; font-size: var(--text-base); }
.md-table tr:hover td { background: oklch(98% 0.005 250); }

.limitations {
  background: var(--err-bg);
  border: 1px solid var(--err);
  border-radius: var(--radius-md);
  padding: var(--space-5);
}
.limitations h2 { color: var(--err-text); border-bottom-color: oklch(85% 0.04 25); }
.limitations li { margin-bottom: var(--space-2); font-size: var(--text-base); }

.audit-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4);
}
.audit-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-5);
}
.audit-card h3 { font-size: var(--text-base); font-weight: 600; margin-bottom: var(--space-3); }
.audit-card .audit-metrics { font-size: var(--text-sm); display: flex; flex-wrap: wrap; gap: var(--space-3); }
.audit-card .audit-metrics .muted { white-space: nowrap; }
.audit-card .audit-warnings { font-size: var(--text-sm); margin-top: var(--space-3); }

.artifacts { margin-bottom: var(--space-8); }
.artifacts a {
  display: block;
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}

.pub-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  margin-bottom: var(--space-4);
}
.pub-card-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.pub-number {
  font-size: var(--text-xl);
  font-weight: 800;
  color: var(--accent);
  line-height: 1;
  flex-shrink: 0;
}
.pub-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--ink);
  line-height: 1.35;
}
.pub-year-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  background: var(--accent-subtle);
  color: var(--accent);
  flex-shrink: 0;
}
.pub-overview { margin-top: var(--space-4); }
.pub-field { margin-top: var(--space-3); }
.pub-field-label {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}
.pub-field-value { font-size: var(--text-base); color: var(--ink); line-height: 1.6; }
.pub-overview-limited { font-size: var(--text-sm); font-style: italic; color: var(--muted); }
.pub-one-line { font-size: var(--text-base); margin-top: var(--space-1); }
.pub-authors { font-size: var(--text-sm); color: var(--muted); margin-top: var(--space-1); line-height: 1.5; }
.pi-author { font-weight: 700; color: var(--accent); }
.pub-meta { font-size: var(--text-sm); color: var(--muted); margin-top: var(--space-1); }
.pub-refs { font-size: var(--text-xs); margin-top: var(--space-2); }

.position-detail { font-size: var(--text-base); }
.position-refs { font-size: var(--text-xs); color: var(--muted); }
.fit-refs { font-size: var(--text-xs); }
.fit-status { margin-left: var(--space-2); }
.overall-status { margin-left: var(--space-2); }

.evidence-panel { margin-top: var(--space-4); }
.evidence-group-title { font-size: var(--text-base); font-weight: 600; margin: var(--space-5) 0 var(--space-2); }
.evidence-group-title:first-child { margin-top: 0; }
.evidence-item {
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid transparent;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  margin-bottom: var(--space-1);
  transition: border-color 200ms, background 200ms;
  scroll-margin-top: calc(var(--nav-height) + var(--space-4));
}
.evidence-item:target {
  border-left-color: var(--accent);
  background: var(--accent-subtle);
  animation: evidence-highlight 2.5s ease-out;
}
.evidence-item-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}
.evidence-id {
  font-family: "SF Mono", "Cascadia Code", "Consolas", monospace;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--accent);
}
.evidence-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 500;
  background: var(--tint-bg);
  color: var(--muted);
}
.evidence-badge.research_description { background: var(--ok-bg); color: var(--ok-text); }
.evidence-badge.confirmed { background: var(--ok-bg); color: var(--ok-text); }
.evidence-badge.profile_snippet { background: var(--warn-bg); color: var(--warn-text); }
.evidence-badge.likely { background: var(--warn-bg); color: var(--warn-text); }
.evidence-badge.link_text_only { background: var(--err-bg); color: var(--err-text); }
.evidence-snippet { font-size: var(--text-base); color: var(--ink); line-height: 1.6; margin-bottom: var(--space-1); }
.evidence-url { font-size: var(--text-sm); color: var(--accent); word-break: break-all; }

@keyframes evidence-highlight {
  0% { background: oklch(94% 0.06 250); }
  100% { background: transparent; }
}

details { margin-bottom: var(--space-4); }
details > summary {
  cursor: pointer;
  font-weight: 600;
  font-size: var(--text-base);
  padding: var(--space-3) 0;
  list-style: none;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  user-select: none;
  color: var(--ink);
}
details > summary::before {
  content: '\\25B8';
  font-size: var(--text-sm);
  transition: transform 150ms cubic-bezier(0.25, 1, 0.5, 1);
  display: inline-block;
  flex-shrink: 0;
}
details[open] > summary::before {
  transform: rotate(90deg);
}
details > summary:hover { color: var(--accent); }
details > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
details > .details-content { padding: var(--space-2) 0 var(--space-2) var(--space-5); }

.all-pubs-item {
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border);
  font-size: var(--text-base);
  line-height: 1.6;
}
.all-pubs-item:last-child { border-bottom: none; }
.all-pubs-year { font-weight: 600; color: var(--muted); margin-right: var(--space-2); }
.all-pubs-authors { font-size: var(--text-sm); color: var(--muted); margin-left: var(--space-1); }
.all-pubs-venue { font-style: italic; color: var(--muted); }
.all-pubs-doi { font-size: var(--text-sm); }

.report-body {
  font-size: var(--text-base);
  line-height: 1.7;
  max-width: 72ch;
}
.report-body h1 { font-size: var(--text-xl); margin: var(--space-6) 0 var(--space-3); }
.report-body h2 { font-size: var(--text-lg); margin: var(--space-5) 0 var(--space-3); border: none; padding: 0; }
.report-body h3 { font-size: var(--text-base); margin: var(--space-4) 0 var(--space-2); }
.report-body p { margin: var(--space-2) 0; }
.report-body ul { margin: var(--space-2) 0; padding-left: var(--space-5); }

@media (max-width: 640px) {
  header, main { padding: var(--space-4); }
  .stats { gap: var(--space-3); }
  .audit-section { grid-template-columns: 1fr; }
  .sticky-nav { padding: 0 var(--space-3); }
  header h1 { font-size: var(--text-xl); }
}

@media (prefers-reduced-motion: reduce) {
  .evidence-item:target { animation: none; background: var(--accent-subtle); }
  details > summary::before { transition: none; }
  .ref { transition: none; }
  #ref-back-btn { transition: none; }
}

#ref-back-btn {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  z-index: 200;
  display: none;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--surface);
  color: var(--accent);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 2px 8px oklch(60% 0.01 250 / 18%);
  transition: background 0.15s, box-shadow 0.15s;
  font-family: inherit;
}
#ref-back-btn:hover { background: var(--accent-subtle); box-shadow: 0 4px 12px oklch(60% 0.01 250 / 24%); }
#ref-back-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

@media print {
  #ref-back-btn { display: none !important; }
  .sticky-nav, .font-toggle { display: none !important; }
  body { font-size: 11pt; line-height: 1.4; color: oklch(10% 0 0); background: oklch(100% 0 0); }
  header { padding: 0 0 var(--space-4); background: none; border-bottom: 2px solid oklch(70% 0 0); }
  main { padding: var(--space-4) 0; max-width: none; }
  a { color: oklch(10% 0 0); text-decoration: underline; }
  .status, .fit-badge, .confidence { border: 1px solid oklch(60% 0 0); }
  section { scroll-margin-top: 0; break-inside: avoid; margin-bottom: var(--space-6); }
  section h2 { break-after: avoid; }
  .card { break-inside: avoid; border: 1px solid oklch(80% 0 0); background: none; }
  .pub-card { break-inside: avoid; background: none; border: 1px solid oklch(80% 0 0); border-left-color: oklch(70% 0 0); }
  .pub-field-label { color: oklch(40% 0 0); }
  .audit-card { break-inside: avoid; background: none; border: 1px solid oklch(80% 0 0); }
  .limitations { background: none; border: 1px solid oklch(60% 0 0); }
  .md-table th { background: oklch(93% 0 0); }
  .md-table tr:hover td { background: none; }
  details > summary::before { display: none; }
  .evidence-item { break-inside: avoid; border-left-color: oklch(70% 0 0); }
  .evidence-item:target { animation: none; background: none; }
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
    site_ev_map: dict[int, dict[str, Any]] | None = None,
    pub_ev_map: dict[int, dict[str, Any]] | None = None,
    all_pubs: list[dict[str, Any]] | None = None,
    pi_name: str = "",
    curated_map: dict[str, dict[str, Any]] | None = None,
) -> str:
    _site_ev = site_ev_map or {}
    _pub_ev = pub_ev_map or {}
    _all_pubs = all_pubs or []
    _curated_map = curated_map or {}

    lab_name = profile.get("lab_name", manifest.get("lab_name", "Unknown Lab"))
    pi_name_resolved = pi_name or profile.get("pi_name", manifest.get("pi_name", ""))

    pi_ln = _pi_last_name(pi_name_resolved).lower()

    def format_authors(authors: list[str] | None) -> str:
        if not authors:
            return ""
        def _highlight(author: str) -> str:
            if pi_ln and pi_ln in author.lower():
                return f'<strong class="pi-author">{e(author)}</strong>'
            return e(author)
        if len(authors) <= 2:
            return ", ".join(_highlight(a) for a in authors)
        return f'{_highlight(authors[0])} ... {_highlight(authors[-1])}'
    pi_name = pi_name_resolved
    institution = profile.get("institution", manifest.get("institution", ""))
    lab_url = profile.get("lab_url", manifest.get("lab_url", ""))
    overall_assessment = profile.get("overall_assessment", "unknown")
    position_signal = profile.get("position_signal", "unknown")
    themes = profile.get("research_themes", [])
    limitations = profile.get("limitations", [])
    evidence_summary = profile.get("evidence_summary", {})
    overall_status = manifest.get("overall_status", "unknown")
    report_html = md_to_html(report_md) if report_md else "<p>No report available.</p>"

    def render_ref(ref_str: str) -> str:
        display = e(ref_str)
        parts = ref_str.split(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            prefix = parts[0]
            idx = int(parts[1])
            anchor = f"evidence-{e(prefix)}-{idx}"
            return f'<a href="#{anchor}" class="ref">[{display}]</a>'
        return f'<span class="ref">[{display}]</span>'

    def render_refs(refs: list[str]) -> str:
        return " ".join(render_ref(r) for r in refs)

    themes_html = ""
    for t in themes:
        conf = t.get("confidence", "unknown")
        refs_str = render_refs(t.get("evidence_refs", []))
        desc = t.get("description", "")
        desc_html = f'<div class="theme-description">{e(desc)}</div>' if desc else ""
        themes_html += f"""
        <div class="theme">
          <div><span class="theme-title">{e(t.get("theme", ""))}</span><span class="confidence {e(conf)}">{e(conf)}</span></div>
          {desc_html}
          <div class="theme-detail">{refs_str}</div>
        </div>"""

    important_pubs_html = ""
    for i, pub in enumerate(profile.get("important_publications", []), 1):
        refs_str = render_refs(pub.get("evidence_refs", []))
        ov = pub.get("publication_overview", {})
        overview_line = f'<div class="pub-one-line">{e(ov.get("one_line", ""))}</div>' if ov.get("one_line") else ""
        ov_fields = ""
        for field_key, label in [
            ("research_question", "Research Question"),
            ("key_finding", "Key Finding"),
            ("methods", "Methods"),
            ("significance", "Significance"),
        ]:
            val = ov.get(field_key, "")
            if val:
                ov_fields += f'<div class="pub-field"><div class="pub-field-label">{e(label)}</div><div class="pub-field-value">{e(val)}</div></div>'
        ov_detail_html = f'<div class="pub-overview">{ov_fields}</div>' if ov_fields else ""
        limited_html = '<div class="pub-overview-limited">[Overview limited: no abstract available]</div>' if ov and not any([ov.get("research_question"), ov.get("key_finding"), ov.get("methods")]) else ""
        doi_key = (pub.get("doi") or "").lower()
        cid = pub.get("candidate_id") or pub.get("curated_id")
        curated_rec = _curated_map.get(doi_key) if doi_key else None
        if not curated_rec and cid is not None:
            curated_rec = _curated_map.get(f"cid:{cid}")
        curated_rec = curated_rec or {}
        authors = curated_rec.get("authors", pub.get("authors"))
        authors_html = f'<div class="pub-authors">{format_authors(authors)}</div>' if authors else ""
        venue_val = pub.get("venue") or pub.get("journal", "")
        important_pubs_html += f"""
        <div class="pub-card">
          <div class="pub-card-header">
            <span class="pub-number">{i}</span>
            <span class="pub-title">{e(pub.get("title", "Untitled"))}</span>
            <span class="pub-year-badge">{e(pub.get("year", "?"))}</span>
          </div>
          {authors_html}
          <div class="pub-meta">{e(venue_val)} | {e(pub.get("publication_type", ""))} | {e(pub.get("match_tier", ""))}{" | theme: " + e(pub["theme"]) if pub.get("theme") else ""}</div>
          {overview_line}{ov_detail_html}{limited_html}
          <div class="pub-refs">{refs_str}</div>
        </div>"""
    if not important_pubs_html:
        important_pubs_html = '<p class="muted">No important recent publications available.</p>'

    confirmed_count = len(_all_pubs)
    all_pubs_html = ""
    if _all_pubs:
        items_html = ""
        for i, pub in enumerate(_all_pubs, 1):
            title = e(pub.get("title", "Untitled"))
            year = e(pub.get("year", ""))
            venue = e(pub.get("venue") or pub.get("journal", ""))
            doi = pub.get("doi", "")
            authors = pub.get("authors")
            authors_line = f' <span class="all-pubs-authors">{format_authors(authors)}</span>' if authors else ""
            doi_link = f' <a class="all-pubs-doi" href="https://doi.org/{e(doi)}">{e(doi)}</a>' if doi else ""
            venue_part = f' <span class="all-pubs-venue">{e(venue)}</span>' if venue else ""
            items_html += f'<div class="all-pubs-item"><span class="all-pubs-year">{year}</span>{title}{authors_line}{venue_part}{doi_link}</div>'
        all_pubs_html = f"""
    <details id="all-publications">
      <summary>Show all {e(confirmed_count)} confirmed publications</summary>
      <div class="details-content">{items_html}
      </div>
    </details>"""

    positions_html = ""
    signals = positions.get("signals", []) if isinstance(positions, dict) else positions if isinstance(positions, list) else []
    for sig in signals:
        refs_str = render_refs(sig.get("evidence_refs", []))
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
        refs_str = render_refs(dim.get("evidence_refs", []))
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

    site_evidence_count = len(_site_ev)
    pub_evidence_count = len(_pub_ev)
    total_evidence = site_evidence_count + pub_evidence_count

    evidence_site_html = ""
    for eid in sorted(_site_ev.keys()):
        item = _site_ev[eid]
        snippet = e(item.get("snippet", ""))
        source_url = item.get("source_url", "")
        claim_type = e(item.get("claim_type", ""))
        quality = e(item.get("evidence_quality", ""))
        url_link = f'<a class="evidence-url" href="{e(source_url)}" target="_blank" rel="noopener">{e(source_url)}</a>' if source_url else ""
        evidence_site_html += f"""
          <div class="evidence-item" id="evidence-site-{eid}">
            <div class="evidence-item-header">
              <span class="evidence-id">site:{eid}</span>
              <span class="evidence-badge {e(claim_type)}">{e(claim_type)}</span>
              <span class="evidence-badge {e(quality)}">{e(quality)}</span>
            </div>
            <div class="evidence-snippet">{snippet}</div>
            {url_link}
          </div>"""

    evidence_pub_html = ""
    for eid in sorted(_pub_ev.keys()):
        item = _pub_ev[eid]
        snippet = e(item.get("snippet", ""))
        source_url = item.get("source_url", "")
        doi = item.get("pub_doi", "")
        match_tier = e(item.get("match_tier", ""))
        url_link = f'<a class="evidence-url" href="{e(source_url)}" target="_blank" rel="noopener">{e(source_url)}</a>' if source_url else ""
        doi_link = f'<a class="evidence-url" href="https://doi.org/{e(doi)}" target="_blank" rel="noopener">{e(doi)}</a>' if doi else ""
        evidence_pub_html += f"""
          <div class="evidence-item" id="evidence-pub-{eid}">
            <div class="evidence-item-header">
              <span class="evidence-id">pub:{eid}</span>
              <span class="evidence-badge {e(match_tier)}">{e(match_tier)}</span>
            </div>
            <div class="evidence-snippet">{snippet}</div>
            {doi_link}{url_link}
          </div>"""

    evidence_sources_html = ""
    if total_evidence > 0:
        evidence_inner = ""
        if evidence_site_html:
            evidence_inner += f'<div class="evidence-group-title">Site Evidence ({e(site_evidence_count)})</div>' + evidence_site_html
        if evidence_pub_html:
            evidence_inner += f'<div class="evidence-group-title">Publication Evidence ({e(pub_evidence_count)})</div>' + evidence_pub_html
        evidence_sources_html = f"""
    <details id="evidence-sources" class="evidence-panel">
      <summary>Evidence Sources ({e(total_evidence)})</summary>
      <div class="details-content">{evidence_inner}
      </div>
    </details>"""

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
  <nav class="sticky-nav" aria-label="Section navigation">
    <div class="nav-links">
      <a href="#themes">Themes</a>
      <a href="#publications">Publications</a>
      <a href="#positions">Positions</a>
      <a href="#assessment">Assessment</a>
      <a href="#report">Report</a>
      <a href="#audits">Audits</a>
      <a href="#evidence-sources">Sources</a>
    </div>
    <div class="font-toggle" role="radiogroup" aria-label="Text size">
      <button data-size="sm" role="radio" aria-checked="false" aria-label="Small text">A<sup>-</sup></button>
      <button data-size="md" class="active" role="radio" aria-checked="true" aria-label="Default text">A</button>
      <button data-size="lg" role="radio" aria-checked="false" aria-label="Large text">A<sup>+</sup></button>
    </div>
  </nav>

  <header>
    <h1>{e(lab_name)}</h1>
    <p>PI: {e(pi_name)} | Institution: {e(institution)}</p>
    {f'<p><a class="lab-url" href="{e(lab_url)}">{e(lab_url)}</a></p>' if lab_url else ""}
    <div class="badge-row">
      <span class="fit-badge {e(overall_assessment)}">{e(overall_assessment.replace("_", " ").title())}</span>
      <span class="status {e(overall_status)} overall-status">{e(overall_status)}</span>
    </div>
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

    <section id="themes" aria-label="Research Themes"><h2>Research Themes</h2>{themes_html if themes_html else '<p class="muted">No research themes available.</p>'}</section>
    <section id="publications" aria-label="Important Publications">
      <h2>Important Recent Publications (Last 3-5 Years)</h2>
      {important_pubs_html}
      {all_pubs_html}
    </section>
    <section id="positions" aria-label="Position Signals"><h2>Position Signals</h2>{positions_html}</section>

    <section id="assessment" aria-label="Fit Assessment">
      <h2>Lab Summary Assessment</h2>
      {f'<div class="fit-badge {e(overall_assessment)}" style="margin-bottom:var(--space-4)">Overall: {e(overall_assessment.replace("_", " ").title())}</div>' if overall_assessment != "unknown" else ""}
      <table class="md-table">
        <thead><tr><th>Dimension</th><th>Status</th><th>Confidence</th><th>Assessment</th></tr></thead>
        <tbody>{fit_html}</tbody>
      </table>
    </section>

    <section id="report" aria-label="Full Report">
      <details>
        <summary>Full Report</summary>
        <div class="details-content">
          <div class="report-body">{report_html}</div>
        </div>
      </details>
    </section>

    <section id="audits" aria-label="Audits">
      <h2>Audits</h2>
      <div class="audit-section">
      {audit_card("Site Audit", site_audit)}
      {audit_card("Publication Audit", pub_audit)}
      {audit_card("Lab Summary Audit", fit_audit)}
      </div>
    </section>

    {evidence_sources_html}

    {f'<section class="limitations" aria-label="Limitations"><h2>Limitations</h2><ul>{"".join(f"<li>{e(lim)}</li>" for lim in limitations)}</ul></section>' if limitations else ""}

    <section class="artifacts" aria-label="Raw Artifacts">
      <h2>Raw Artifacts</h2>
      {artifacts_html}
    </section>
  </main>

<button id="ref-back-btn" type="button" aria-label="Return to previous position">&larr; Back</button>

<script>
(function(){{
  var root=document.documentElement;
  var btns=document.querySelectorAll('.font-toggle button');
  btns.forEach(function(b){{
    b.addEventListener('click',function(){{
      var sz=b.getAttribute('data-size');
      btns.forEach(function(x){{
        x.classList.remove('active');
        x.setAttribute('aria-checked','false');
      }});
      b.classList.add('active');
      b.setAttribute('aria-checked','true');
      if(sz==='sm') root.setAttribute('data-text-size','sm');
      else if(sz==='lg') root.setAttribute('data-text-size','lg');
      else root.removeAttribute('data-text-size');
      try{{localStorage.setItem('lab-text-size',sz);}}catch(e){{}}
    }});
  }});
  try{{
    var saved=localStorage.getItem('lab-text-size');
    if(saved){{
      var match=document.querySelector('.font-toggle button[data-size="'+saved+'"]');
      if(match) match.click();
    }}
  }}catch(e){{}}

  var navLinks=document.querySelectorAll('.sticky-nav .nav-links a');
  var sections=Array.from(navLinks).map(function(a){{
    var id=a.getAttribute('href').slice(1);
    return document.getElementById(id);
  }}).filter(Boolean);

  function onScroll(){{
    var scrollY=window.scrollY;
    var current=null;
    for(var i=sections.length-1;i>=0;i--){{
      if(sections[i].getBoundingClientRect().top<=120){{
        current=sections[i];break;
      }}
    }}
    navLinks.forEach(function(a){{
      var id=a.getAttribute('href').slice(1);
      if(current&&current.id===id) a.classList.add('active');
      else a.classList.remove('active');
    }});
  }}
  var ticking=false;
  window.addEventListener('scroll',function(){{
    if(!ticking){{window.requestAnimationFrame(function(){{onScroll();ticking=false;}});ticking=true;}}
  }});
  onScroll();

  document.addEventListener('click',function(ev){{
    var a=ev.target.closest('a.ref');
    if(!a) return;
    var href=a.getAttribute('href');
    if(!href||href.charAt(0)!=='#') return;
    var target=document.getElementById(href.slice(1));
    if(!target) return;
    window._refOrigin=window.scrollY;
    var backBtn=document.getElementById('ref-back-btn');
    if(backBtn) backBtn.style.display='inline-flex';
    var details=target.closest('details');
    if(details&&!details.open){{
      details.open=true;
    }}
    setTimeout(function(){{
      target.scrollIntoView({{behavior:'smooth',block:'center'}});
    }},50);
  }});

  var backBtn=document.getElementById('ref-back-btn');
  if(backBtn){{
    backBtn.addEventListener('click',function(){{
      var origin=window._refOrigin;
      window._refOrigin=null;
      backBtn.style.display='none';
      if(typeof origin==='number'){{
        window.scrollTo({{top:origin,behavior:'smooth'}});
      }}
    }});
    var hideTimer=null;
    window.addEventListener('scroll',function(){{
      if(!window._refOrigin||backBtn.style.display==='none') return;
      if(hideTimer) clearTimeout(hideTimer);
      hideTimer=setTimeout(function(){{
        if(Math.abs(window.scrollY-window._refOrigin)<60){{
          backBtn.style.display='none';
          window._refOrigin=null;
        }}
      }},100);
    }});
  }}
}})();
</script>
</body>
</html>
"""


def _flatten_curated(curated_data: dict[str, Any]) -> list[dict[str, Any]]:
    pubs = curated_data.get("publications", curated_data.get("candidates", []))
    if pubs:
        return pubs
    tier_keys = ("confirmed", "likely", "ambiguous", "rejected")
    has_tier_key = any(k in curated_data for k in tier_keys)
    if not has_tier_key:
        return []
    result: list[dict[str, Any]] = []
    for tier in tier_keys:
        for entry in curated_data.get(tier, []):
            entry = dict(entry)
            entry.setdefault("match_tier", tier)
            result.append(entry)
    return result


def _candidate_is_confirmed(candidate: dict[str, Any]) -> bool:
    if candidate.get("match_tier") in ("confirmed", "likely"):
        return True
    if candidate.get("match_status") in ("confirmed", "likely"):
        return True
    me = candidate.get("match_evidence", {})
    if isinstance(me, dict):
        pi_match = me.get("pi_name_match")
        aff_match = me.get("affiliation_match")
        pi_ok = pi_match is True or pi_match == "confirmed"
        aff_ok = aff_match in ("confirmed", "likely", True)
        if pi_ok and aff_ok:
            return True
    return False


def _pi_last_name(pi_name: str) -> str:
    if not pi_name:
        return ""
    if "," in pi_name:
        return pi_name.split(",", 1)[0].strip()
    parts = pi_name.strip().split()
    return parts[-1] if parts else ""


def build(lab_summaries_dir: Path) -> Path:
    profile = read_json(lab_summaries_dir / "lab_profile.json", {})
    fit_assessment = read_json(lab_summaries_dir / "lab_summary_assessment.json", {})
    positions = read_json(lab_summaries_dir / "position_signals.json", {})
    site_audit = read_json(lab_summaries_dir / "lab_site_audit.json", {})
    pub_audit = read_json(lab_summaries_dir / "publication_audit.json", {})
    fit_audit = read_json(lab_summaries_dir / "lab_summary_audit.json", {})
    manifest = read_json(lab_summaries_dir / "lab_summary_manifest.json", {})
    report_md = normalize_report_md(lab_summaries_dir, profile)

    site_ev_items = read_jsonl(lab_summaries_dir / "lab_site_evidence.jsonl")
    site_ev_map: dict[int, dict[str, Any]] = {item.get("evidence_id", i): item for i, item in enumerate(site_ev_items)}

    pub_ev_items = read_jsonl(lab_summaries_dir / "publication_evidence.jsonl")
    pub_ev_map: dict[int, dict[str, Any]] = {item.get("evidence_id", i): item for i, item in enumerate(pub_ev_items)}

    pi_name = profile.get("pi_name", manifest.get("pi_name", ""))
    curated_data = read_json(lab_summaries_dir / "publications.curated.json", None)
    if curated_data:
        curated_pubs = _flatten_curated(curated_data)
        curated_map: dict[str, dict[str, Any]] = {}
        for c in curated_pubs:
            doi_key = (c.get("doi") or "").lower()
            if doi_key:
                curated_map[doi_key] = c
            cid = c.get("candidate_id") or c.get("curated_id")
            if cid is not None:
                curated_map[f"cid:{cid}"] = c
        all_pubs = [c for c in curated_pubs if c.get("match_tier") in ("confirmed", "likely")]
    else:
        pub_candidates = read_jsonl(lab_summaries_dir / "publication_candidates.jsonl")
        curated_map = {}
        for c in pub_candidates:
            doi_key = (c.get("doi") or "").lower()
            if doi_key:
                curated_map[doi_key] = c
            cid = c.get("candidate_id") or c.get("curated_id")
            if cid is not None:
                curated_map[f"cid:{cid}"] = c
        all_pubs = [
            c for c in pub_candidates
            if _candidate_is_confirmed(c)
        ]

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
        site_ev_map=site_ev_map,
        pub_ev_map=pub_ev_map,
        all_pubs=all_pubs,
        pi_name=pi_name,
        curated_map=curated_map,
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

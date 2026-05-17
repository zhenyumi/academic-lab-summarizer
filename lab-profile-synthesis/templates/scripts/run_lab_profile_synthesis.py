from __future__ import annotations

"""Copyable template runner for lab-profile-synthesis.

Reads lab_summary_input.json and upstream artifacts (site evidence, curated
publications, publication evidence, research theme profile) from fixtures or
real upstream outputs, then writes:
  - position_signals.json
  - lab_summary_assessment.json
  - lab_profile.json
  - report.md
  - lab_summary_audit.json

No network calls. Copy into <run>/tools/ and adapt for real runs.
"""

import argparse
import json
import re
from pathlib import Path

EVIDENCE_REF_RE = re.compile(r"^(site|pub):(\d+)$")


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def curated_list(curated: dict) -> list[dict]:
    return curated.get("candidates", curated.get("publications", []))


def write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def find_fixture(fixtures_dir: Path | None, canonical: str, sample: str) -> Path | None:
    if fixtures_dir is None:
        return None
    p = fixtures_dir / canonical
    if p.exists():
        return p
    p = fixtures_dir / sample
    if p.exists():
        return p
    return None


POSITION_KEYWORDS: list[tuple[str, list[str]]] = [
    ("postdoc", ["postdoc", "postdoctoral", "post-doctoral", "fellow"]),
    ("phd", ["phd", "ph.d", "doctoral", "graduate student"]),
    ("masters", ["master", "msc", "m.s."]),
    ("undergraduate", ["undergraduate", "intern", "summer student"]),
    ("research_assistant", ["research assistant", " ra ", "research associate"]),
    ("technician", ["technician", "lab tech"]),
    ("lab_manager", ["lab manager", "laboratory manager"]),
    ("staff_scientist", ["staff scientist", "research scientist"]),
]


def classify_position(snippet: str) -> str:
    text = f" {snippet.lower()} "
    for category, keywords in POSITION_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    if any(keyword in text for keyword in ["join", "apply", "position", "opening", "recruit"]):
        return "other"
    return "none"


def classify_position_strength(snippet: str, category: str, quality: str) -> str:
    text = snippet.lower()
    if category == "none":
        return "none"
    if any(keyword in text for keyword in ["closed", "filled", "deadline passed", "no longer accepting"]):
        return "closed_or_past"
    has_application_signal = any(keyword in text for keyword in [
        "apply", "application", "send cv", "send your cv", "deadline", "start date",
        "starting", "position available", "opening", "we are seeking", "we are recruiting",
    ])
    if category != "other" and has_application_signal and quality != "link_text_only":
        return "confirmed_opening"
    if category != "other":
        return "likely_opening"
    return "generic_recruitment"


def build_position_signals(site_evidence: list[dict], lab_id: str) -> dict:
    signals = []
    signal_id = 0
    for ev in site_evidence:
        if ev.get("claim_type") != "position_signal":
            continue
        signal_id += 1
        quality = ev.get("evidence_quality", "none")
        snippet = ev.get("snippet", "")
        category = classify_position(snippet)
        strength = classify_position_strength(snippet, category, quality)

        if strength == "confirmed_opening":
            confidence = "high"
        elif strength == "likely_opening":
            confidence = "medium"
        elif strength == "generic_recruitment":
            confidence = "low"
        else:
            confidence = "unknown"

        signals.append({
            "signal_id": signal_id,
            "source_url": ev.get("source_url", ""),
            "snippet": snippet,
            "position_category": category,
            "signal_strength": strength,
            "details": snippet[:120] if snippet else "No details",
            "evidence_refs": [f"site:{ev.get('evidence_id', 0)}"],
            "confidence": confidence,
            "last_observed_or_posted_date": ev.get("last_observed_or_posted_date", ""),
        })

    strengths = [s["signal_strength"] for s in signals]
    if "confirmed_opening" in strengths:
        overall = "confirmed_opening"
    elif "likely_opening" in strengths:
        overall = "likely_opening"
    elif "generic_recruitment" in strengths:
        overall = "generic_recruitment"
    elif "closed_or_past" in strengths:
        overall = "closed_or_past"
    else:
        overall = "none"

    return {
        "lab_id": lab_id,
        "signals": signals,
        "overall_position_signal": overall,
        "notes": f"Found {len(signals)} position signal(s).",
    }


def build_lab_summary_assessment(
    lab_id: str,
    themes: dict,
    site_evidence: list[dict],
    curated: dict,
    position_signals: dict,
) -> dict:
    confirmed = {c["candidate_id"] for c in curated_list(curated) if c.get("match_tier") == "confirmed"}
    likely = {c["candidate_id"] for c in curated_list(curated) if c.get("match_tier") == "likely"}
    theme_pub_ids = set()
    for t in themes.get("themes", themes.get("research_themes", [])):
        theme_pub_ids.update(t.get("supporting_publications", []))

    site_research = [ev for ev in site_evidence if ev.get("claim_type") == "research_direction"]

    confirmed_signals = [s for s in position_signals.get("signals", []) if s["signal_strength"] == "confirmed_opening"]
    likely_signals = [s for s in position_signals.get("signals", []) if s["signal_strength"] == "likely_opening"]
    generic_signals = [s for s in position_signals.get("signals", []) if s["signal_strength"] == "generic_recruitment"]

    dimensions = []

    if theme_pub_ids:
        dims_refs = [f"site:{ev['evidence_id']}" for ev in site_research[:2]]
        dims_refs += [f"pub:{pid}" for pid in list(theme_pub_ids)[:2]]
        dims_status = "assessed"
        dims_confidence = "high" if len(theme_pub_ids) >= 2 else "medium"
        dims_text = f"Lab has {len(theme_pub_ids)} publication(s) aligned with research themes."
    else:
        dims_refs = []
        dims_status = "unavailable"
        dims_confidence = "unknown"
        dims_text = "No publication themes available for alignment assessment."

    dimensions.append({
        "dimension": "research_focus",
        "description": "Research themes and directions evident in the lab's publications and site.",
        "assessment": dims_text,
        "confidence": dims_confidence,
        "evidence_refs": dims_refs,
        "status": dims_status,
        "limitations": [] if dims_status == "assessed" else ["No theme data."],
    })

    dimensions.append({
        "dimension": "publication_profile",
        "description": "Recent publications, attribution confidence, and theme coverage.",
        "assessment": f"{len(confirmed)} confirmed and {len(likely)} likely recent publication(s) support the lab profile.",
        "confidence": "high" if len(confirmed) >= 1 else ("medium" if len(likely) >= 2 else "low"),
        "evidence_refs": [f"pub:{pid}" for pid in list(confirmed | likely)[:3]],
        "status": "assessed" if confirmed or likely else "unavailable",
        "limitations": [] if confirmed or likely else ["No confirmed or likely publication matches."],
    })

    if confirmed_signals:
        ha_text = "Confirmed open position signal found."
        ha_refs = confirmed_signals[0]["evidence_refs"]
        ha_conf = "high"
        ha_status = "assessed"
    elif likely_signals:
        ha_text = "Likely position signal found."
        ha_refs = likely_signals[0]["evidence_refs"]
        ha_conf = "medium"
        ha_status = "assessed"
    elif generic_signals:
        ha_text = "Generic recruitment language found; no role-specific opening confirmed."
        ha_refs = generic_signals[0]["evidence_refs"]
        ha_conf = "low"
        ha_status = "partial"
    else:
        ha_text = "No specific position signal found."
        ha_refs = []
        ha_conf = "unknown"
        ha_status = "unavailable"

    dimensions.append({
        "dimension": "position_availability",
        "description": "Based on position signals, not inference.",
        "assessment": ha_text,
        "confidence": ha_conf,
        "evidence_refs": ha_refs,
        "status": ha_status,
        "limitations": [] if ha_status == "assessed" else ["No position signals."],
    })

    pub_count = len(confirmed) + len(likely)
    if pub_count >= 3:
        lm_text = f"PI has {pub_count} confirmed/likely recent publications; lab appears active."
        lm_conf = "medium"
        lm_status = "partial"
    elif pub_count >= 1:
        lm_text = f"PI has {pub_count} confirmed/likely publication(s); limited data for maturity assessment."
        lm_conf = "low"
        lm_status = "partial"
    else:
        lm_text = "No confirmed publications found."
        lm_conf = "unknown"
        lm_status = "unavailable"

    dimensions.append({
        "dimension": "lab_activity_and_trajectory",
        "description": "PI career stage, lab size, publication trajectory.",
        "assessment": lm_text,
        "confidence": lm_conf,
        "evidence_refs": [f"pub:{pid}" for pid in list(confirmed | likely)[:3]],
        "status": lm_status,
        "limitations": ["Lab size not directly observed."] if lm_status != "unavailable" else ["No publication data."],
    })

    site_methods = [ev for ev in site_evidence if ev.get("claim_type") == "research_direction"]
    if site_methods:
        mf_text = site_methods[0].get("snippet", "Methods described on lab site.")[:150]
        mf_refs = [f"site:{site_methods[0]['evidence_id']}"]
        mf_conf = "medium"
        mf_status = "assessed"
    else:
        mf_text = "No methodological information found on lab site."
        mf_refs = []
        mf_conf = "unknown"
        mf_status = "unavailable"

    dimensions.append({
        "dimension": "methods_and_approaches",
        "description": "Techniques, methods, and experimental approaches documented for the lab.",
        "assessment": mf_text,
        "confidence": mf_conf,
        "evidence_refs": mf_refs,
        "status": mf_status,
        "limitations": [] if mf_status == "assessed" else ["No method data."],
    })

    funding_evidence = [ev for ev in site_evidence if "grant" in ev.get("snippet", "").lower()
                        or "funding" in ev.get("snippet", "").lower()
                        or "nih" in ev.get("snippet", "").lower()
                        or "nsf" in ev.get("snippet", "").lower()]
    if funding_evidence:
        fi_text = "Funding information found on lab site."
        fi_refs = [f"site:{funding_evidence[0]['evidence_id']}"]
        fi_conf = "medium"
        fi_status = "assessed"
    else:
        fi_text = "No funding information found on the lab site."
        fi_refs = []
        fi_conf = "unknown"
        fi_status = "unavailable"

    dimensions.append({
        "dimension": "funding_indicators",
        "description": "Grant mentions, lab resources, institutional support.",
        "assessment": fi_text,
        "confidence": fi_conf,
        "evidence_refs": fi_refs,
        "status": fi_status,
        "limitations": [] if fi_status == "assessed" else ["No site evidence for funding."],
    })

    assessed = sum(1 for d in dimensions if d["status"] == "assessed")
    partial = sum(1 for d in dimensions if d["status"] == "partial")
    if assessed >= 4:
        overall_assessment = "strong_profile"
        overall_conf = "medium"
    elif assessed >= 3:
        overall_assessment = "usable_profile"
        overall_conf = "medium"
    elif assessed + partial >= 3:
        overall_assessment = "limited_profile"
        overall_conf = "low"
    else:
        overall_assessment = "unknown"
        overall_conf = "low"

    return {
        "lab_id": lab_id,
        "dimensions": dimensions,
        "overall_assessment": overall_assessment,
        "overall_confidence": overall_conf,
    }


def build_important_publications(
    curated: dict,
    themes: dict,
) -> list[dict]:
    curated_list = curated.get("candidates", curated.get("publications", []))
    candidates = {c["candidate_id"]: c for c in curated_list}
    theme_by_pub: dict[int, str] = {}
    for t in themes.get("themes", themes.get("research_themes", [])):
        for pid in t.get("supporting_publications", []):
            if pid not in theme_by_pub:
                theme_by_pub[pid] = t.get("theme", t.get("name", ""))

    results = []
    priority_order = [
        lambda c: c.get("match_tier") == "confirmed" and c.get("publication_type") == "peer_reviewed",
        lambda c: c.get("match_tier") == "confirmed",
        lambda c: c.get("match_tier") == "likely" and c.get("publication_type") == "peer_reviewed",
        lambda c: c.get("match_tier") == "likely",
    ]
    for priority_fn in priority_order:
        for c in curated_list:
            if any(r["candidate_id"] == c["candidate_id"] for r in results):
                continue
            if priority_fn(c):
                theme_name = theme_by_pub.get(c["candidate_id"], "")
                abstract = c.get("abstract", "")
                is_valid_abstract = (
                    abstract
                    and len(abstract) >= 50
                    and abstract.strip().rstrip(".").lower() != c.get("title", "").strip().rstrip(".").lower()
                )
                overview = {"one_line": "", "research_question": "", "key_finding": "", "methods": "", "significance": ""}
                if is_valid_abstract:
                    sentences = [s.strip() for s in abstract.split(".") if s.strip()]
                    overview["one_line"] = (sentences[0] + "." if sentences else abstract)[:250].strip()
                    if len(sentences) > 1:
                        overview["key_finding"] = (sentences[1] + ".")[:250].strip()
                else:
                    overview["one_line"] = c.get("title", "Untitled")
                if theme_name:
                    overview["significance"] = f"Relates to lab theme: {theme_name}"
                results.append({
                    "candidate_id": c["candidate_id"],
                    "title": c.get("title", "Untitled"),
                    "year": c.get("year"),
                    "venue": c.get("venue", ""),
                    "publication_type": c.get("publication_type", "unknown"),
                    "match_tier": c.get("match_tier", "unknown"),
                    "theme": theme_name,
                    "publication_overview": overview,
                    "evidence_refs": [f"pub:{c['candidate_id']}"],
                })

    return results


def build_lab_profile(
    lab_id: str,
    lab_name: str,
    pi_name: str,
    institution: str,
    lab_url: str,
    themes: dict,
    curated: dict,
    position_signals: dict,
    fit_assessment: dict,
    site_evidence: list[dict],
    pub_evidence: list[dict],
) -> dict:
    confirmed = [c for c in curated_list(curated) if c.get("match_tier") == "confirmed"]
    likely = [c for c in curated_list(curated) if c.get("match_tier") == "likely"]

    research_themes = []
    for t in themes.get("themes", themes.get("research_themes", [])):
        supporting = t.get("supporting_publications", [])
        research_themes.append({
            "theme": t.get("theme", t.get("name", "Unknown")),
            "confidence": t.get("confidence", "medium"),
            "evidence_refs": [f"pub:{pid}" for pid in supporting],
        })

    important_publications = build_important_publications(curated, themes)

    weak_count = sum(1 for ev in site_evidence if ev.get("evidence_quality") in ("link_text_only", "none"))
    weak_ratio = round(weak_count / len(site_evidence), 2) if site_evidence else 0.0

    limitations = []
    fi_dim = next((d for d in fit_assessment["dimensions"] if d["dimension"] == "funding_indicators"), None)
    if fi_dim and fi_dim["status"] == "unavailable":
        limitations.append("Funding indicators are unavailable.")
    generic_sigs = [s for s in position_signals.get("signals", []) if s["signal_strength"] == "generic_recruitment"]
    if generic_sigs:
        limitations.append("One or more position signals are generic recruitment language, not confirmed openings.")
    ambig = themes.get("ambiguous_excluded_count", 0)
    if ambig > 0:
        limitations.append(f"{ambig} publication(s) ambiguous and excluded from research themes.")

    return {
        "lab_id": lab_id,
        "lab_name": lab_name,
        "pi_name": pi_name,
        "institution": institution,
        "lab_url": lab_url,
        "research_themes": research_themes,
        "important_publications": important_publications,
        "confirmed_publication_count": len(confirmed),
        "likely_publication_count": len(likely),
        "position_signal": position_signals.get("overall_position_signal", "none"),
        "overall_assessment": fit_assessment.get("overall_assessment", "unknown"),
        "evidence_summary": {
            "site_evidence_count": len(site_evidence),
            "publication_evidence_count": len(pub_evidence),
            "weak_evidence_ratio": weak_ratio,
        },
        "limitations": limitations,
    }


def build_report(
    lab_name: str,
    pi_name: str,
    institution: str,
    curated: dict,
    themes: dict,
    position_signals: dict,
    fit_assessment: dict,
    lab_profile: dict,
) -> str:
    lines = []
    lines.append(f"# Lab Profile: {lab_name}\n")
    lines.append(f"## PI: {pi_name}\n")
    lines.append(f"## Institution: {institution}\n")

    lines.append("## Research Themes\n")
    for theme in lab_profile.get("research_themes", []):
        refs_str = ", ".join(theme.get("evidence_refs", []))
        lines.append(f"**{theme['theme']}** ({theme.get('confidence', 'medium')} confidence)")
        lines.append(f"Evidence: [{refs_str}]\n")

    lines.append("## Important Recent Publications (Last 3-5 Years)\n")
    important = lab_profile.get("important_publications", [])
    if important:
        for pub in important:
            pub_type = pub.get("publication_type", "unknown")
            lines.append(f"- **{pub['title']}** ({pub.get('year', '?')}) [{pub_type}, {pub.get('match_tier', '?')}]")
            if pub.get("venue"):
                lines.append(f"  - Venue: {pub['venue']}")
            ov = pub.get("publication_overview", {})
            if ov.get("one_line"):
                lines.append(f"  - Overview: {ov['one_line']}")
            if ov.get("research_question"):
                lines.append(f"  - Research question: {ov['research_question']}")
            if ov.get("key_finding"):
                lines.append(f"  - Key finding: {ov['key_finding']}")
            if ov.get("methods"):
                lines.append(f"  - Methods: {ov['methods']}")
            if ov.get("significance"):
                lines.append(f"  - Significance: {ov['significance']}")
            if ov and not any([ov.get("research_question"), ov.get("key_finding"), ov.get("methods")]):
                lines.append(f"  - [Overview limited — no abstract available]")
            if pub.get("theme"):
                lines.append(f"  - Research theme: {pub['theme']}")
            lines.append("")
    else:
        lines.append("No recent publications available.\n")

    lines.append("## Recent Publications\n")
    confirmed = [c for c in curated_list(curated) if c.get("match_tier") == "confirmed"]
    likely = [c for c in curated_list(curated) if c.get("match_tier") == "likely"]
    ambiguous = [c for c in curated_list(curated) if c.get("match_tier") == "ambiguous"]

    peer_reviewed = [c for c in confirmed + likely if c.get("publication_type") == "peer_reviewed"]
    preprints = [c for c in confirmed + likely if c.get("publication_type") == "preprint"]

    if peer_reviewed:
        lines.append("### Peer-reviewed\n")
        for i, c in enumerate(peer_reviewed, 1):
            venue = c.get("source_db", "")
            lines.append(f"{i}. {c.get('title', 'Untitled')} ({c.get('year', '?')}, {venue}) [{c.get('match_tier', '?')}]\n")

    if preprints:
        lines.append("### Preprints\n")
        for i, c in enumerate(preprints, 1):
            lines.append(f"{i}. {c.get('title', 'Untitled')} ({c.get('year', '?')}, preprint) [{c.get('match_tier', '?')}]\n")

    if ambiguous:
        lines.append("### Excluded\n")
        for c in ambiguous:
            lines.append(f"- {c.get('title', 'Untitled')} ({c.get('year', '?')}) — ambiguous match, excluded from research summaries\n")

    lines.append("## Position Signals\n")
    if position_signals.get("signals"):
        lines.append("| Strength | Type | Details | Evidence |\n")
        lines.append("|---|---|---|---|\n")
        for sig in position_signals["signals"]:
            refs = ", ".join(sig.get("evidence_refs", []))
            lines.append(f"| {sig['signal_strength']} | {sig.get('position_category', 'unknown')} | {sig.get('details', '')[:80]} | [{refs}] |\n")
    else:
        lines.append("No position signals found.\n")

    lines.append("\n## Lab Summary Assessment\n")
    lines.append("| Dimension | Assessment | Confidence | Evidence |\n")
    lines.append("|---|---|---|---|\n")
    for dim in fit_assessment.get("dimensions", []):
        refs = ", ".join(dim.get("evidence_refs", [])) or "—"
        lines.append(f"| {dim['dimension']} | {dim.get('assessment', '')[:80]} | {dim['confidence']} | [{refs}] |\n")

    lines.append(f"\n**Overall assessment: {lab_profile.get('overall_assessment', 'unknown')}** ({lab_profile.get('evidence_summary', {}).get('weak_evidence_ratio', 0)} weak evidence ratio)\n")

    methods_dim = next((d for d in fit_assessment.get("dimensions", []) if d.get("dimension") == "methods_and_approaches"), None)
    lines.append("\n## Methods and Approaches\n")
    if methods_dim:
        refs = ", ".join(methods_dim.get("evidence_refs", [])) or "—"
        lines.append(f"{methods_dim.get('assessment', 'No method information available.')} [{refs}]\n")
    else:
        lines.append("No method information available.\n")

    funding_dim = next((d for d in fit_assessment.get("dimensions", []) if d.get("dimension") == "funding_indicators"), None)
    lines.append("\n## Funding/Resource Indicators\n")
    if funding_dim:
        refs = ", ".join(funding_dim.get("evidence_refs", [])) or "—"
        lines.append(f"{funding_dim.get('assessment', 'No funding/resource information available.')} [{refs}]\n")
    else:
        lines.append("No funding/resource information available.\n")

    lines.append("\n## Limitations\n")
    for lim in lab_profile.get("limitations", []):
        lines.append(f"- {lim}\n")

    return "\n".join(lines)


def build_audit(
    lab_id: str,
    site_evidence: list[dict],
    pub_evidence: list[dict],
    curated: dict,
    themes: dict,
    position_signals: dict,
    fit_assessment: dict,
    lab_profile: dict,
) -> dict:
    confirmed = [c for c in curated_list(curated) if c.get("match_tier") == "confirmed"]
    likely = [c for c in curated_list(curated) if c.get("match_tier") == "likely"]
    ambiguous = [c for c in curated_list(curated) if c.get("match_tier") == "ambiguous"]

    confirmed_sigs = [s for s in position_signals.get("signals", []) if s["signal_strength"] == "confirmed_opening"]
    generic_sigs = [s for s in position_signals.get("signals", []) if s["signal_strength"] == "generic_recruitment"]

    dims_assessed = sum(1 for d in fit_assessment.get("dimensions", []) if d["status"] == "assessed")
    dims_partial = sum(1 for d in fit_assessment.get("dimensions", []) if d["status"] == "partial")
    dims_unavail = sum(1 for d in fit_assessment.get("dimensions", []) if d["status"] == "unavailable")

    all_refs = []
    for sig in position_signals.get("signals", []):
        all_refs.extend(sig.get("evidence_refs", []))
    for dim in fit_assessment.get("dimensions", []):
        all_refs.extend(dim.get("evidence_refs", []))
    for theme in lab_profile.get("research_themes", []):
        all_refs.extend(theme.get("evidence_refs", []))

    weak_count = sum(1 for ev in site_evidence if ev.get("evidence_quality") in ("link_text_only", "none"))
    weak_ratio = round(weak_count / len(site_evidence), 2) if site_evidence else 0.0

    blocking = []
    warnings = []
    repair_hints = []

    if not site_evidence:
        blocking.append("No site evidence found.")
    if not confirmed and not likely:
        blocking.append("No confirmed or likely publications found.")
    if not position_signals.get("signals"):
        warnings.append("No position signals found.")

    for ws in generic_sigs:
        warnings.append(f"Signal {ws['signal_id']}: generic recruitment — must not be reported as a confirmed open position.")

    if ambiguous:
        warnings.append(f"{len(ambiguous)} publication(s) ambiguous and excluded from research themes.")

    fi_dim = next((d for d in fit_assessment.get("dimensions", []) if d["dimension"] == "funding_indicators"), None)
    if fi_dim and fi_dim["status"] == "unavailable":
        warnings.append("Funding indicators dimension is unavailable.")
        repair_hints.append("Check lab site for grant or funding pages if funding indicators are important.")

    if dims_unavail > 2:
        warnings.append(f"{dims_unavail} dimensions unavailable — limited assessment quality.")

    status = "fail" if blocking else ("partial" if warnings or dims_unavail > 0 else "pass")

    return {
        "lab_id": lab_id,
        "status": status,
        "metrics": {
            "site_evidence_count": len(site_evidence),
            "publication_evidence_count": len(pub_evidence),
            "confirmed_publication_count": len(confirmed),
            "likely_publication_count": len(likely),
            "ambiguous_publications_excluded": len(ambiguous),
            "position_signals_count": len(position_signals.get("signals", [])),
            "confirmed_position_signals": len(confirmed_sigs),
            "generic_position_signals": len(generic_sigs),
            "dimensions_assessed": dims_assessed,
            "dimensions_partial": dims_partial,
            "dimensions_unavailable": dims_unavail,
            "evidence_refs_total": len(all_refs),
            "weak_evidence_ratio": weak_ratio,
        },
        "blocking": blocking,
        "warnings": warnings,
        "repair_hints": repair_hints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to lab_summary_input.json")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--fixtures", help="Directory with fixture files (optional)")
    args = parser.parse_args()

    inp = read_json(Path(args.input))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    lab_id = inp.get("lab_id", "unknown-lab")
    lab_name = inp.get("lab_name", "Unknown Lab")
    pi_name = inp.get("pi_name", "Unknown PI")
    institution = inp.get("institution", "Unknown")
    lab_url = inp.get("lab_url", "")

    fixtures = Path(args.fixtures) if args.fixtures else None

    site_path = find_fixture(fixtures, "lab_site_evidence.jsonl", "lab_site_evidence.sample.jsonl")
    site_evidence = read_jsonl(site_path) if site_path else []

    curated_path = find_fixture(fixtures, "publications.curated.json", "publications.curated.sample.json")
    curated = read_json(curated_path) if curated_path else {"candidates": [], "tier_counts": {}}

    pub_ev_path = find_fixture(fixtures, "publication_evidence.jsonl", "publication_evidence.sample.jsonl")
    pub_evidence = read_jsonl(pub_ev_path) if pub_ev_path else []

    themes_path = find_fixture(fixtures, "research_theme_profile.json", "research_theme_profile.sample.json")
    themes = read_json(themes_path) if themes_path else {"themes": []}

    position_signals = build_position_signals(site_evidence, lab_id)
    fit_assessment = build_lab_summary_assessment(lab_id, themes, site_evidence, curated, position_signals)
    lab_profile = build_lab_profile(lab_id, lab_name, pi_name, institution, lab_url,
                                     themes, curated, position_signals, fit_assessment,
                                     site_evidence, pub_evidence)
    report = build_report(lab_name, pi_name, institution, curated, themes,
                          position_signals, fit_assessment, lab_profile)
    audit = build_audit(lab_id, site_evidence, pub_evidence, curated, themes,
                        position_signals, fit_assessment, lab_profile)

    write_json(out / "position_signals.json", position_signals)
    write_json(out / "lab_summary_assessment.json", fit_assessment)
    write_json(out / "lab_profile.json", lab_profile)
    write_text(out / "report.md", report)
    write_json(out / "lab_summary_audit.json", audit)

    sig_count = len(position_signals.get("signals", []))
    dims = len(fit_assessment.get("dimensions", []))
    themes_count = len(lab_profile.get("research_themes", []))
    print(f"Wrote {sig_count} signals, {dims} dimensions, {themes_count} themes, audit status={audit['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

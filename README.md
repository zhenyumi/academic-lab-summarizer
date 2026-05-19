# Academic Lab Summarizer Agent Skills

Evidence-first skills for helping AI coding agents summarize one academic lab from its website, recent publications, and recruitment signals.

[中文版本 / Chinese version](README.zh-CN.md)

## Project Goal

`academic-lab-summarizer` gives AI agents a structured way to build a traceable profile of a specific academic lab. The workflow focuses on three things that should not be guessed: what the lab studies, what the lab has published recently, and whether there are open or likely recruitment opportunities.

Every output follows a "show your work" approach. Lab claims point back to source evidence, publication matches keep source provenance and confidence tiers, and hiring signals must say whether a role is confirmed, likely, generic, closed/past, absent, or unknown.

The target users are students, researchers, and research staff who want to understand a lab before contacting it, applying to it, or comparing it with other labs.

## Requirements

- **Python 3.9+**. The shipped scripts use only the Python standard library.
- One of these AI coding agents:
  - [Claude Code](https://claude.ai)
  - [Codex CLI](https://github.com/openai/codex)
  - [OpenCode](https://opencode.ai)
  - [OpenClaw](https://clawhub.ai)

## Installation

### Claude Code

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-claude.sh                              # Install globally (all skills)
./install-claude.sh --project /path/to/project   # Or install to a specific project
./install-claude.sh --categories "lab-site-evidence-extraction,lab-publication-profile"  # Pick specific skills
./install-claude.sh --update                     # Update only changed skills
./install-claude.sh --list                       # See what's available
./install-claude.sh --validate                   # Check everything is in order
./install-claude.sh --verbose --dry-run          # Preview with details
./install-claude.sh --uninstall                  # Remove all installed skills
```

### Codex CLI

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-codex.sh                               # Install globally (all skills)
./install-codex.sh --project /path/to/project    # Or install to a specific project
./install-codex.sh --categories "academic-lab-summarizer,lab-profile-synthesis"  # Pick specific skills
./install-codex.sh --update                      # Update only changed skills
./install-codex.sh --list                        # See what's available
./install-codex.sh --validate                    # Check everything is in order
./install-codex.sh --verbose --dry-run           # Preview with details
./install-codex.sh --uninstall                   # Remove all installed skills
```

### OpenCode

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-opencode.sh                            # Install globally (all skills)
./install-opencode.sh --project /path/to/project # Or install to a specific project
./install-opencode.sh --categories "academic-lab-summarizer"  # Pick specific skills
./install-opencode.sh --update                   # Update only changed skills
./install-opencode.sh --list                     # See what's available
./install-opencode.sh --validate                 # Check everything is in order
./install-opencode.sh --verbose --dry-run        # Preview with details
./install-opencode.sh --uninstall                # Remove all installed skills
```

### OpenClaw

```bash
git clone https://github.com/zhenyumi/academic-lab-summarizer.git
cd academic-lab-summarizer
./install-openclaw.sh                            # Install globally (all skills)
./install-openclaw.sh --project /path/to/project # Or install to a specific project
./install-openclaw.sh --update                   # Update only changed skills
./install-openclaw.sh --list                     # See what's available
./install-openclaw.sh --validate                 # Check everything is in order
./install-openclaw.sh --verbose --dry-run        # Preview with details
./install-openclaw.sh --uninstall                # Remove all installed skills
```

Common options across all installers: `--categories` to install only specific skills, `--update` to refresh skills that changed, `--dry-run` to preview without writing, `--verbose` for detailed output, and `--force` to overwrite existing installed skill content.

> **Platform support:** The install scripts are Bash scripts. They work on macOS, Linux, and Windows (via Git Bash, WSL, or another Bash-compatible shell). Do not run them with `sh`, `zsh`, or native PowerShell/CMD.

## Reports and Files

The workflow writes run artifacts and reports in two main locations:

```text
lab_summaries/<lab_id>/
  lab_summary_input.json
  lab_site_evidence.jsonl
  publication_search_plan.json
  publication_candidates.jsonl
  publications.curated.json
  publication_evidence.jsonl
  publication_audit.json
  research_theme_profile.json
  position_signals.json
  lab_summary_assessment.json
  lab_profile.json
  report.md
  lab_summary_audit.json
  lab_summary_manifest.json

reports/lab-summaries/<task_id>/
  report.html
  report.md
  report_manifest.json
  assets/
  artifacts/
```

`report.html` is the default user-facing report with interactive navigation, clickable evidence references, and collapsible sections. `report.md` is the matching Markdown report. JSON and JSONL artifacts are kept alongside the report so the agent can audit evidence, rerun individual steps, or explain how a conclusion was reached.

## Skill Categories

### Lab Evidence

Extract structured source material from one known lab website.

| Skill | What it does |
|-------|--------------|
| `lab-site-evidence-extraction` | Reads a lab website and extracts evidence for lab identity, PI and affiliation, research directions, people, methods, funding/resource indicators, publication references, and hiring/open-position language. |

### Publication Profile

Publication analysis is a core v1 contract, not a future add-on.

| Skill | What it does |
|-------|--------------|
| `lab-publication-profile` | Builds a recent publication profile with a tiered search policy, source provenance, match tiers, curated publication status, evidence records, audit output, and research theme synthesis. Lab website publications page is searched first (Tier 0, zero API cost); then OpenAlex and Semantic Scholar (Tier 1); PubMed is required for biomedical, clinical, life-science, and neuroscience labs; Crossref and preprint servers act as enrichment or fallback (Tier 2). API rate limiting with exponential backoff is enforced. |

Ambiguous and rejected publications are excluded from research themes and lab research summaries. Confirmed and likely papers can be summarized with structured overviews covering the research question, methods, key finding, and significance.

### Lab Synthesis

Turn site evidence and publication evidence into a lab profile.

| Skill | What it does |
|-------|--------------|
| `lab-profile-synthesis` | Synthesizes lab identity, research summary, recent publication themes, important recent publications, open positions/recruitment signals, methods, funding/resource indicators, limitations, audit files, and user-facing reports. |

Position analysis is required. `position_signals.json` must be present even when no openings are found. Supported categories are `phd`, `masters`, `undergraduate`, `postdoc`, `research_assistant`, `technician`, `lab_manager`, `staff_scientist`, `other`, and `none`. Generic "join us" language may be reported, but it cannot be upgraded to a confirmed opening without role-specific evidence.

### Workflow

Run the whole lab summarization pipeline.

| Skill | What it does |
|-------|--------------|
| `academic-lab-summarizer` | Coordinates lab site extraction, publication profiling, and lab profile synthesis. It tracks required artifacts, validates handoffs, and writes the final manifest. |

## Example Usage

Once installed, talk to your agent naturally:

Recommended direct workflow invocation:

```text
/academic-lab-summarizer <lab-homepage-or-profile-url>
```

Focused worker invocations:

```text
/lab-site-evidence-extraction <lab-homepage-url>
/lab-publication-profile <lab-name-or-pi-name>
/lab-profile-synthesis <lab-summary-artifact-directory>
```

Examples:

```text
"Run a full lab summary for <lab-url>. Include recent publications and hiring signals."
"Summarize this lab's last few years of publications using OpenAlex, Semantic Scholar, and PubMed where relevant."
"Check whether this lab has confirmed openings for PhD students, postdocs, RAs, or other research staff."
"Create an evidence-backed profile for <PI name>'s lab with limitations clearly separated from confirmed facts."
"Generate the final HTML and Markdown reports from this lab summary artifact directory."
```

## Report Features

The HTML report includes:

- **Sticky section navigation** with scroll-based active state highlighting
- **Clickable evidence references** (`[site:N]`, `[pub:N]`) that auto-open the evidence panel and scroll to the target with a highlight animation
- **Publication cards** with numbered entries, author display (first + last author, PI name highlighted), and structured overview fields (research question, key finding, methods, significance)
- **Collapsible full publication list** sourced from curated confirmed/likely publications
- **Three-tier font size toggle** (A⁻/A/A⁺) with localStorage persistence
- **Return button** after navigating to an evidence reference
- **Print-optimized layout** and `prefers-reduced-motion` support

## Behind the Scenes

Each skill includes runner scripts, templates, references, and example artifacts. Agents can copy templates into a run-local tools directory and adapt those copies for real websites or API calls. The shipped code stays standard-library first so it is easy to inspect, move, and run in constrained environments.

The workflow is intentionally conservative. It separates confirmed facts from likely or ambiguous evidence, keeps publication provenance visible, and records recruitment signals without inflating weak language into definite openings.

## Validation

```bash
python lab-site-evidence-extraction/scripts/validate_lab_site_artifacts.py --examples
python lab-publication-profile/scripts/validate_publication_profile_artifacts.py --examples
python lab-profile-synthesis/scripts/validate_lab_summary_artifacts.py --examples
```

## License

MIT License. See [LICENSE](LICENSE) for details.

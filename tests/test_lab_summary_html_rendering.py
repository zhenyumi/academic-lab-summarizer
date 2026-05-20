from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "lab-profile-synthesis" / "templates" / "scripts" / "build_lab_summary_html.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_lab_summary_html", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestLabSummaryHtmlRendering(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = load_builder()

    def render(self, profile: dict) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            return self.builder.render_html(
                lab_summaries_dir=report_dir,
                report_md="# Lab Profile: Example\n",
                profile=profile,
                fit_assessment={"dimensions": []},
                positions={"signals": []},
                site_audit={"status": "pass", "metrics": {}, "warnings": []},
                pub_audit={"status": "pass", "metrics": {}, "warnings": []},
                fit_audit={"status": "pass", "metrics": {}, "warnings": []},
                manifest={"overall_status": "partial"},
                artifact_prefix="artifacts/",
                asset_prefix="",
            )

    def test_important_publication_shows_evidence_level_and_source(self) -> None:
        html = self.render({
            "lab_name": "Example Lab",
            "important_publications": [{
                "candidate_id": 1,
                "title": "Open access full text paper",
                "year": 2025,
                "publication_type": "peer_reviewed",
                "match_tier": "confirmed",
                "evidence_level": "full_text",
                "summary_source": {
                    "type": "pmc",
                    "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/",
                    "retrieval_status": "available",
                },
                "publication_overview": {
                    "research_question": "What is tested?",
                    "key_finding": "The paper reports a result.",
                    "methods": "The study used open-access full text.",
                    "significance": "The finding is relevant.",
                },
            }],
            "limitations": [
                "Only open access full text was used for important-publication enrichment.",
                "Funding information was not available in the collected evidence.",
            ],
        })

        self.assertIn("Evidence: Full Text", html)
        self.assertIn("Source: pmc", html)
        self.assertIn("available", html)

    def test_limitations_section_renders_even_when_empty(self) -> None:
        html = self.render({
            "lab_name": "Example Lab",
            "important_publications": [],
            "limitations": [],
        })

        self.assertIn('class="limitations"', html)
        self.assertIn("No limitations recorded.", html)


if __name__ == "__main__":
    unittest.main()

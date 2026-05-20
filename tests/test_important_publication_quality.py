from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "lab-profile-synthesis" / "templates" / "scripts" / "run_lab_profile_synthesis.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_lab_profile_synthesis", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestImportantPublicationQuality(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_sentence_split_preserves_decimal_gene_notation(self) -> None:
        text = (
            "The role of 16p11.2 deletion in interneuron maturation is unclear. "
            "Using single-cell profiling, we found altered PV interneuron states."
        )

        sentences = self.runner._split_sentences(text)

        self.assertEqual(
            [
                "The role of 16p11.2 deletion in interneuron maturation is unclear",
                "Using single-cell profiling, we found altered PV interneuron states",
            ],
            sentences,
        )

    def test_fragmentary_abstract_is_not_valid(self) -> None:
        candidate = {
            "title": "Circuit mechanisms in PV interneurons",
            "abstract": (
                "channels on PV interneurons. These findings demonstrate altered inhibition "
                "and suggest a disease-relevant circuit mechanism."
            ),
        }

        self.assertFalse(self.runner._has_valid_abstract(candidate))

    def test_question_style_abstract_is_valid(self) -> None:
        candidate = {
            "title": "Neural crest derivatives in vertebrates",
            "abstract": (
                "Which developmental programs shape neural crest derivatives in vertebrates remains an active question. "
                "Using developmental profiling and comparative analysis, we report candidate regulatory programs."
            ),
        }

        self.assertTrue(self.runner._has_valid_abstract(candidate))

    def test_build_important_publications_sets_abstract_evidence_level(self) -> None:
        curated = {
            "candidates": [
                {
                    "candidate_id": 1,
                    "title": "Interneuron mechanisms in disease",
                    "year": 2026,
                    "venue": "Science",
                    "publication_type": "peer_reviewed",
                    "match_tier": "confirmed",
                    "abstract": (
                        "The role of 16p11.2 deletion in interneuron maturation is unclear. "
                        "Using single-cell profiling and electrophysiology, we found altered PV interneuron states. "
                        "These findings identify a disease-relevant inhibitory circuit mechanism."
                    ),
                }
            ]
        }
        themes = {"themes": [{"theme": "Interneuron disease mechanisms", "supporting_publications": [1]}]}

        pubs = self.runner.build_important_publications(curated, themes)

        self.assertEqual("abstract", pubs[0]["evidence_level"])
        self.assertEqual("abstract", pubs[0]["summary_source"]["type"])
        self.assertEqual("available", pubs[0]["summary_source"]["retrieval_status"])

    def test_overview_significance_falls_back_to_finding_without_theme(self) -> None:
        candidate = {
            "title": "Wnt signaling regulates neural stem cell proliferation",
            "abstract": (
                "How Wnt signaling regulates neural stem cell proliferation during development is not fully resolved. "
                "Using mouse neural stem cell cultures and proliferation assays, we found that Wnt activity controls progenitor expansion."
            ),
        }

        overview = self.runner._build_publication_overview(candidate, "")

        self.assertTrue(overview["significance"])

    def test_full_text_enrichment_only_updates_important_publications(self) -> None:
        important = [
            {"candidate_id": 1, "publication_overview": {}, "evidence_level": "abstract"},
            {"candidate_id": 2, "publication_overview": {}, "evidence_level": "abstract"},
        ]
        full_text_records = [
            {
                "candidate_id": 1,
                "source_type": "pmc",
                "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/",
                "retrieval_status": "available",
                "text": (
                    "The mechanism linking 16p11.2 deletion to interneuron dysfunction is unclear. "
                    "We used single-cell profiling and electrophysiology in mouse models. "
                    "We found altered PV interneuron states and disrupted inhibitory circuits."
                ),
            },
            {
                "candidate_id": 99,
                "source_type": "pmc",
                "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC99/",
                "retrieval_status": "available",
                "text": "This non-important publication must not be added to the important set.",
            },
        ]

        enriched = self.runner.enrich_important_publications_with_full_text(important, full_text_records)

        by_id = {pub["candidate_id"]: pub for pub in enriched}
        self.assertEqual({1, 2}, set(by_id))
        self.assertEqual("full_text", by_id[1]["evidence_level"])
        self.assertEqual("pmc", by_id[1]["summary_source"]["type"])
        self.assertEqual("abstract", by_id[2]["evidence_level"])

    def test_runner_audit_counts_important_publication_evidence_levels(self) -> None:
        lab_profile = {
            "research_themes": [],
            "important_publications": [
                {"candidate_id": 1, "evidence_level": "full_text", "publication_overview": {"research_question": "Q", "key_finding": "K", "methods": "M", "significance": "S"}},
                {"candidate_id": 2, "evidence_level": "abstract", "publication_overview": {"research_question": "Q", "key_finding": "K", "methods": "", "significance": "S"}},
                {"candidate_id": 3, "evidence_level": "metadata_only", "publication_overview": {"research_question": "Q", "key_finding": "K", "methods": "M", "significance": "S"}},
            ],
        }
        result = self.runner.build_audit(
            "lab-1",
            site_evidence=[{"evidence_quality": "research_description"}],
            pub_evidence=[],
            curated={"candidates": [{"candidate_id": 1, "match_tier": "confirmed"}]},
            themes={"themes": []},
            position_signals={"signals": []},
            fit_assessment={"dimensions": []},
            lab_profile=lab_profile,
        )

        self.assertEqual(1, result["metrics"]["important_publication_full_text_count"])
        self.assertEqual(1, result["metrics"]["important_publication_abstract_count"])
        self.assertEqual(1, result["metrics"]["important_publication_metadata_only_count"])
        self.assertEqual(1, result["metrics"]["important_publication_missing_overview_field_count"])

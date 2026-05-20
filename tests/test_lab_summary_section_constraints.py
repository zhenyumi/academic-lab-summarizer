from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "lab-profile-synthesis" / "scripts" / "validate_lab_summary_artifacts.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_lab_summary_artifacts", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestLabSummarySectionConstraints(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def valid_profile(self) -> dict:
        return {
            "lab_id": "lab-1",
            "lab_name": "Example Lab",
            "pi_name": "Jane Doe",
            "institution": "Example University",
            "lab_url": "https://example.edu/lab",
            "research_themes": [
                {"theme": "Neural circuits", "description": "Circuit mechanisms.", "confidence": "high", "evidence_refs": ["pub:1"]}
            ],
            "important_publications": [
                {
                    "candidate_id": 1,
                    "title": "Circuit mechanisms",
                    "publication_overview": {
                        "one_line": "Circuit mechanisms.",
                        "research_question": "What mechanism links genotype to circuit dysfunction?",
                        "key_finding": "The study identifies altered interneuron states.",
                        "methods": "Single-cell profiling and electrophysiology.",
                        "significance": "Defines a disease-relevant circuit mechanism.",
                    },
                    "evidence_level": "abstract",
                    "summary_source": {"type": "abstract", "retrieval_status": "available", "source_url": ""},
                },
                {
                    "candidate_id": 2,
                    "title": "Developmental mechanisms",
                    "publication_overview": {
                        "one_line": "Developmental mechanisms.",
                        "research_question": "How do developmental programs shape interneuron fate?",
                        "key_finding": "The study finds altered maturation trajectories.",
                        "methods": "Mouse models and transcriptomics.",
                        "significance": "Connects development to lab research themes.",
                    },
                    "evidence_level": "abstract",
                    "summary_source": {"type": "abstract", "retrieval_status": "available", "source_url": ""},
                },
                {
                    "candidate_id": 3,
                    "title": "Synaptic mechanisms",
                    "publication_overview": {
                        "one_line": "Synaptic mechanisms.",
                        "research_question": "How are synapses altered in disease models?",
                        "key_finding": "The study finds impaired inhibitory synaptic function.",
                        "methods": "Patch-clamp electrophysiology.",
                        "significance": "Links synaptic mechanisms to lab priorities.",
                    },
                    "evidence_level": "abstract",
                    "summary_source": {"type": "abstract", "retrieval_status": "available", "source_url": ""},
                },
            ],
            "confirmed_publication_count": 3,
            "likely_publication_count": 0,
            "position_signal": "none",
            "overall_assessment": "usable_profile",
            "evidence_summary": {"site_evidence_count": 1, "publication_evidence_count": 3, "weak_evidence_ratio": 0.0},
            "limitations": ["Funding evidence was not found on reviewed pages.", "Position information was not found on reviewed pages."],
        }

    def test_important_publication_empty_overview_field_is_invalid(self) -> None:
        profile = self.valid_profile()
        profile["important_publications"][0]["publication_overview"]["methods"] = ""
        errors: list[str] = []

        self.validator.validate_lab_profile(profile, {1, 2, 3}, set(), errors)

        self.assertIn(
            "lab_profile.json: important_publications[0] publication_overview empty 'methods'",
            errors,
        )

    def test_important_publication_requires_evidence_level(self) -> None:
        profile = self.valid_profile()
        del profile["important_publications"][0]["evidence_level"]
        errors: list[str] = []

        self.validator.validate_lab_profile(profile, {1, 2, 3}, set(), errors)

        self.assertIn("lab_profile.json: important_publications[0] missing evidence_level", errors)

    def test_limitations_require_two_specific_items(self) -> None:
        profile = self.valid_profile()
        profile["limitations"] = ["Limited evidence."]
        errors: list[str] = []

        self.validator.validate_lab_profile(profile, {1, 2, 3}, set(), errors)

        self.assertIn("lab_profile.json: limitations must include at least 2 specific items", errors)

    def test_assessment_must_cover_all_six_dimensions(self) -> None:
        assessment = {
            "lab_id": "lab-1",
            "overall_assessment": "usable_profile",
            "overall_confidence": "medium",
            "dimensions": [
                {
                    "dimension": "research_focus",
                    "description": "Research focus.",
                    "assessment": "Assessed from evidence.",
                    "confidence": "medium",
                    "evidence_refs": ["pub:1"],
                    "status": "assessed",
                    "limitations": [],
                }
            ],
        }
        errors: list[str] = []

        self.validator.validate_fit_assessment(assessment, set(), {1}, errors)

        self.assertIn("lab_summary_assessment.json: must include exactly 6 dimensions", errors)

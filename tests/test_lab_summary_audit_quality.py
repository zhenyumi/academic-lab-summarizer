from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "lab-profile-synthesis" / "templates" / "scripts" / "audit_lab_summary.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_lab_summary", AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class TestLabSummaryAuditQuality(unittest.TestCase):
    def setUp(self) -> None:
        self.audit_module = load_audit_module()

    def write_artifacts(self, artifact_dir: Path, profile: dict) -> None:
        write_json(
            artifact_dir / "position_signals.json",
            {"lab_id": "lab-1", "signals": [], "overall_position_signal": "none"},
        )
        write_json(
            artifact_dir / "lab_summary_assessment.json",
            {
                "lab_id": "lab-1",
                "overall_assessment": "usable_profile",
                "overall_confidence": "medium",
                "dimensions": [
                    {"dimension": "research_focus", "status": "assessed", "evidence_refs": ["pub:1"]},
                    {"dimension": "publication_profile", "status": "assessed", "evidence_refs": ["pub:1"]},
                    {"dimension": "position_availability", "status": "unavailable", "evidence_refs": []},
                    {"dimension": "lab_activity_and_trajectory", "status": "partial", "evidence_refs": ["pub:1"]},
                    {"dimension": "methods_and_approaches", "status": "assessed", "evidence_refs": ["site:1"]},
                    {"dimension": "funding_indicators", "status": "unavailable", "evidence_refs": []},
                ],
            },
        )
        write_json(artifact_dir / "lab_profile.json", profile)
        (artifact_dir / "lab_site_evidence.jsonl").write_text(
            json.dumps({"evidence_id": 1, "claim_type": "research_direction", "evidence_quality": "research_description"}) + "\n",
            encoding="utf-8",
        )
        (artifact_dir / "publication_evidence.jsonl").write_text("", encoding="utf-8")
        write_json(
            artifact_dir / "publications.curated.json",
            {
                "candidates": [
                    {"candidate_id": 1, "match_tier": "confirmed"},
                    {"candidate_id": 2, "match_tier": "confirmed"},
                    {"candidate_id": 3, "match_tier": "likely"},
                ]
            },
        )
        write_json(artifact_dir / "research_theme_profile.json", {"themes": []})

    def test_audit_counts_evidence_levels_and_missing_overview_fields(self) -> None:
        profile = {
            "lab_id": "lab-1",
            "important_publications": [
                {
                    "candidate_id": 1,
                    "title": "Full text paper",
                    "evidence_level": "full_text",
                    "publication_overview": {
                        "research_question": "Question.",
                        "key_finding": "Finding.",
                        "methods": "Methods.",
                        "significance": "Significance.",
                    },
                },
                {
                    "candidate_id": 2,
                    "title": "Abstract paper",
                    "evidence_level": "abstract",
                    "publication_overview": {
                        "research_question": "Question.",
                        "key_finding": "Finding.",
                        "methods": "",
                        "significance": "Significance.",
                    },
                },
                {
                    "candidate_id": 3,
                    "title": "Metadata paper",
                    "evidence_level": "metadata_only",
                    "publication_overview": {
                        "research_question": "Question.",
                        "key_finding": "Finding.",
                        "methods": "Methods.",
                        "significance": "Significance.",
                    },
                },
            ],
            "research_themes": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            artifact_dir = Path(tmp)
            self.write_artifacts(artifact_dir, profile)

            result = self.audit_module.audit(artifact_dir)

        self.assertEqual(1, result["metrics"]["important_publication_full_text_count"])
        self.assertEqual(1, result["metrics"]["important_publication_abstract_count"])
        self.assertEqual(1, result["metrics"]["important_publication_metadata_only_count"])
        self.assertEqual(1, result["metrics"]["important_publication_missing_overview_field_count"])
        self.assertTrue(any("missing overview fields" in warning for warning in result["warnings"]))

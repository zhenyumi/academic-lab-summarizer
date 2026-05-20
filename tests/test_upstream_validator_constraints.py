from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_VALIDATOR_PATH = ROOT / "lab-site-evidence-extraction" / "scripts" / "validate_lab_site_artifacts.py"
PUB_VALIDATOR_PATH = ROOT / "lab-publication-profile" / "scripts" / "validate_publication_profile_artifacts.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestUpstreamValidatorConstraints(unittest.TestCase):
    def test_site_evidence_requires_research_direction(self) -> None:
        validator = load_module(SITE_VALIDATOR_PATH, "validate_lab_site_artifacts")

        errors = validator._validate_lab_site_evidence([
            {
                "evidence_id": 1,
                "lab_id": "lab-1",
                "source_url": "https://example.edu/lab",
                "snippet": "Jane Doe is the PI.",
                "claim_type": "pi_info",
                "evidence_quality": "profile_snippet",
                "extraction_status": "extracted",
            }
        ])

        self.assertIn("lab_site_evidence.jsonl: missing research_direction evidence", errors)

    def test_publication_audit_requires_abstract_coverage_metrics(self) -> None:
        validator = load_module(PUB_VALIDATOR_PATH, "validate_publication_profile_artifacts")
        audit = {
            "status": "pass",
            "metrics": {
                "total_candidates": 1,
                "confirmed": 1,
                "likely": 0,
                "sufficient": True,
            },
            "source_status": {
                "tier0_available": True,
                "tier1_sufficient": True,
                "tier2_attempted": False,
                "stop_reason": "tier1_sufficient",
                "sources": [],
            },
            "blocking_failures": [],
            "warnings": [],
        }

        errors = validator._validate_audit(audit)

        self.assertIn("publication_audit.json metrics missing field: abstract_coverage_ratio", errors)
        self.assertIn("publication_audit.json metrics missing field: confirmed_likely_abstract_coverage_ratio", errors)

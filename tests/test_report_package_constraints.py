from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
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


class TestReportPackageConstraints(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def write_manifest(self, report_dir: Path, primary_report: str = "report.html") -> None:
        (report_dir / "report_manifest.json").write_text(
            "{\n"
            f'  "primary_report": "{primary_report}",\n'
            '  "markdown_report": "report.md"\n'
            "}\n",
            encoding="utf-8",
        )

    def test_report_package_requires_html_primary_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            (report_dir / "report.md").write_text("# Markdown fallback\n", encoding="utf-8")
            self.write_manifest(report_dir, primary_report="report.md")

            errors = self.validator.validate_report_package(report_dir)

        self.assertIn("report.html: not found", errors)
        self.assertIn("report_manifest.json: primary_report must be report.html", errors)

    def test_complete_report_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            (report_dir / "report.html").write_text("<html></html>\n", encoding="utf-8")
            (report_dir / "report.md").write_text("# Markdown fallback\n", encoding="utf-8")
            (report_dir / "assets").mkdir()
            (report_dir / "artifacts").mkdir()
            self.write_manifest(report_dir)

            errors = self.validator.validate_report_package(report_dir)

        self.assertEqual([], errors)

    def test_cli_can_validate_report_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            (report_dir / "report.html").write_text("<html></html>\n", encoding="utf-8")
            (report_dir / "report.md").write_text("# Markdown fallback\n", encoding="utf-8")
            (report_dir / "assets").mkdir()
            (report_dir / "artifacts").mkdir()
            self.write_manifest(report_dir)

            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), "--report-package", str(report_dir)],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("VALID report package", result.stdout)

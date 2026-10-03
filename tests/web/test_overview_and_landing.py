"""test_overview_and_landing.py — Verification tests for mock contracts and overview data models.

Uses Python standard library only.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


class TestOverviewAndLandingContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.mocks_dir = Path(__file__).resolve().parent.parent.parent / "web-ui" / "src" / "mocks"

    def test_rich_mock_integrity(self) -> None:
        rich_path = self.mocks_dir / "rich.mock.json"
        self.assertTrue(rich_path.is_file(), "rich.mock.json must exist")
        data = json.loads(rich_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("schema_version"), "1.0")
        self.assertIn("capture", data)
        self.assertIn("coverage", data)
        self.assertIn("findings", data)
        self.assertIn("claims", data)
        self.assertIn("rules", data)

        capture = data["capture"]
        self.assertIn("filename", capture)
        self.assertIn("sha256", capture)
        self.assertIn("packet_count", capture)
        self.assertIn("duration_s", capture)
        self.assertIn("truncated", capture)

        coverage = data["coverage"]
        self.assertIn("checks_total", coverage)
        self.assertIn("checks_found", coverage)
        self.assertIn("checks_passed", coverage)
        self.assertIn("checks_gap", coverage)
        self.assertIn("tshark_version", coverage)
        self.assertIn("tshark_exit_clean", coverage)

        # Overview top findings contract
        findings = data["findings"]
        self.assertIsInstance(findings, list)
        self.assertGreater(len(findings), 0)
        for f in findings:
            self.assertIn("rule_id", f)
            self.assertIn("severity", f)
            self.assertIn("title", f)
            self.assertIn("tier", f)

        # Claims tier contract
        claims = data["claims"]
        self.assertIsInstance(claims, list)
        valid_tiers = {
            "OBSERVED",
            "INFERRED_SIDE_CHANNEL",
            "INFERRED_IMPLEMENTATION_DEFAULT",
            "ML_PREDICTION",
            "NOT_OBSERVABLE",
        }
        for c in claims:
            self.assertIn(c["tier"], valid_tiers)
            if c["tier"] == "OBSERVED":
                self.assertEqual(c["confidence"], 1.0)
            elif c["tier"] == "NOT_OBSERVABLE":
                self.assertIsNone(c["value"])

    def test_golden_mock_integrity(self) -> None:
        golden_path = self.mocks_dir / "golden.mock.json"
        self.assertTrue(golden_path.is_file(), "golden.mock.json must exist")
        data = json.loads(golden_path.read_text(encoding="utf-8"))

        # Golden mock invariant from AGENTS.md: findings is empty list, verdicts is non-empty
        self.assertEqual(data.get("schema_version"), "1.0")
        self.assertEqual(data.get("findings"), [])
        self.assertGreater(len(data.get("verdicts", [])), 0)

        # Overview must be able to render capture and coverage
        self.assertIn("capture", data)
        self.assertIn("coverage", data)

    def test_empty_mock_integrity(self) -> None:
        empty_path = self.mocks_dir / "empty.mock.json"
        self.assertTrue(empty_path.is_file(), "empty.mock.json must exist")
        data = json.loads(empty_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("findings"), [])
        self.assertEqual(data.get("claims"), [])
        self.assertEqual(data.get("candidate_sets"), [])
        self.assertEqual(data.get("passes"), [])
        self.assertEqual(data["coverage"]["checks_total"], 15)
        self.assertEqual(data["coverage"]["checks_gap"], 15)


if __name__ == "__main__":
    unittest.main()

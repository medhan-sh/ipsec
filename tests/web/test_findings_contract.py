"""test_findings_contract.py — Validation of findings.json data contract for findings page.

Verifies rich.mock.json, golden.mock.json, and empty.mock.json against
the Findings schema 1.0 requirements.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

MOCKS_DIR = Path(__file__).resolve().parent.parent.parent / "web-ui" / "src" / "mocks"

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
VALID_TIERS = {
    "OBSERVED",
    "INFERRED_SIDE_CHANNEL",
    "INFERRED_IMPLEMENTATION_DEFAULT",
    "ML_PREDICTION",
    "NOT_OBSERVABLE",
}


class TestFindingsContract(unittest.TestCase):
    def test_rich_mock_findings(self) -> None:
        path = MOCKS_DIR / "rich.mock.json"
        self.assertTrue(path.exists(), f"Missing mock at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        findings = data.get("findings", [])
        self.assertGreater(len(findings), 0, "rich.mock.json should have findings")

        rules = data.get("rules", {})
        for idx, finding in enumerate(findings):
            self.assertIn("rule_id", finding, f"Finding {idx} missing rule_id")
            self.assertIn("severity", finding, f"Finding {idx} missing severity")
            self.assertIn(finding["severity"].upper(), VALID_SEVERITIES)
            self.assertIn("title", finding, f"Finding {idx} missing title")
            self.assertIn("tier", finding, f"Finding {idx} missing tier")
            self.assertIn(finding["tier"], VALID_TIERS)
            self.assertIn("evidence", finding, f"Finding {idx} missing evidence")
            self.assertIsInstance(finding["evidence"], list)
            self.assertIn("scope", finding, f"Finding {idx} missing scope")

            # Check rule metadata entry
            rule_id = finding["rule_id"]
            if rule_id in rules:
                meta = rules[rule_id]
                if "explanation" in meta:
                    self.assertIsInstance(meta["explanation"], str)

    def test_golden_mock_zero_findings(self) -> None:
        path = MOCKS_DIR / "golden.mock.json"
        self.assertTrue(path.exists(), f"Missing mock at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        findings = data.get("findings", [])
        passes = data.get("passes", [])
        gaps = data.get("gaps", [])

        # Invariant: golden fixture has exactly 0 findings, non-empty passes, and gaps
        self.assertEqual(len(findings), 0, "golden fixture must have findings: []")
        self.assertGreater(len(passes), 0, "golden fixture should have passes")
        self.assertGreater(len(gaps), 0, "golden fixture should have gaps")

        for p in passes:
            self.assertIn("rule_id", p)
            self.assertIn("tier", p)
            self.assertIn(p["tier"], VALID_TIERS)

    def test_empty_mock_contract(self) -> None:
        path = MOCKS_DIR / "empty.mock.json"
        self.assertTrue(path.exists(), f"Missing mock at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("findings", []), [])
        self.assertEqual(data.get("passes", []), [])
        self.assertEqual(data.get("gaps", []), [])
        self.assertEqual(data.get("coverage", {}).get("checks_total"), 15)


if __name__ == "__main__":
    unittest.main()

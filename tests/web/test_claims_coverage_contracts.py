"""test_claims_coverage_contracts.py — Contract and fixture verification tests for Claims and Coverage.

Verifies that mock fixtures (rich, golden, empty) strictly satisfy
the provenance and coverage accounting invariants defined in AGENTS.md,
CLAUDE.md, and types.ts.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

MOCKS_DIR = Path(__file__).resolve().parent.parent.parent / "web-ui" / "src" / "mocks"
VALID_TIERS = {
    "OBSERVED",
    "INFERRED_SIDE_CHANNEL",
    "INFERRED_IMPLEMENTATION_DEFAULT",
    "ML_PREDICTION",
    "NOT_OBSERVABLE",
}


class TestClaimsCoverageContracts(unittest.TestCase):
    def load_fixture(self, name: str) -> dict:
        path = MOCKS_DIR / name
        self.assertTrue(path.is_file(), f"Fixture not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_golden_mock_contract(self) -> None:
        doc = self.load_fixture("golden.mock.json")
        self.assertEqual(doc.get("schema_version"), "1.0")

        # Coverage accounting check
        cov = doc["coverage"]
        total = cov["checks_total"]
        assessable = cov["checks_assessable"]
        gaps = cov["checks_gap"]
        passed = cov["checks_passed"]
        found = cov["checks_found"]

        self.assertEqual(total, assessable + gaps, "Golden: Total checks must equal assessable + gaps")
        self.assertEqual(assessable, passed + found, "Golden: Assessable checks must equal passed + found")

        # Claims tier contract
        for c in doc.get("claims", []):
            tier = c.get("tier")
            self.assertIn(tier, VALID_TIERS)
            if tier == "OBSERVED":
                self.assertEqual(c.get("confidence"), 1.0, f"OBSERVED claim {c['field']} must have confidence 1.0")
            elif tier == "NOT_OBSERVABLE":
                self.assertIsNone(c.get("value"), f"NOT_OBSERVABLE claim {c['field']} must carry null value")
                self.assertIsNone(c.get("confidence"), f"NOT_OBSERVABLE claim {c['field']} must carry null confidence")

        # Gaps contract
        for g in doc.get("gaps", []):
            self.assertIn("rule_id", g)
            self.assertIn("gap_kind", g)
            self.assertIn(g.get("required_tier"), VALID_TIERS)
            self.assertIn(g.get("actual_tier"), VALID_TIERS)

    def test_rich_mock_contract(self) -> None:
        doc = self.load_fixture("rich.mock.json")
        self.assertEqual(doc.get("schema_version"), "1.0")

        cov = doc["coverage"]
        total = cov["checks_total"]
        assessable = cov["checks_assessable"]
        gaps = cov["checks_gap"]

        self.assertEqual(total, assessable + gaps, "Rich: Total checks must equal assessable + gaps")

        # Claims tier contract
        for c in doc.get("claims", []):
            tier = c.get("tier")
            self.assertIn(tier, VALID_TIERS)
            if tier == "OBSERVED":
                self.assertEqual(c.get("confidence"), 1.0, f"OBSERVED claim {c['field']} must have confidence 1.0")
            elif tier == "NOT_OBSERVABLE":
                self.assertIsNone(c.get("value"), f"NOT_OBSERVABLE claim {c['field']} must carry null value")

        # Gaps contract
        for g in doc.get("gaps", []):
            self.assertIn("rule_id", g)
            self.assertIn("gap_kind", g)
            self.assertIn("reason", g)
            self.assertTrue(len(g["reason"]) > 0, f"Gap {g['rule_id']} must have non-empty reason")

    def test_empty_mock_contract(self) -> None:
        doc = self.load_fixture("empty.mock.json")
        self.assertEqual(doc.get("schema_version"), "1.0")
        cov = doc["coverage"]
        self.assertEqual(cov["checks_total"], 15)
        self.assertEqual(cov["checks_gap"], 15)
        self.assertEqual(cov["checks_assessable"], 0)
        self.assertEqual(len(doc.get("claims", [])), 0)
        self.assertEqual(len(doc.get("passes", [])), 0)
        self.assertEqual(len(doc.get("gaps", [])), 0)


if __name__ == "__main__":
    unittest.main()

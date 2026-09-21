"""Closes the disclosed duplication risk flagged in reports/phase-6.md's
Known gaps: `output/report.py`'s `TIER_ORDER` duplicates `core.claims.Tier`'s
member names as plain strings (required — `output/` may not import
project-local code, see tests/test_import_graph.py's `"output": set()`).
Tests are not part of the dependency graph that test enforces, so a test
file is allowed to import both sides and assert they still agree — the
one place this drift could actually be caught before it ships.
"""

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.output.report import TIER_ORDER


def test_tier_order_matches_the_frozen_tier_enum_exactly():
    assert [t.name for t in Tier] == TIER_ORDER

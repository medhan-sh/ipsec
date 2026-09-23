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


def test_every_tier_has_a_label_and_an_explanation():
    """Same drift risk, one level up: a tier added to the frozen enum
    without a label renders as a bare enum name, and without an
    explanation the provenance section silently omits it — which is the
    one concept this report exists to teach.
    """
    from ipsec_analyzer.output.report import TIER_EXPLANATIONS, TIER_LABELS

    names = {t.name for t in Tier}
    assert set(TIER_LABELS) == names
    assert set(TIER_EXPLANATIONS) == names
    for name in names:
        assert len(TIER_EXPLANATIONS[name].split()) >= 30, f"{name}: explanation too short"


def test_every_gap_kind_has_a_label_and_an_explanation():
    """The gap-kind vocabulary is closed and validated at rule-load time
    (assessment/rules/schema.py::VALID_GAP_KINDS); the report duplicates
    it to render it, so the same agreement has to hold.
    """
    from ipsec_analyzer.assessment.rules.schema import VALID_GAP_KINDS
    from ipsec_analyzer.output.report import GAP_KIND_EXPLANATIONS, GAP_KIND_LABELS

    assert set(GAP_KIND_LABELS) == set(VALID_GAP_KINDS)
    assert set(GAP_KIND_EXPLANATIONS) == set(VALID_GAP_KINDS)

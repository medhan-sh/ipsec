import inspect

import pytest

from claims import CandidateSet, Claim, Tier, TierPromotionError, eliminate, rank


def make_observed(field="x", value=1, evidence=(1,)):
    return Claim(
        field=field,
        value=value,
        tier=Tier.OBSERVED,
        confidence=1.0,
        method="test",
        evidence=evidence,
    )


class TestClaimValidation:
    def test_observed_claim_with_confidence_1_is_valid(self):
        claim = make_observed()
        assert claim.tier is Tier.OBSERVED
        assert claim.confidence == 1.0

    def test_observed_claim_rejects_confidence_099(self):
        with pytest.raises(ValueError):
            Claim(
                field="x",
                value=1,
                tier=Tier.OBSERVED,
                confidence=0.99,
                method="test",
                evidence=(1,),
            )

    def test_not_observable_claim_is_valid_with_no_value(self):
        claim = Claim(
            field="x",
            value=None,
            tier=Tier.NOT_OBSERVABLE,
            confidence=0.0,
            method="test",
            evidence=(),
        )
        assert claim.value is None

    def test_not_observable_claim_rejects_a_value(self):
        with pytest.raises(ValueError):
            Claim(
                field="x",
                value="something",
                tier=Tier.NOT_OBSERVABLE,
                confidence=0.0,
                method="test",
                evidence=(),
            )

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            Claim(
                field="x",
                value=1,
                tier=Tier.ML_PREDICTION,
                confidence=1.5,
                method="test",
                evidence=(),
            )


class TestTierPromotion:
    def test_derived_claim_at_or_below_ceiling_is_valid(self):
        base = Claim(
            field="a",
            value=1,
            tier=Tier.ML_PREDICTION,
            confidence=0.5,
            method="model",
            evidence=(),
        )
        derived = Claim(
            field="b",
            value=2,
            tier=Tier.ML_PREDICTION,
            confidence=0.5,
            method="derive",
            evidence=(),
            derived_from=(base,),
        )
        assert derived.tier is Tier.ML_PREDICTION

    def test_derived_claim_above_weakest_input_raises(self):
        weak = Claim(
            field="a",
            value=1,
            tier=Tier.ML_PREDICTION,
            confidence=0.5,
            method="model",
            evidence=(),
        )
        with pytest.raises(TierPromotionError):
            Claim(
                field="b",
                value=2,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="derive",
                evidence=(),
                derived_from=(weak,),
            )

    def test_derived_tier_ceiling_is_minimum_of_multiple_inputs(self):
        strong = make_observed(field="a")
        weak = Claim(
            field="b",
            value=1,
            tier=Tier.INFERRED_SIDE_CHANNEL,
            confidence=0.8,
            method="side-channel",
            evidence=(2,),
        )
        with pytest.raises(TierPromotionError):
            Claim(
                field="c",
                value=3,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="derive",
                evidence=(),
                derived_from=(strong, weak),
            )
        # but sitting at or below the weakest input is fine
        ok = Claim(
            field="c",
            value=3,
            tier=Tier.INFERRED_SIDE_CHANNEL,
            confidence=0.8,
            method="derive",
            evidence=(),
            derived_from=(strong, weak),
        )
        assert ok.tier is Tier.INFERRED_SIDE_CHANNEL


class TestCandidateSetEliminate:
    def _universe(self):
        ids = frozenset({"A", "B", "C", "D"})
        return CandidateSet(universe=ids, surviving=ids, eliminated_by=())

    def test_eliminate_removes_candidates(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A", "B"}, "framing arithmetic ruled out A, B")
        assert cs2.surviving == frozenset({"C", "D"})

    def test_eliminate_records_human_readable_derivation(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A"}, "gcd(g)=16 excludes counter-mode A")
        assert ("A", "gcd(g)=16 excludes counter-mode A") in cs2.eliminated_by

    def test_eliminate_does_not_resurrect_previously_eliminated(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A"}, "reason 1")
        cs3 = eliminate(cs2, {"B"}, "reason 2")
        assert cs3.surviving == frozenset({"C", "D"})
        assert len(cs3.eliminated_by) == 2

    def test_eliminate_returns_new_candidateset_not_mutating_original(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A"}, "reason")
        assert cs.surviving == frozenset({"A", "B", "C", "D"})
        assert cs2 is not cs


class TestRank:
    def _universe(self):
        ids = frozenset({"A", "B", "C"})
        return CandidateSet(universe=ids, surviving=frozenset({"A", "B"}), eliminated_by=())

    def test_rank_returns_a_list(self):
        cs = self._universe()
        result = rank(cs, {"A": 0.9, "B": 0.1})
        assert isinstance(result, list)

    def test_rank_drops_scores_outside_surviving(self):
        cs = self._universe()
        result = rank(cs, {"A": 0.9, "B": 0.1, "C": 0.99})
        assert {suite for suite, _ in result} == {"A", "B"}

    def test_rank_orders_descending_by_score(self):
        cs = self._universe()
        result = rank(cs, {"A": 0.1, "B": 0.9})
        assert result == [("B", 0.9), ("A", 0.1)]

    def test_rank_never_constructs_a_candidateset(self):
        source = inspect.getsource(rank)
        assert "CandidateSet(" not in source

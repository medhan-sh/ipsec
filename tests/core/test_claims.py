import pytest

from ipsec_analyzer.core.claims import Claim, Tier, TierPromotionError


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
        # Dataclass-level only: the *dataclass* is free to carry any float
        # confidence in [0, 1] at this tier (0.0 by convention everywhere
        # this project constructs one) — nothing in Claim.__post_init__
        # forces it to 0.0. The *serialized* form is a separate, stricter
        # rule (a tier with no value shouldn't carry a confidence number
        # either) enforced in cli.py's typed-to-dict conversion and
        # covered by tests/test_cli.py::TestNotObservableClaimsSerializeConfidenceAsNull.
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

import pytest

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.core.constants import (
    ADDITIONAL_KEY_EXCHANGE,
    PPK_IDENTITY_KEY,
    PPK_SUPPORT,
)
from ipsec_analyzer.inference.notify_posture import (
    DowngradeExposureReason,
    DowngradeProtectionState,
    assess_notify_posture,
    classify_downgrade_exposure_reason,
    classify_downgrade_protection_state,
)
from ipsec_analyzer.synth.synth_ike import synth_downgrade_prevention_posture, synth_ike_sa_init


def _assess_from_exchange(exchange, dh_groups=None):
    return assess_notify_posture(
        request_notify_types=exchange.request.notify_types,
        response_notify_types=exchange.response.notify_types,
        proposed_dh_groups=dh_groups if dh_groups is not None else exchange.request.dh_groups,
        request_frame=exchange.request.frame,
        response_frame=exchange.response.frame,
    )


class TestFourStateLattice:
    """Built entirely against synth_ike, per Phase 2's "testable entirely
    against synth_ike" / "consumes synth_ike output only" — the production
    module itself never imports synth (see notify_posture.py's module
    docstring for why), so these tests are the point where synth_ike's
    output actually gets unpacked into it.
    """

    def test_both_state_is_protected(self):
        exchange = synth_downgrade_prevention_posture("both")
        state = classify_downgrade_protection_state(
            request_notify_types=exchange.request.notify_types,
            response_notify_types=exchange.response.notify_types,
        )
        assert state is DowngradeProtectionState.PROTECTED

    def test_request_only_state_is_partial_responder_lacks(self):
        exchange = synth_downgrade_prevention_posture("request_only")
        state = classify_downgrade_protection_state(
            request_notify_types=exchange.request.notify_types,
            response_notify_types=exchange.response.notify_types,
        )
        assert state is DowngradeProtectionState.PARTIAL_RESPONDER_LACKS

    def test_response_only_state_is_partial_initiator_lacks_not_protected(self):
        exchange = synth_downgrade_prevention_posture("response_only")
        state = classify_downgrade_protection_state(
            request_notify_types=exchange.request.notify_types,
            response_notify_types=exchange.response.notify_types,
        )
        assert state is DowngradeProtectionState.PARTIAL_INITIATOR_LACKS
        assert state is not DowngradeProtectionState.PROTECTED

    def test_neither_state_is_none(self):
        exchange = synth_downgrade_prevention_posture("neither")
        state = classify_downgrade_protection_state(
            request_notify_types=exchange.request.notify_types,
            response_notify_types=exchange.response.notify_types,
        )
        assert state is DowngradeProtectionState.NONE

    def test_arguments_are_keyword_only(self):
        # Phase 2 review fix #3: positional args risk a silent
        # request/response swap at a future call site (e.g. Phase 4's
        # adapter) with no test able to catch it. Confirms that risk is
        # closed off at the language level, not just by convention.
        with pytest.raises(TypeError):
            classify_downgrade_protection_state((16447,), ())


class TestSeverityBranches:
    def test_hybrid_pq_present_is_high(self):
        reason = classify_downgrade_exposure_reason(
            request_notify_types=(ADDITIONAL_KEY_EXCHANGE,),
            response_notify_types=(),
            proposed_dh_groups=(14,),
        )
        assert reason is DowngradeExposureReason.HYBRID_PQ_EXPOSED
        assert reason.severity == "HIGH"

    def test_mixed_weak_and_strong_groups_is_high(self):
        reason = classify_downgrade_exposure_reason(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(2, 14),
        )
        assert reason is DowngradeExposureReason.MIXED_STRENGTH_GROUPS
        assert reason.severity == "HIGH"

    def test_weak_only_is_medium(self):
        reason = classify_downgrade_exposure_reason(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(1, 2, 5),
        )
        assert reason is DowngradeExposureReason.WEAK_GROUP_NEGOTIABLE
        assert reason.severity == "MEDIUM"

    def test_no_weak_group_is_info(self):
        reason = classify_downgrade_exposure_reason(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(14, 19, 31),
        )
        assert reason is DowngradeExposureReason.NO_WEAK_GROUP
        assert reason.severity == "INFO"

    def test_hybrid_pq_outranks_mixed_groups(self):
        # both conditions present — HIGH either way, but confirms the
        # priority order doesn't accidentally short-circuit incorrectly
        reason = classify_downgrade_exposure_reason(
            request_notify_types=(ADDITIONAL_KEY_EXCHANGE,),
            response_notify_types=(),
            proposed_dh_groups=(2, 14),
        )
        assert reason is DowngradeExposureReason.HYBRID_PQ_EXPOSED


class TestAssessNotifyPosture:
    def test_all_claims_are_observed_confidence_1_with_evidence(self):
        exchange = synth_ike_sa_init(request_frame=3, response_frame=4)
        claims = _assess_from_exchange(exchange, dh_groups=(14,))
        assert claims, "expected at least one claim"
        for claim in claims:
            assert claim.tier is Tier.OBSERVED
            assert claim.confidence == 1.0
            assert claim.evidence == (3, 4)

    def test_protected_exchange_has_no_severity_claim(self):
        exchange = synth_downgrade_prevention_posture("both", request_dh_groups=(14,))
        claims = _assess_from_exchange(exchange)
        fields = {c.field for c in claims}
        assert "ike_sa_init.downgrade_exposure_severity" not in fields

    def test_unprotected_exchange_has_a_severity_claim(self):
        exchange = synth_downgrade_prevention_posture("neither", request_dh_groups=(1, 14))
        claims = _assess_from_exchange(exchange)
        severity_claims = [c for c in claims if c.field == "ike_sa_init.downgrade_exposure_severity"]
        assert len(severity_claims) == 1
        # amendment after Phase 5's review: value is now {"severity", "reason"}
        # so rules can distinguish HIGH-because-mixed from HIGH-because-hybrid-PQ
        assert severity_claims[0].value == {"severity": "HIGH", "reason": "MIXED_STRENGTH_GROUPS"}

    def test_ppk_notify_detected(self):
        exchange = synth_ike_sa_init(request_notify_types=(PPK_SUPPORT, PPK_IDENTITY_KEY))
        claims = _assess_from_exchange(exchange, dh_groups=(14,))
        ppk_claim = next(c for c in claims if c.field == "ike_sa_init.ppk_in_use")
        assert ppk_claim.value is True

    def test_ppk_not_detected_when_absent(self):
        exchange = synth_ike_sa_init()
        claims = _assess_from_exchange(exchange, dh_groups=(14,))
        ppk_claim = next(c for c in claims if c.field == "ike_sa_init.ppk_in_use")
        assert ppk_claim.value is False

    def test_hybrid_pq_claim_reflects_severity_input(self):
        exchange = synth_ike_sa_init(request_notify_types=(ADDITIONAL_KEY_EXCHANGE,))
        claims = _assess_from_exchange(exchange, dh_groups=(14,))
        pq_claim = next(c for c in claims if c.field == "ike_sa_init.hybrid_pq_exposed")
        assert pq_claim.value is True

    def test_arguments_are_keyword_only(self):
        with pytest.raises(TypeError):
            assess_notify_posture((), (), (), 1, 2)


class TestPartialObservationIsACoverageGapNotAFinding:
    """Phase 2 review fix #1: a capture that starts mid-session or is
    truncated before IKE_SA_INIT means one or both halves were never
    observed. Reporting that as posture NONE (a confident "neither peer
    supports anti-downgrade" finding) would be exactly the kind of
    confident-wrong-conclusion-from-missing-data invariant 3 exists to
    rule out. These tests are the ones that would have failed against the
    pre-fix behavior — each mirrors a way a real mid-session or truncated
    capture would actually look to this module.
    """

    def test_missing_request_yields_not_observable_posture(self):
        claims = assess_notify_posture(
            request_notify_types=None,
            response_notify_types=(),
            proposed_dh_groups=(14,),
            request_frame=None,
            response_frame=7,
        )
        posture = next(c for c in claims if c.field == "ike_sa_init.downgrade_protection_state")
        assert posture.tier is Tier.NOT_OBSERVABLE
        assert posture.value is None
        assert posture.evidence == (7,)

    def test_missing_response_yields_not_observable_posture(self):
        claims = assess_notify_posture(
            request_notify_types=(),
            response_notify_types=None,
            proposed_dh_groups=(14,),
            request_frame=3,
            response_frame=None,
        )
        posture = next(c for c in claims if c.field == "ike_sa_init.downgrade_protection_state")
        assert posture.tier is Tier.NOT_OBSERVABLE
        assert posture.value is None

    def test_missing_half_never_reports_none_or_a_severity(self):
        claims = assess_notify_posture(
            request_notify_types=None,
            response_notify_types=(),
            proposed_dh_groups=(1, 14),  # would be a mixed-groups HIGH if evaluated
            request_frame=None,
            response_frame=7,
        )
        posture = next(c for c in claims if c.field == "ike_sa_init.downgrade_protection_state")
        assert posture.value != DowngradeProtectionState.NONE.value
        fields = {c.field for c in claims}
        assert "ike_sa_init.downgrade_exposure_severity" not in fields

    def test_both_missing_still_abstains_cleanly(self):
        claims = assess_notify_posture(
            request_notify_types=None,
            response_notify_types=None,
            proposed_dh_groups=(),
            request_frame=None,
            response_frame=None,
        )
        posture = next(c for c in claims if c.field == "ike_sa_init.downgrade_protection_state")
        assert posture.tier is Tier.NOT_OBSERVABLE
        assert posture.evidence == ()

    def test_positive_hybrid_pq_from_the_observed_half_still_reported(self):
        # Presence found in the one half we DID see is decisive regardless
        # of what else was missed.
        claims = assess_notify_posture(
            request_notify_types=(ADDITIONAL_KEY_EXCHANGE,),
            response_notify_types=None,
            proposed_dh_groups=(14,),
            request_frame=3,
            response_frame=None,
        )
        pq_claim = next(c for c in claims if c.field == "ike_sa_init.hybrid_pq_exposed")
        assert pq_claim.tier is Tier.OBSERVED
        assert pq_claim.confidence == 1.0
        assert pq_claim.value is True

    def test_negative_hybrid_pq_with_missing_half_is_not_observable(self):
        # Absent from what we saw, but we didn't see everything — can't
        # confirm absence.
        claims = assess_notify_posture(
            request_notify_types=(),
            response_notify_types=None,
            proposed_dh_groups=(14,),
            request_frame=3,
            response_frame=None,
        )
        pq_claim = next(c for c in claims if c.field == "ike_sa_init.hybrid_pq_exposed")
        assert pq_claim.tier is Tier.NOT_OBSERVABLE
        assert pq_claim.value is None

    def test_negative_ppk_with_missing_half_is_not_observable(self):
        claims = assess_notify_posture(
            request_notify_types=(),
            response_notify_types=None,
            proposed_dh_groups=(14,),
            request_frame=3,
            response_frame=None,
        )
        ppk_claim = next(c for c in claims if c.field == "ike_sa_init.ppk_in_use")
        assert ppk_claim.tier is Tier.NOT_OBSERVABLE
        assert ppk_claim.value is None

    def test_both_halves_observed_and_empty_still_yields_a_real_none_result(self):
        # Phase 5a review fix #1: `[]` (observed, no notifies) must never
        # collapse into the same thing as `None` (not observed at all).
        # This is the case that actually exercises the NONE-protection
        # branch through assess_notify_posture end-to-end — the other
        # tests here only exercise it via classify_downgrade_protection_state
        # directly against synth_ike fixtures.
        claims = assess_notify_posture(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(14,),
            request_frame=3,
            response_frame=4,
        )
        posture = next(c for c in claims if c.field == "ike_sa_init.downgrade_protection_state")
        assert posture.tier is Tier.OBSERVED
        assert posture.value == DowngradeProtectionState.NONE.value
        severity = next(c for c in claims if c.field == "ike_sa_init.downgrade_exposure_severity")
        assert severity.value == {"severity": "INFO", "reason": "NO_WEAK_GROUP"}

    def test_fully_observed_negative_is_still_a_confident_false(self):
        # Regression guard: the fix must not weaken the fully-observed case.
        exchange = synth_ike_sa_init()
        claims = _assess_from_exchange(exchange, dh_groups=(14,))
        ppk_claim = next(c for c in claims if c.field == "ike_sa_init.ppk_in_use")
        pq_claim = next(c for c in claims if c.field == "ike_sa_init.hybrid_pq_exposed")
        assert ppk_claim.tier is Tier.OBSERVED and ppk_claim.value is False
        assert pq_claim.tier is Tier.OBSERVED and pq_claim.value is False


class TestUnknownStateGuard:
    def test_classify_downgrade_protection_state_never_raises_on_valid_input(self):
        # sanity: all four boolean combinations are handled, no fifth branch
        for req_has, resp_has in [(True, True), (True, False), (False, True), (False, False)]:
            req = (16447,) if req_has else ()
            resp = (16447,) if resp_has else ()
            classify_downgrade_protection_state(request_notify_types=req, response_notify_types=resp)

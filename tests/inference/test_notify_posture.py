import pytest

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.core.constants import (
    ADDITIONAL_KEY_EXCHANGE,
    PPK_IDENTITY_KEY,
    PPK_SUPPORT,
)
from ipsec_analyzer.inference.notify_posture import (
    DowngradeExposureSeverity,
    DowngradeProtectionState,
    assess_notify_posture,
    classify_downgrade_exposure_severity,
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
            exchange.request.notify_types, exchange.response.notify_types
        )
        assert state is DowngradeProtectionState.PROTECTED

    def test_request_only_state_is_partial_responder_lacks(self):
        exchange = synth_downgrade_prevention_posture("request_only")
        state = classify_downgrade_protection_state(
            exchange.request.notify_types, exchange.response.notify_types
        )
        assert state is DowngradeProtectionState.PARTIAL_RESPONDER_LACKS

    def test_response_only_state_is_partial_initiator_lacks_not_protected(self):
        exchange = synth_downgrade_prevention_posture("response_only")
        state = classify_downgrade_protection_state(
            exchange.request.notify_types, exchange.response.notify_types
        )
        assert state is DowngradeProtectionState.PARTIAL_INITIATOR_LACKS
        assert state is not DowngradeProtectionState.PROTECTED

    def test_neither_state_is_none(self):
        exchange = synth_downgrade_prevention_posture("neither")
        state = classify_downgrade_protection_state(
            exchange.request.notify_types, exchange.response.notify_types
        )
        assert state is DowngradeProtectionState.NONE


class TestSeverityBranches:
    def test_hybrid_pq_present_is_high(self):
        severity = classify_downgrade_exposure_severity(
            request_notify_types=(ADDITIONAL_KEY_EXCHANGE,),
            response_notify_types=(),
            proposed_dh_groups=(14,),
        )
        assert severity is DowngradeExposureSeverity.HIGH

    def test_mixed_weak_and_strong_groups_is_high(self):
        severity = classify_downgrade_exposure_severity(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(2, 14),
        )
        assert severity is DowngradeExposureSeverity.HIGH

    def test_weak_only_is_medium(self):
        severity = classify_downgrade_exposure_severity(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(1, 2, 5),
        )
        assert severity is DowngradeExposureSeverity.MEDIUM

    def test_no_weak_group_is_info(self):
        severity = classify_downgrade_exposure_severity(
            request_notify_types=(),
            response_notify_types=(),
            proposed_dh_groups=(14, 19, 31),
        )
        assert severity is DowngradeExposureSeverity.INFO

    def test_hybrid_pq_outranks_mixed_groups(self):
        # both conditions present — HIGH either way, but confirms the
        # priority order doesn't accidentally short-circuit incorrectly
        severity = classify_downgrade_exposure_severity(
            request_notify_types=(ADDITIONAL_KEY_EXCHANGE,),
            response_notify_types=(),
            proposed_dh_groups=(2, 14),
        )
        assert severity is DowngradeExposureSeverity.HIGH


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
        assert severity_claims[0].value == "HIGH"  # mixed weak+strong

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


class TestUnknownStateGuard:
    def test_classify_downgrade_protection_state_never_raises_on_valid_input(self):
        # sanity: all four boolean combinations are handled, no fifth branch
        for req_has, resp_has in [(True, True), (True, False), (False, True), (False, False)]:
            req = (16447,) if req_has else ()
            resp = (16447,) if resp_has else ()
            classify_downgrade_protection_state(req, resp)  # must not raise

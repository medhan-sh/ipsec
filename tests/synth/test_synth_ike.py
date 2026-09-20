import pytest

from ipsec_analyzer.core.constants import IKE_SA_INIT_FULL_TRANSCRIPT_AUTH
from ipsec_analyzer.synth.synth_ike import synth_downgrade_prevention_posture, synth_ike_sa_init


class TestSynthIkeSaInit:
    def test_default_roles_and_frames(self):
        exchange = synth_ike_sa_init()
        assert exchange.request.role == "initiator"
        assert exchange.response.role == "responder"
        assert exchange.request.frame == 1
        assert exchange.response.frame == 2

    def test_dh_groups_pass_through(self):
        exchange = synth_ike_sa_init(request_dh_groups=(1, 2, 14), response_dh_groups=(14,))
        assert exchange.request.dh_groups == (1, 2, 14)
        assert exchange.response.dh_groups == (14,)

    def test_transforms_pass_through(self):
        exchange = synth_ike_sa_init(
            request_transforms=(("ENCR", 20), ("PRF", 5)),
            response_transforms=(("ENCR", 20),),
        )
        assert exchange.request.transforms == (("ENCR", 20), ("PRF", 5))
        assert exchange.response.transforms == (("ENCR", 20),)

    def test_notify_types_pass_through(self):
        exchange = synth_ike_sa_init(request_notify_types=(16441, 16445))
        assert exchange.request.notify_types == (16441, 16445)
        assert exchange.response.notify_types == ()


class TestNotifyPostureStates:
    """Uses IKE_SA_INIT_FULL_TRANSCRIPT_AUTH from core.constants (not
    synth_ike's re-export) to prove synth_ike is actually reading the
    shared constant rather than a stale local copy — the exact duplication
    the Phase 1 review flagged.
    """

    def test_both_state_has_notify_in_request_and_response(self):
        exchange = synth_downgrade_prevention_posture("both")
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH in exchange.request.notify_types
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH in exchange.response.notify_types

    def test_request_only_state(self):
        exchange = synth_downgrade_prevention_posture("request_only")
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH in exchange.request.notify_types
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH not in exchange.response.notify_types

    def test_response_only_state(self):
        exchange = synth_downgrade_prevention_posture("response_only")
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH not in exchange.request.notify_types
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH in exchange.response.notify_types

    def test_neither_state(self):
        exchange = synth_downgrade_prevention_posture("neither")
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH not in exchange.request.notify_types
        assert IKE_SA_INIT_FULL_TRANSCRIPT_AUTH not in exchange.response.notify_types

    def test_unknown_state_raises(self):
        with pytest.raises(ValueError):
            synth_downgrade_prevention_posture("bogus")

    def test_kwargs_pass_through_to_underlying_builder(self):
        exchange = synth_downgrade_prevention_posture("both", request_dh_groups=(1, 22))
        assert exchange.request.dh_groups == (1, 22)

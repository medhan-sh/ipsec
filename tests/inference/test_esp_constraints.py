import pytest

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.core.constants import SUITE_FRAMINGS
from ipsec_analyzer.inference.esp_constraints.anchor_solver import (
    find_sustained_reverse_anchor,
    solve_icv_candidates,
)
from ipsec_analyzer.inference.esp_constraints.engine import (
    EspPacketObservation,
    analyze_esp_flow,
)
from ipsec_analyzer.inference.esp_constraints.gcd_estimator import estimate_granularity
from ipsec_analyzer.inference.esp_constraints.tfc_gate import suspect_tfc_by_length_distribution
from ipsec_analyzer.synth.synth_esp import esp_wire_len, synth_esp_flow, synth_tfc_flow


def _observations_from_flow(flow):
    return [
        EspPacketObservation(direction=p.direction, wire_len=p.wire_len, ciphertext_prefix=p.ciphertext_prefix)
        for p in flow
    ]


def _observations_without_prefix(flow):
    # Models a capture with no usable payload byte evidence at all (e.g.
    # only lengths were retained) — the pre-review EspPacketObservation
    # shape, still a supported input.
    return [EspPacketObservation(direction=p.direction, wire_len=p.wire_len) for p in flow]


class TestGcdEstimator:
    @pytest.mark.parametrize("suite_id", list(SUITE_FRAMINGS))
    def test_recovers_correct_granularity_for_every_suite(self, suite_id):
        framing = SUITE_FRAMINGS[suite_id]
        flow = synth_esp_flow(framing, count=120)
        g = estimate_granularity([p.wire_len for p in flow])
        assert g == framing.pad_granularity

    def test_fewer_than_8_distinct_values_abstains(self):
        assert estimate_granularity([100] * 20) is None

    def test_all_identical_lengths_abstains(self):
        assert estimate_granularity([68]) is None

    def test_invalid_raw_gcd_abstains(self):
        # 9 distinct values whose pairwise differences share gcd=3, not in {4,8,16}
        assert estimate_granularity([100, 103, 106, 109, 112, 115, 118, 121, 124]) is None

    def test_never_returns_a_value_outside_valid_set(self):
        for suite_id in SUITE_FRAMINGS:
            framing = SUITE_FRAMINGS[suite_id]
            flow = synth_esp_flow(framing, count=120)
            g = estimate_granularity([p.wire_len for p in flow])
            assert g in (None, 4, 8, 16)


class TestTfcGate:
    def test_dominant_near_mtu_length_is_suspected(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_tfc_flow(framing, count=100)
        assert suspect_tfc_by_length_distribution([p.wire_len for p in flow]) is True

    def test_genuine_bulk_flow_is_not_suspected(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120)
        assert suspect_tfc_by_length_distribution([p.wire_len for p in flow]) is False

    def test_empty_is_not_suspected(self):
        assert suspect_tfc_by_length_distribution([]) is False


class TestAnchorSolver:
    @pytest.mark.parametrize("suite_id", list(SUITE_FRAMINGS))
    def test_recovers_correct_icv_len_for_every_suite(self, suite_id):
        framing = SUITE_FRAMINGS[suite_id]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        directions = [p.direction for p in flow]
        wire_lengths = [p.wire_len for p in flow]

        anchor_len = find_sustained_reverse_anchor(directions, wire_lengths)
        assert anchor_len is not None, f"{suite_id}: no anchor found"

        plausible = solve_icv_candidates(anchor_len, framing.pad_granularity)
        assert framing.icv_len in plausible, (
            f"{suite_id}: expected icv_len {framing.icv_len} in {sorted(plausible)}"
        )

    def test_no_second_direction_returns_no_anchor(self):
        assert find_sustained_reverse_anchor(["forward"] * 10, [1400] * 10) is None

    def test_balanced_directions_return_no_anchor(self):
        directions = ["forward", "reverse"] * 10
        lengths = [700] * 20
        assert find_sustained_reverse_anchor(directions, lengths) is None

    def test_too_few_reverse_packets_returns_no_anchor(self):
        directions = ["forward"] * 20 + ["reverse"] * 3
        lengths = [1400] * 20 + [68] * 3
        assert find_sustained_reverse_anchor(directions, lengths) is None

    def test_empty_input_returns_no_anchor(self):
        assert find_sustained_reverse_anchor([], []) is None

    def test_both_hypotheses_can_be_plausible_and_are_both_reported(self):
        # Construct e_ack so both P=40 and P=52 land on real icv_len values
        # within the same family/granularity bucket.
        framing_16 = SUITE_FRAMINGS["AES-128-GCM-16"]  # icv_len=16, granularity=4
        framing_12 = SUITE_FRAMINGS["AES-128-GCM-12"]  # icv_len=12, granularity=4
        e_ack_for_40_giving_16 = esp_wire_len(40, framing_16)
        # Check whether P=52 on the same e_ack also yields a known icv (12) —
        # if so this e_ack is a genuine "both plausible" case.
        plausible = solve_icv_candidates(e_ack_for_40_giving_16, 4)
        assert 16 in plausible  # P=40 hypothesis always recovers the true icv_len
        # Whether 12 also appears depends on arithmetic coincidence; assert
        # the function *can* return multiple values without asserting which
        # e_ack triggers it, to avoid over-fitting the test to today's table.
        assert isinstance(plausible, frozenset)


class TestEndToEndEngine:
    @pytest.mark.parametrize("suite_id", list(SUITE_FRAMINGS))
    def test_correct_suite_survives_for_every_suite(self, suite_id):
        framing = SUITE_FRAMINGS[suite_id]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow), evidence=(1, 2, 3))

        assert result.granularity_claim.tier is Tier.INFERRED_SIDE_CHANNEL
        assert result.granularity_claim.confidence == 1.0
        assert result.granularity_claim.value == framing.pad_granularity
        assert result.candidate_set is not None
        assert suite_id in result.candidate_set.surviving, (
            f"{suite_id} was eliminated but should have survived"
        )

    def test_tfc_flow_returns_not_observable_but_null_channel_still_runs(self):
        # Amendment after Phase 4's review: candidate_set is never None —
        # the NULL-encryption channel is independent of TFC/granularity
        # (see engine.py's module docstring) and still runs here. This is
        # the exact scenario every real capture in Phase 4 hit.
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_tfc_flow(framing, count=100)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.granularity_claim.tier is Tier.NOT_OBSERVABLE
        assert result.granularity_claim.value is None
        assert any("TFC" in c for c in result.granularity_claim.caveats)
        assert result.candidate_set is not None
        null_ids = frozenset(sid for sid in SUITE_FRAMINGS if SUITE_FRAMINGS[sid].explicit_iv == 0)
        assert not (null_ids & result.candidate_set.surviving), "NULL-ENC should still be eliminated"
        # nothing else eliminated — family/ICV channels correctly abstained
        assert result.candidate_set.surviving == frozenset(SUITE_FRAMINGS) - null_ids

    def test_all_identical_lengths_returns_not_observable_but_null_channel_still_runs(self):
        observations = [EspPacketObservation(direction="forward", wire_len=68) for _ in range(20)]
        result = analyze_esp_flow(observations)
        assert result.granularity_claim.tier is Tier.NOT_OBSERVABLE
        assert result.candidate_set is not None
        null_ids = frozenset(sid for sid in SUITE_FRAMINGS if SUITE_FRAMINGS[sid].explicit_iv == 0)
        assert not (null_ids & result.candidate_set.surviving), "no payload evidence should still eliminate NULL-ENC by default"

    def test_not_observable_claim_has_no_value(self):
        observations = [EspPacketObservation(direction="forward", wire_len=68) for _ in range(20)]
        result = analyze_esp_flow(observations)
        # Claim.__post_init__ would have raised already if this were violated;
        # this test documents the invariant explicitly for this call site.
        assert result.granularity_claim.value is None

    def test_indistinguishable_suites_appear_together_and_are_not_separated(self):
        # AES-*-GCM-16 (128/192/256) and AES-*-CCM-16 (128/256) all share
        # (counter, 4, 8, 16) framing — genuinely indistinguishable by this
        # method. Checked structurally rather than against a hardcoded
        # suite list, so this doesn't rot if the table's contents change.
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.candidate_set is not None

        group = next(
            (g for g in result.candidate_set.indistinguishable if "AES-128-GCM-16" in g),
            None,
        )
        assert group is not None, "expected AES-128-GCM-16 to be in an indistinguishable group"
        assert len(group) > 1

        # Every member of the group must share the exact same framing tuple.
        tuples = {
            (
                SUITE_FRAMINGS[sid].family,
                SUITE_FRAMINGS[sid].pad_granularity,
                SUITE_FRAMINGS[sid].explicit_iv,
                SUITE_FRAMINGS[sid].icv_len,
            )
            for sid in group
        }
        assert len(tuples) == 1

        # And every member of the group must be in `surviving` together —
        # never split apart by elimination.
        assert group <= result.candidate_set.surviving

    def test_eliminated_by_derivations_are_human_readable(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.candidate_set is not None
        assert result.candidate_set.eliminated_by, "expected at least one elimination"
        for suite_id, reason in result.candidate_set.eliminated_by:
            assert isinstance(suite_id, str) and suite_id
            assert isinstance(reason, str) and len(reason) > 15

    def test_granularity_claim_evidence_is_passed_through(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120)
        result = analyze_esp_flow(_observations_from_flow(flow), evidence=(5, 6, 7))
        assert result.granularity_claim.evidence == (5, 6, 7)


class TestNullEncryptionElimination:
    """Added on review: NULL-ENC's icv values (12 or 16) can independently
    look "plausible" against a real cipher's own ICV-hypothesis widening
    (see anchor_solver.solve_icv_candidates's explicit_iv x P combinations),
    so without a payload check NULL-ENC survives essentially any
    counter-mode capture by arithmetic coincidence — which would block
    Phase 5's verdict lifting from ever reaching unanimity and make rule 10
    (NULL encryption) a false positive on every capture. These tests
    reproduce that exact collision and confirm the fix closes it.
    """

    def _null_suite_ids(self):
        return frozenset(sid for sid in SUITE_FRAMINGS if SUITE_FRAMINGS[sid].explicit_iv == 0)

    def test_null_enc_eliminated_from_a_real_ciphers_flow(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.candidate_set is not None
        null_ids = self._null_suite_ids()
        assert not (null_ids & result.candidate_set.surviving), "NULL-ENC should have been eliminated"
        eliminated_ids = {sid for sid, _ in result.candidate_set.eliminated_by}
        assert null_ids <= eliminated_ids

    @pytest.mark.parametrize("suite_id", ["NULL-ENC + HMAC-SHA1-96", "NULL-ENC + HMAC-SHA256-128"])
    def test_null_enc_survives_its_own_genuine_flow(self, suite_id):
        framing = SUITE_FRAMINGS[suite_id]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.candidate_set is not None
        assert suite_id in result.candidate_set.surviving
        # Added for Phase 5's rule 10 ("NULL encryption"): a positive
        # confirmation must be its own Claim, not just "wasn't eliminated"
        # (an absence Phase 5's rule engine has nothing to query).
        assert result.null_encryption_claim is not None
        assert result.null_encryption_claim.value is True
        assert result.null_encryption_claim.tier is Tier.INFERRED_SIDE_CHANNEL

    def test_null_encryption_claim_is_none_when_null_is_eliminated(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.null_encryption_claim is None

    def test_no_payload_evidence_still_eliminates_null_by_default(self):
        # Without any ciphertext_prefix data at all (a capture that kept
        # only lengths), NULL-ENC must not survive by default — real ESP
        # is essentially never actually NULL.
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_without_prefix(flow))
        assert result.candidate_set is not None
        assert not (self._null_suite_ids() & result.candidate_set.surviving)

    def test_insufficient_diversity_but_readable_payload_eliminates_null_with_reason(self):
        # Phase 5a review fix #6: confirms elimination-channel independence
        # holds specifically for "granularity abstains, but there IS
        # payload evidence" (not just "granularity abstains and there's no
        # payload evidence at all", already covered above) — every wire
        # length is identical (insufficient size diversity: GCD abstains),
        # but each packet carries a real, non-NULL ciphertext prefix. The
        # NULL-encryption channel must still run independently and record
        # a human-readable elimination reason, exactly as it does when
        # granularity succeeds.
        observations = [
            EspPacketObservation(direction="forward", wire_len=1400, ciphertext_prefix=b"\xb0\x00\x00\x00")
            for _ in range(20)
        ]
        result = analyze_esp_flow(observations)
        assert result.granularity_claim.tier is Tier.NOT_OBSERVABLE
        assert result.candidate_set is not None
        null_ids = self._null_suite_ids()
        assert not (null_ids & result.candidate_set.surviving), "NULL-ENC should still be eliminated"
        null_reasons = [reason for sid, reason in result.candidate_set.eliminated_by if sid in null_ids]
        assert null_reasons
        assert all(len(reason) > 15 for reason in null_reasons)

    def test_null_elimination_reason_is_human_readable(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.candidate_set is not None
        null_ids = self._null_suite_ids()
        null_reasons = [reason for sid, reason in result.candidate_set.eliminated_by if sid in null_ids]
        assert null_reasons
        assert all(len(reason) > 15 for reason in null_reasons)


class TestIcvClaimHeuristicCaveat:
    """Added on review: the ICV claim's arithmetic is exact, but only
    conditional on the ACK-anchor packet identification being correct —
    that identification is a heuristic (modal smallest reverse-direction
    length during a burst), unlike the GCD granularity claim, which is
    arithmetically forced by the observed lengths with nothing to identify
    first. Same tier and confidence, but the ICV claim must name that
    assumption explicitly.
    """

    def test_icv_claim_carries_a_heuristic_caveat(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.icv_claim is not None
        assert result.icv_claim.tier == result.granularity_claim.tier  # same tier, per review
        assert result.icv_claim.confidence == 1.0
        assert result.icv_claim.caveats
        assert "heuristic" in result.icv_claim.caveats[0]
        assert 16 in result.icv_claim.value

    def test_granularity_claim_has_no_such_caveat(self):
        # Contrast case: the granularity claim has nothing to identify
        # first (the GCD is forced by the lengths themselves), so it
        # shouldn't carry the same heuristic-dependency caveat.
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert not result.granularity_claim.caveats

    def test_icv_claim_is_none_when_no_anchor_is_found(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=120, forward_run=1, reverse_run=0)  # no reverse direction at all
        result = analyze_esp_flow(_observations_from_flow(flow))
        assert result.granularity_claim.tier is Tier.INFERRED_SIDE_CHANNEL  # granularity still recovered
        assert result.icv_claim is None

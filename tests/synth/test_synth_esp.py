import math
from itertools import combinations

import pytest

from core.constants import SUITE_FRAMINGS, SuiteFraming
from synth.synth_esp import SyntheticPacket, ciphertext_len, esp_wire_len, synth_esp_flow


class TestRoundTripCongruence:
    """Round-trip property over E itself — the only quantity Phase 3 ever
    observes on the wire. (An earlier version of this test checked
    ciphertext_len's ceiling property instead; that's a necessary but not
    sufficient stand-in for what Phase 3 actually consumes, flagged as an
    overclaim in reports/phase-1.md's addendum.)
    """

    @pytest.mark.parametrize("suite_id", list(SUITE_FRAMINGS))
    def test_congruence_holds_for_every_plaintext_length(self, suite_id):
        framing = SUITE_FRAMINGS[suite_id]
        for p in range(20, 1501):
            e = esp_wire_len(p, framing)
            ct_len = e - framing.explicit_iv - framing.icv_len
            assert ct_len % framing.pad_granularity == 0, (
                f"{suite_id}: ciphertext_len {ct_len} not aligned to {framing.pad_granularity} for P={p}"
            )
            assert ct_len >= p + 2, f"{suite_id}: ciphertext_len {ct_len} shorter than P+2 for P={p}"
            assert ct_len - (p + 2) < framing.pad_granularity, (
                f"{suite_id}: padding overshoot for P={p}"
            )


class TestWorkedCases:
    """The three generic worked cases from MVP_BUILD_PROMPT.md Phase 1, using
    icv_len=0 synthetic framings so the stated ciphertext_len/E values are
    checked directly (the doc's "+ icv" is the real suite's icv_len on top),
    plus named-suite checks for both families — counter (given in prose) and
    CBC (added on review: the two generic cases alone don't exercise a real
    CBC suite, and CBC's ceil-division is the branch most likely to be off
    by one).
    """

    def test_counter_b4_p40(self):
        framing = SuiteFraming("test-counter", "counter", explicit_iv=8, pad_granularity=4, icv_len=0, rfc="test")
        assert ciphertext_len(40, framing) == 44
        assert esp_wire_len(40, framing) == 52

    def test_cbc_b16_p40(self):
        framing = SuiteFraming("test-cbc16", "cbc", explicit_iv=16, pad_granularity=16, icv_len=0, rfc="test")
        assert ciphertext_len(40, framing) == 48
        assert esp_wire_len(40, framing) == 64

    def test_cbc_b8_p40(self):
        framing = SuiteFraming("test-cbc8", "cbc", explicit_iv=8, pad_granularity=8, icv_len=0, rfc="test")
        assert ciphertext_len(40, framing) == 48
        assert esp_wire_len(40, framing) == 56

    def test_aes128_gcm16_bare_ack_is_68(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        assert esp_wire_len(40, framing) == 68

    def test_aes128_gcm12_bare_ack_is_64(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-12"]
        assert esp_wire_len(40, framing) == 64

    def test_aes128_cbc_hmac_sha1_96_bare_ack_is_76(self):
        # 16 (explicit_iv) + ceil(42/16)*16=48 (ciphertext_len) + 12 (icv) = 76
        framing = SUITE_FRAMINGS["AES-128-CBC + HMAC-SHA1-96"]
        assert ciphertext_len(40, framing) == 48
        assert esp_wire_len(40, framing) == 76

    def test_3des_cbc_hmac_sha1_96_bare_ack_is_68(self):
        # 8 (explicit_iv) + ceil(42/8)*8=48 (ciphertext_len) + 12 (icv) = 68
        framing = SUITE_FRAMINGS["3DES-CBC + HMAC-SHA1-96"]
        assert ciphertext_len(40, framing) == 48
        assert esp_wire_len(40, framing) == 68


class TestCiphertextLenValidation:
    def test_negative_plaintext_len_rejected(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        with pytest.raises(ValueError):
            ciphertext_len(-1, framing)


class TestSynthEspFlow:
    def test_flow_has_requested_packet_count(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=27)
        assert len(flow) == 27
        assert all(isinstance(p, SyntheticPacket) for p in flow)

    def test_flow_wire_lens_match_oracle(self):
        framing = SUITE_FRAMINGS["AES-256-CBC + HMAC-SHA256-128"]
        flow = synth_esp_flow(framing, count=18)
        for packet in flow:
            assert packet.wire_len == esp_wire_len(packet.inner_len, framing)

    def test_flow_is_mostly_forward_with_sparse_reverse_acks(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=90, forward_run=8, reverse_run=1)
        forward = [p for p in flow if p.direction == "forward"]
        reverse = [p for p in flow if p.direction == "reverse"]
        assert len(forward) == 80
        assert len(reverse) == 10
        assert all(p.inner_len == 40 for p in reverse)
        assert all(40 <= p.inner_len <= 1400 for p in forward)

    def test_flow_is_deterministic(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow1 = synth_esp_flow(framing, count=40)
        flow2 = synth_esp_flow(framing, count=40)
        assert flow1 == flow2

    def test_forward_lengths_sweep_rather_than_repeat_one_value(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        flow = synth_esp_flow(framing, count=90, forward_run=8, reverse_run=1)
        forward_lengths = {p.inner_len for p in flow if p.direction == "forward"}
        assert len(forward_lengths) > 10, "forward lengths should span a genuine range, not cluster"

    def test_negative_count_rejected(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        with pytest.raises(ValueError):
            synth_esp_flow(framing, count=-1)

    def test_empty_forward_range_rejected(self):
        framing = SUITE_FRAMINGS["AES-128-GCM-16"]
        with pytest.raises(ValueError):
            synth_esp_flow(framing, count=10, forward_inner_range=(100, 50))


class TestGcdRecoverability:
    """This is the test Phase 3's core estimator actually depends on: it
    pre-validates, a phase early, that synth_esp_flow's output is dense
    enough for gcd-of-pairwise-differences to land exactly on
    pad_granularity rather than some larger multiple of it. Added on review
    after the original flow generator (narrow near-MTU cluster) was shown to
    fail this for every suite.
    """

    @pytest.mark.parametrize("suite_id", list(SUITE_FRAMINGS))
    def test_gcd_of_flow_recovers_pad_granularity(self, suite_id):
        framing = SUITE_FRAMINGS[suite_id]
        flow = synth_esp_flow(framing, count=120, forward_run=8, reverse_run=1)
        wire_lens = [p.wire_len for p in flow]
        diffs = [abs(a - b) for a, b in combinations(wire_lens, 2) if a != b]
        assert diffs, f"{suite_id}: flow produced no distinct E values at all"
        observed_gcd = math.gcd(*diffs)
        assert observed_gcd == framing.pad_granularity, (
            f"{suite_id}: gcd of E differences is {observed_gcd}, expected {framing.pad_granularity}"
        )

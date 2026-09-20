from pathlib import Path

import pytest

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.protocol.ike_parse import (
    EXCHANGE_TYPE_IKE_SA_INIT,
    IkeMessage,
    IkeTransforms,
    ParsedIke,
    TsharkError,
    extract_ike_sa_init_claims,
    extract_ikev1_detected_claim,
    get_tshark_version,
    notify_posture_inputs,
    parse_ike_messages,
    run_tshark_json,
)

CAPTURES = Path(__file__).resolve().parent.parent.parent / "captures"

# (filename, expected transform_id, expected key_length or None, expected dh_group)
# Ground truth is the filename itself — verified by hand against IANA's
# "Transform Type 1 - Encryption Algorithm Transform IDs" registry, see
# reports/phase-4.md.
WIRESHARK_VECTORS = [
    ("ikev2-decrypt-aes128ccm12.pcap", 15, 128, 19),   # ENCR_AES_CCM_12
    ("ikev2-decrypt-3des-sha1_160.pcap", 3, None, 14),  # ENCR_3DES
    ("ikev2-decrypt-aes192ctr.pcap", 13, 192, 19),      # ENCR_AES_CTR
    ("ikev2-decrypt-aes256cbc.pcapng", 12, 256, 19),    # ENCR_AES_CBC
    ("ikev2-decrypt-aes256gcm16.pcap", 20, 256, 19),    # ENCR_AES_GCM_16
    ("ikev2-decrypt-aes256gcm8.pcap", 18, 256, 19),     # ENCR_AES_GCM_8
]


class TestRunTsharkJson:
    def test_returns_frames_for_a_real_capture(self):
        result = run_tshark_json(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        assert len(result.frames) == 6
        assert result.exit_clean is True

    def test_returns_empty_list_for_no_isakmp_traffic(self):
        result = run_tshark_json(str(CAPTURES / "http.pcap"))
        assert result.frames == []
        assert result.exit_clean is True

    def test_nonexistent_file_raises_tsharkerror(self):
        with pytest.raises(TsharkError):
            run_tshark_json(str(CAPTURES / "does_not_exist.pcap"))

    def test_truncated_capture_returns_partial_frames_and_reports_dirty_exit(self):
        # The real finding from this phase's build: tshark exits non-zero
        # on a mid-packet truncation but still emits valid JSON for every
        # packet it read before the cut. This must not raise, and the
        # non-zero exit must be surfaced rather than discarded.
        result = run_tshark_json(str(CAPTURES / "ikev2-decrypt-aes256gcm16_truncated.pcap"))
        assert isinstance(result.frames, list)
        assert len(result.frames) <= 6
        assert result.exit_clean is False


class TestIkeSaInitExtraction:
    @pytest.mark.parametrize("filename,encr_id,key_length,dh_group", WIRESHARK_VECTORS)
    def test_encryption_and_dh_match_filename_ground_truth(self, filename, encr_id, key_length, dh_group):
        parsed = parse_ike_messages(str(CAPTURES / filename))
        claims = extract_ike_sa_init_claims(parsed)
        by_field = {c.field: c for c in claims}

        assert "ike_sa.encryption" in by_field
        encryption = by_field["ike_sa.encryption"]
        assert encryption.tier is Tier.OBSERVED
        assert encryption.confidence == 1.0
        assert encryption.value["transform_id"] == encr_id
        assert encryption.value["key_length"] == key_length

        assert "ike_sa.dh_group" in by_field
        assert by_field["ike_sa.dh_group"].value == dh_group

    @pytest.mark.parametrize("filename,_a,_b,_c", WIRESHARK_VECTORS)
    def test_prf_always_extracted(self, filename, _a, _b, _c):
        parsed = parse_ike_messages(str(CAPTURES / filename))
        claims = extract_ike_sa_init_claims(parsed)
        by_field = {c.field: c for c in claims}
        assert "ike_sa.prf" in by_field
        assert by_field["ike_sa.prf"].tier is Tier.OBSERVED

    def test_integrity_present_for_non_aead_cipher(self):
        # 3DES-CBC needs a separate integrity transform (not combined-mode)
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-3des-sha1_160.pcap"))
        claims = extract_ike_sa_init_claims(parsed)
        by_field = {c.field: c for c in claims}
        assert "ike_sa.integrity" in by_field

    def test_integrity_absent_for_aead_cipher(self):
        # AES-GCM is combined-mode: no separate integrity transform exists
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        claims = extract_ike_sa_init_claims(parsed)
        by_field = {c.field: c for c in claims}
        assert "ike_sa.integrity" not in by_field

    def test_all_claims_cite_the_response_frame_as_evidence(self):
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        claims = extract_ike_sa_init_claims(parsed)
        assert claims
        for claim in claims:
            assert claim.evidence == (2,)  # frame 2 is the IKE_SA_INIT response in this capture

    def test_no_ike_sa_init_yields_no_claims(self):
        parsed = parse_ike_messages(str(CAPTURES / "weberblog_ikev2_midsession.pcap"))
        assert extract_ike_sa_init_claims(parsed) == []

    def test_ikev1_capture_yields_no_ikev2_style_claims(self):
        # IKEv1 doesn't use IKEv2's exchange types at all — this is a
        # correct "different protocol version, nothing to extract" result,
        # not a coverage gap in the missing-data sense.
        parsed = parse_ike_messages(str(CAPTURES / "weberblog_ikev1.pcap"))
        assert extract_ike_sa_init_claims(parsed) == []

    def test_non_ipsec_capture_yields_no_claims_not_a_crash(self):
        parsed = parse_ike_messages(str(CAPTURES / "http.pcap"))
        assert extract_ike_sa_init_claims(parsed) == []


class TestNotifyPostureInputs:
    def test_fully_observed_exchange_returns_both_frames(self):
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        inputs = notify_posture_inputs(parsed)
        assert inputs is not None
        assert inputs["request_frame"] == 1
        assert inputs["response_frame"] == 2
        assert inputs["request_notify_types"] is not None
        assert inputs["response_notify_types"] is not None

    def test_no_ike_sa_init_returns_none(self):
        parsed = parse_ike_messages(str(CAPTURES / "weberblog_ikev2_midsession.pcap"))
        assert notify_posture_inputs(parsed) is None

    def test_no_public_capture_contains_the_downgrade_prevention_notify(self):
        # Per Phase 2's report: the downgrade-prevention draft is new
        # enough that no public capture is expected to contain notify
        # 16447 yet. Confirmed here against every real capture available.
        for filename, *_ in WIRESHARK_VECTORS:
            parsed = parse_ike_messages(str(CAPTURES / filename))
            inputs = notify_posture_inputs(parsed)
            assert inputs is not None
            all_types = set(inputs["request_notify_types"]) | set(inputs["response_notify_types"])
            assert 16447 not in all_types


class TestFragmentationAbstention:
    """MVP_BUILD_PROMPT.md Phase 4: 'If RFC 7383 fragmentation is present,
    record the fact and abstain. Do not implement reassembly.'

    No publicly available test capture in captures/ (see FETCH.md)
    contains IKE message fragmentation — it's an uncommon, mostly-large-
    payload-triggered feature — so this is verified against a
    hand-constructed IkeMessage fixture rather than real data. Honest gap,
    documented in reports/phase-4.md: the *detection* logic is tested,
    the *real-world tshark JSON shape* for a Fragment payload is not.
    """

    def test_fragmented_ike_sa_init_abstains_rather_than_extracting(self):
        parsed = ParsedIke(
            messages=[
                IkeMessage(frame_no=1, exchange_type=EXCHANGE_TYPE_IKE_SA_INIT, is_request=True, has_fragment=True),
                IkeMessage(
                    frame_no=2,
                    exchange_type=EXCHANGE_TYPE_IKE_SA_INIT,
                    is_request=False,
                    transforms=IkeTransforms(encr_id=20, encr_key_length=256, prf_id=5, dh_id=19),
                ),
            ],
            tshark_exit_clean=True,
        )
        claims = extract_ike_sa_init_claims(parsed)
        assert len(claims) == 1
        assert claims[0].tier is Tier.NOT_OBSERVABLE
        assert claims[0].value is None
        assert "fragmentation" in claims[0].caveats[0].lower()
        assert claims[0].evidence == (1,)

    def test_unfragmented_ike_sa_init_is_unaffected(self):
        parsed = ParsedIke(
            messages=[
                IkeMessage(frame_no=1, exchange_type=EXCHANGE_TYPE_IKE_SA_INIT, is_request=True),
                IkeMessage(
                    frame_no=2,
                    exchange_type=EXCHANGE_TYPE_IKE_SA_INIT,
                    is_request=False,
                    transforms=IkeTransforms(encr_id=20, encr_key_length=256, prf_id=5, dh_id=19),
                ),
            ],
            tshark_exit_clean=True,
        )
        claims = extract_ike_sa_init_claims(parsed)
        assert any(c.tier is Tier.OBSERVED for c in claims)


class TestWithinFrameTruncation:
    """Phase 4 review fix #3: a between-frames truncation (tshark exits
    non-zero, see TestRunTsharkJson) is not the only way a capture can be
    incomplete. A capture taken with a small snaplen — historically a
    common tcpdump default — captures every frame's header intact but
    cuts each frame's *payload* short; tshark still reports the frame
    (exit code stays clean) but its later payloads (here, the SA
    transforms) are silently absent from the dissection. Before this fix,
    that looked identical to "a response that legitimately has no SA
    payload", which cannot actually happen for a real IKE_SA_INIT
    response — so the old code would have silently extracted nothing and
    called it a normal empty result, and worse, could have reported a
    partial, wrong notify-posture finding if just the notify payloads
    (not the whole SA) had been the part cut off.

    `ikev2-decrypt-aes256gcm16_snaplen.pcap` (see FETCH.md) is
    `ikev2-decrypt-aes256gcm16.pcap` re-captured with `editcap -s 100` —
    every frame present, but truncated to 100 bytes each, well short of
    where the SA payload starts.
    """

    def test_snaplen_capture_has_clean_tshark_exit(self):
        # Unlike a between-frames cut, a snaplen-limited capture is a
        # structurally valid file — tshark reads it start to finish
        # without complaint. The incompleteness is real but invisible at
        # the exit-code level, which is exactly why per-frame
        # is_fully_captured tracking is necessary and exit_clean alone
        # would not have been enough.
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16_snaplen.pcap"))
        assert parsed.tshark_exit_clean is True

    def test_snaplen_response_frame_is_marked_not_fully_captured(self):
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16_snaplen.pcap"))
        init_messages = [m for m in parsed.messages if m.exchange_type == EXCHANGE_TYPE_IKE_SA_INIT]
        assert len(init_messages) == 2
        assert all(not m.is_fully_captured for m in init_messages)

    def test_snaplen_capture_yields_no_ike_sa_claims_not_a_partial_answer(self):
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16_snaplen.pcap"))
        assert extract_ike_sa_init_claims(parsed) == []

    def test_snaplen_capture_notify_posture_is_a_coverage_gap_not_a_finding(self):
        # The core of this fix: this must be None, never a confident NONE
        # downgrade-posture finding built from a request/response that
        # exists as a frame but was never fully captured.
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16_snaplen.pcap"))
        assert notify_posture_inputs(parsed) is None


class TestIkev1Detection:
    """Smaller item from Phase 4's review: 'IKEv1 should say something,
    not nothing.' extract_ike_sa_init_claims() correctly returns [] for
    an IKEv1 capture (the exchange types and SA structure genuinely
    differ), but that's indistinguishable on its own from a tool failure.
    This is the explicit signal.
    """

    def test_ikev1_capture_is_detected(self):
        parsed = parse_ike_messages(str(CAPTURES / "weberblog_ikev1.pcap"))
        claim = extract_ikev1_detected_claim(parsed)
        assert claim is not None
        assert claim.tier is Tier.OBSERVED
        assert claim.value == 1
        assert "IKEv1" in claim.caveats[0]
        assert claim.evidence

    def test_ikev2_capture_is_not_flagged(self):
        parsed = parse_ike_messages(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        assert extract_ikev1_detected_claim(parsed) is None

    def test_non_ipsec_capture_is_not_flagged(self):
        parsed = parse_ike_messages(str(CAPTURES / "http.pcap"))
        assert extract_ikev1_detected_claim(parsed) is None


class TestTsharkVersion:
    def test_returns_a_version_string(self):
        version = get_tshark_version()
        assert version
        assert version[0].isdigit()

    def test_matches_the_dockerfile_pinned_version(self):
        # The Dockerfile pins TSHARK_VERSION=4.4.18-0+deb13u1 — confirms
        # the running binary is actually that pin, not silently drifted.
        version = get_tshark_version()
        assert version.startswith("4.4.18")

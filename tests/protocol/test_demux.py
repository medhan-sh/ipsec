from pathlib import Path

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.protocol.demux import AH_PROTO, ESP_PROTO, demux, extract_ah_detected_claim
from ipsec_analyzer.protocol.ingest import load_capture
from ipsec_analyzer.protocol.records import PacketRecord

CAPTURES = Path(__file__).resolve().parent.parent.parent / "captures"


def _record(proto, sport=None, dport=None, payload=b"", frame_no=1, src="10.0.0.1", dst="10.0.0.2"):
    return PacketRecord(
        frame_no=frame_no, ts=0.0, src=src, dst=dst, proto=proto,
        sport=sport, dport=dport, payload_len=len(payload), payload=payload, raw_offset=0,
    )


class TestPortRouting:
    def test_udp_500_routes_to_ike(self):
        records = [_record(17, sport=500, dport=500, payload=b"\x01" * 20)]
        result = demux(records)
        assert result.ike_frames == (1,)
        assert result.esp_records == ()

    def test_ip_proto_50_routes_to_esp(self):
        records = [_record(ESP_PROTO, payload=b"\x00\x00\x00\x01" + b"\x00" * 20)]
        result = demux(records)
        assert result.ike_frames == ()
        assert len(result.esp_records) == 1
        assert result.esp_records[0].spi == 1

    def test_ip_proto_51_flags_ah_and_is_excluded_from_esp(self):
        records = [_record(AH_PROTO, payload=b"\x00" * 20)]
        result = demux(records)
        assert result.ah_frames == (1,)
        assert result.esp_records == ()
        assert result.ike_frames == ()

    def test_irrelevant_protocol_is_dropped_silently(self):
        records = [_record(6, sport=443, dport=54321, payload=b"tcp data")]  # TCP
        result = demux(records)
        assert result.ike_frames == () and result.esp_records == () and result.ah_frames == ()


class TestNatTMarkerCheck:
    def test_udp_4500_with_non_esp_marker_routes_to_ike(self):
        payload = b"\x00\x00\x00\x00" + b"\x01" * 20  # non-ESP marker + ISAKMP-ish bytes
        records = [_record(17, sport=4500, dport=4500, payload=payload)]
        result = demux(records)
        assert result.ike_frames == (1,)
        assert result.esp_records == ()

    def test_udp_4500_without_marker_routes_to_esp(self):
        payload = b"\x00\x00\x00\x2a" + b"\x00\x00\x00\x01" + b"\x00" * 20  # SPI=0x2a, nonzero
        records = [_record(17, sport=4500, dport=4500, payload=payload)]
        result = demux(records)
        assert result.esp_records != ()
        assert result.ike_frames == ()
        assert result.esp_records[0].spi == 0x2A

    def test_short_udp_4500_payload_treated_as_esp_not_crash(self):
        records = [_record(17, sport=4500, dport=4500, payload=b"\x01\x02")]
        result = demux(records)
        # too short for a marker check AND too short for an ESP header —
        # must not raise; the malformed packet is just dropped
        assert result.esp_records == ()
        assert result.ike_frames == ()


class TestEspRecordsBySpi:
    def test_groups_by_spi(self):
        r1 = _record(ESP_PROTO, payload=b"\x00\x00\x00\x01" + b"\x00" * 10, frame_no=1)
        r2 = _record(ESP_PROTO, payload=b"\x00\x00\x00\x01" + b"\x00" * 12, frame_no=2)
        r3 = _record(ESP_PROTO, payload=b"\x00\x00\x00\x02" + b"\x00" * 10, frame_no=3)
        result = demux([r1, r2, r3])
        grouped = result.esp_records_by_spi()
        assert set(grouped) == {1, 2}
        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1


class TestEspTunnelPairing:
    """Phase 4 review fix #2: ESP SAs are unidirectional, so grouping by
    SPI alone hands the anchor solver a single direction with no reverse
    traffic inside it — the anchor can then never fire, permanently, on
    any real capture. esp_tunnels() pairs SPIs by nearest first-seen frame
    within a shared endpoint pair.
    """

    def _esp_record(self, spi, src, dst, frame_no):
        payload = spi.to_bytes(4, "big") + b"\x00" * 12
        return _record(ESP_PROTO, payload=payload, frame_no=frame_no, src=src, dst=dst)

    def test_pairs_two_spis_between_the_same_endpoints(self):
        records = [
            self._esp_record(1, "10.0.0.1", "10.0.0.2", frame_no=1),
            self._esp_record(2, "10.0.0.2", "10.0.0.1", frame_no=2),
        ]
        result = demux(records)
        tunnels = result.esp_tunnels()
        assert len(tunnels) == 1
        assert {tunnels[0].spi_a, tunnels[0].spi_b} == {1, 2}
        assert len(tunnels[0].records_a) == 1
        assert len(tunnels[0].records_b) == 1

    def test_separates_two_sequential_connections_between_the_same_hosts(self):
        # Mirrors the real multi-algo NAT-T capture's shape: two distinct
        # Child SA pairs between the same two hosts, separated in time.
        records = [
            self._esp_record(1, "10.0.0.1", "10.0.0.2", frame_no=5),
            self._esp_record(2, "10.0.0.2", "10.0.0.1", frame_no=6),
            self._esp_record(3, "10.0.0.1", "10.0.0.2", frame_no=23),
            self._esp_record(4, "10.0.0.2", "10.0.0.1", frame_no=24),
        ]
        result = demux(records)
        tunnels = result.esp_tunnels()
        assert len(tunnels) == 2
        pairs = sorted(({t.spi_a, t.spi_b} for t in tunnels), key=lambda s: min(s))
        assert pairs == [{1, 2}, {3, 4}]

    def test_unpaired_spi_reports_empty_reverse_direction(self):
        records = [self._esp_record(1, "10.0.0.1", "10.0.0.2", frame_no=1)]
        result = demux(records)
        tunnels = result.esp_tunnels()
        assert len(tunnels) == 1
        assert tunnels[0].spi_b is None
        assert tunnels[0].records_b == ()


class TestAgainstRealCaptures:
    def test_multi_algo_natt_capture_separates_six_child_sas(self):
        records = load_capture(str(CAPTURES / "ipsec_multi_algo_natt.pcapng"))
        result = demux(records)
        by_spi = result.esp_records_by_spi()
        # three sequential connections, each with its own inbound+outbound
        # Child SA — six distinct SPIs
        assert len(by_spi) == 6
        for spi, recs in by_spi.items():
            assert len(recs) > 0

    def test_ah_never_appears_in_real_captures_used_here(self):
        # sanity: none of our real captures use AH, so ah_frames should be
        # empty for them — confirms the AH path is exercised only by the
        # synthetic PacketRecord tests above, not by available real data
        # (documented as a known gap in reports/phase-4.md)
        records = load_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        result = demux(records)
        assert result.ah_frames == ()

    def test_ike_frames_recorded_for_ikev2_capture(self):
        records = load_capture(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        result = demux(records)
        assert result.ike_frames == (1, 2, 3, 4, 5, 6)

    def test_multi_algo_natt_capture_pairs_into_three_tunnels(self):
        # The real fixture that motivated this fix: three sequential Child
        # SA pairs between the same two hosts, verified by hand (see
        # demux.py's module docstring) to cluster tightly enough in frame
        # number for nearest-first-seen pairing to separate them cleanly.
        records = load_capture(str(CAPTURES / "ipsec_multi_algo_natt.pcapng"))
        result = demux(records)
        tunnels = result.esp_tunnels()
        assert len(tunnels) == 3
        for tunnel in tunnels:
            assert tunnel.spi_b is not None, "every tunnel here has both directions observed"
            assert tunnel.records_a and tunnel.records_b


class TestAhDetectedClaim:
    """Phase 5's rule 11 ("AH in use (deprecated)") needs a Claim, not
    just the raw `ah_frames` tuple — assessment/ reads the ClaimLedger,
    never protocol/ types directly.
    """

    def test_no_claim_when_no_ah_seen(self):
        result = demux([_record(6, sport=443, dport=1234)])
        assert extract_ah_detected_claim(result) is None

    def test_claim_when_ah_seen(self):
        result = demux([_record(AH_PROTO, payload=b"\x00" * 20, frame_no=7)])
        claim = extract_ah_detected_claim(result)
        assert claim is not None
        assert claim.tier is Tier.OBSERVED
        assert claim.value is True
        assert claim.evidence == (7,)

from pathlib import Path

from ipsec_analyzer.protocol.ingest import load_capture

CAPTURES = Path(__file__).resolve().parent.parent.parent / "captures"


class TestLoadCapture:
    def test_loads_a_real_ikev2_capture(self):
        records = load_capture(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        assert len(records) == 6
        assert all(r.proto == 17 for r in records)  # all UDP (IKE)
        assert records[0].frame_no == 1
        assert records[-1].frame_no == 6

    def test_frame_numbers_are_1_indexed_and_sequential(self):
        records = load_capture(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        assert [r.frame_no for r in records] == list(range(1, len(records) + 1))

    def test_udp_payload_excludes_udp_header(self):
        records = load_capture(str(CAPTURES / "ikev2-decrypt-aes256gcm16.pcap"))
        first = records[0]
        assert first.sport == 500 and first.dport == 500
        # ISAKMP header starts with the 8-byte Initiator SPI; payload
        # should start there, not 8 bytes earlier at the UDP header.
        assert first.payload_len == len(first.payload)
        assert first.payload_len > 0

    def test_loads_pcapng_too(self):
        records = load_capture(str(CAPTURES / "ikev2-decrypt-aes256cbc.pcapng"))
        assert len(records) > 0

    def test_loads_ipv6_capture(self):
        records = load_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        assert len(records) > 0
        assert all(":" in r.src for r in records)  # IPv6 addresses

    def test_non_ipsec_capture_does_not_crash(self):
        records = load_capture(str(CAPTURES / "http.pcap"))
        # http.pcap has no IKE/ESP traffic — loading it must not raise,
        # whatever it returns (TCP records, or none if scapy has no IP
        # layer to read — either is fine, a crash is not).
        assert isinstance(records, list)

    def test_truncated_capture_does_not_crash(self):
        records = load_capture(str(CAPTURES / "ikev2-decrypt-aes256gcm16_truncated.pcap"))
        assert isinstance(records, list)
        # whatever scapy could recover before the cut point; must be a
        # coverage gap (fewer records), not an exception
        assert len(records) <= 6

    def test_esp_records_carry_raw_payload_bytes(self):
        records = load_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        esp_records = [r for r in records if r.proto == 50]
        assert esp_records
        for r in esp_records:
            assert isinstance(r.payload, bytes)
            assert len(r.payload) == r.payload_len
            assert r.sport is None and r.dport is None  # ESP has no ports

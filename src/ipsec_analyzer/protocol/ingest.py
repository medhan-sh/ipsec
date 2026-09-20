"""ingest.py — pcap/pcapng → PacketRecord[] (MVP_BUILD_PROMPT.md Phase 4).

Uses scapy (approved in MVP_BUILD_PROMPT.md §3) to read the whole capture
into memory in one shot — no streaming, no bounded-memory work, per
CLAUDE.md's constraints; this is a single-run CLI tool, not a service.
scapy handles both classic pcap and pcapng natively.

Per-packet failures (a corrupt or truncated packet scapy can partially
parse but not fully) are skipped rather than raised — an explicit Phase 4
acceptance criterion is that a truncated capture produces coverage gaps,
not a crash, and one bad packet must not take down the whole load.
"""

from __future__ import annotations

from scapy.layers.inet import IP, UDP
from scapy.layers.inet6 import IPv6
from scapy.utils import rdpcap

from ipsec_analyzer.protocol.records import PacketRecord


def load_capture(path: str) -> list[PacketRecord]:
    """Reads every IP-layer (v4 or v6) packet in the capture. Non-IP
    packets (ARP, etc.) are silently skipped — this tool has nothing to
    say about them. Frame numbers are 1-indexed and always assigned from
    the original packet order, even for packets later skipped for parse
    failures, so `frame_no` always matches what a human would see in
    Wireshark for the same file.
    """
    records, _skipped = load_capture_with_skip_count(path)
    return records


def load_capture_with_skip_count(path: str) -> tuple[list[PacketRecord], int]:
    """Same as `load_capture`, plus how many packets were not turned into
    a `PacketRecord` (not IP at all, or malformed past readability) — a
    coverage fact (see `protocol/coverage.py`) nothing downstream can
    recompute once only the surviving records are handed onward.
    """
    packets = rdpcap(path)
    records: list[PacketRecord] = []
    skipped = 0
    offset = 0
    for frame_no, pkt in enumerate(packets, start=1):
        pkt_len = len(bytes(pkt))
        record = _to_packet_record(pkt, frame_no, offset)
        if record is not None:
            records.append(record)
        else:
            skipped += 1
        offset += pkt_len
    return records, skipped


def _to_packet_record(pkt, frame_no: int, offset: int) -> PacketRecord | None:
    if pkt.haslayer(IP):
        ip_layer = pkt[IP]
        proto = int(ip_layer.proto)
    elif pkt.haslayer(IPv6):
        ip_layer = pkt[IPv6]
        proto = int(ip_layer.nh)
    else:
        return None  # not an IP packet at all — irrelevant to this tool

    try:
        src = str(ip_layer.src)
        dst = str(ip_layer.dst)
        ts = float(pkt.time)
        payload = bytes(ip_layer.payload)
    except Exception:
        return None  # malformed enough that even basic fields aren't readable

    sport: int | None = None
    dport: int | None = None
    if proto == 17 and pkt.haslayer(UDP):
        try:
            udp_layer = pkt[UDP]
            sport = int(udp_layer.sport)
            dport = int(udp_layer.dport)
            payload = bytes(udp_layer.payload)  # re-slice past the UDP header too
        except Exception:
            pass  # keep the IP-layer payload as a fallback rather than dropping the packet

    return PacketRecord(
        frame_no=frame_no,
        ts=ts,
        src=src,
        dst=dst,
        proto=proto,
        sport=sport,
        dport=dport,
        payload_len=len(payload),
        payload=payload,
        raw_offset=offset,
    )

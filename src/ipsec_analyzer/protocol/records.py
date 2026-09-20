"""records.py — the shape every parsed packet takes (MVP_BUILD_PROMPT.md
Phase 4; ARCHITECTURE.md §5, "Protocol → Inference" contract).

`PacketRecord` is deliberately dumb: it carries what scapy can read off an
IP-layer packet without decoding any higher protocol. `ingest.py` builds
these; `demux.py` routes them; nothing here parses IKE or ESP internals —
that's `ike_parse.py` (via tshark) and `inference/esp_constraints/`
(via size arithmetic) respectively.

Amendment on ARCHITECTURE.md's sketch: that document lists `payload_len`
but not raw payload bytes. This adds a `payload` field carrying the actual
bytes after the IP header (or after the UDP header too, for UDP) —
`protocol/` isn't a frozen contract, and this is needed for real reasons
that postdate ARCHITECTURE.md: the NAT-T non-ESP-marker check in
`demux.py` needs to inspect the first bytes of a UDP/4500 payload, and
Phase 3's NULL-encryption check (added on review, see reports/phase-3.md)
needs a few real ciphertext-offset bytes from real ESP packets, not just
their length.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PacketRecord:
    frame_no: int            # 1-indexed, matches Wireshark
    ts: float                # epoch seconds
    src: str                 # IP, family-agnostic string (v4 or v6)
    dst: str
    proto: int                # IP protocol / IPv6 next-header number
    sport: int | None         # UDP source port; None for non-UDP
    dport: int | None         # UDP destination port; None for non-UDP
    payload_len: int          # len(payload) — transport payload, UDP header already subtracted
    payload: bytes            # the actual bytes (UDP payload, or IP payload for ESP/AH/other)
    raw_offset: int           # cumulative byte offset into the capture, for debugging/evidence

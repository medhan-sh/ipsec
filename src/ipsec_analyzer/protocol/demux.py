"""demux.py — route by port / IP proto (MVP_BUILD_PROMPT.md Phase 4).

UDP/500 -> IKE. UDP/4500 -> non-ESP marker check -> IKE or
UDP-encapsulated ESP. IP proto 50 -> ESP. IP proto 51 -> flag AH
deprecated and stop (recorded, not analyzed further — deep AH analysis is
explicitly out of scope). Everything else (TCP, ICMP, ...) is irrelevant
to this tool and silently dropped.

`ike_frames` is bookkeeping only: the actual IKE parsing (`ike_parse.py`)
hands tshark the *original* capture file directly, so tshark's own
dissector — not this module — resolves NAT-T encapsulation for IKE. This
module's own non-ESP-marker check exists only to decide which UDP/4500
packets belong to the *ESP* side, where this project's own size-based
analysis (not tshark) does the work.

ESP records are grouped by SPI (the first 4 bytes of the ESP header,
identifying which Child SA a packet belongs to) because a real capture
routinely contains more than one Child SA — e.g. a rekey, or multiple
tunnels — and mixing two SAs' packet sizes together would corrupt the
size-based analysis in inference/esp_constraints/ far worse than having
no data at all. Splitting by SPI isn't a nice-to-have here; without it,
"the ESP constraint engine runs on real ESP flows" cannot be satisfied on
a multi-SA capture at all.

**Amendment after Phase 4's review.** ESP SAs are unidirectional — a
tunnel is a *pair* of SPIs, one per direction. Grouping by SPI alone (as
this module originally did) hands `esp_constraints.engine` a single
direction's packets with no reverse direction inside it at all, so the
ACK-anchor solver (which specifically looks for a reverse-direction
trickle during a forward-direction burst) can never fire — permanently,
on every real capture, regardless of packet-size diversity. That was
masked in this phase's own tests because every real capture also hit the
granularity abstention first, for an unrelated reason (see
reports/phase-4.md's addendum for the full account of both).

`esp_tunnels()` pairs SPIs into (likely) tunnels: SPIs sharing an
unordered pair of endpoints are grouped, then paired by *nearest first-
seen frame number* — the two directions of one Child SA are negotiated
together and start being used at essentially the same time, so their
first packets cluster tightly, distinctly from any earlier or later
SA sharing the same two endpoints (verified by hand against the real
NAT-T multi-algorithm capture: three sequential connections between the
same two hosts produce three cleanly-separated pairs this way — see
`tests/protocol/test_demux.py::TestEspTunnelPairing`). This is a
heuristic, not a protocol guarantee: it assumes SA pairs don't overlap
in time with other SA pairs between the same two hosts. That's true for
every real capture available to this project, and is documented as a
known limitation rather than silently assumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ipsec_analyzer.core.claims import Claim, Tier
from ipsec_analyzer.protocol.records import PacketRecord

IKE_PORT = 500
NAT_T_PORT = 4500
ESP_PROTO = 50
AH_PROTO = 51

_MIN_ESP_HEADER_LEN = 8  # SPI (4) + Sequence Number (4), RFC 4303 §2


@dataclass(frozen=True)
class EspRecord:
    frame_no: int
    src: str
    dst: str
    spi: int      # identifies which Child SA this packet belongs to
    payload: bytes  # ESP payload starting at the SPI field; NAT-T UDP wrapper (if any) already stripped


@dataclass(frozen=True)
class EspTunnel:
    """One Child SA's two directions, paired by temporal proximity within
    a shared pair of endpoints (see the module docstring for why this is
    a heuristic, not a protocol guarantee). `spi_b`/`records_b` are empty
    when the reverse direction was never observed at all — a real,
    reportable coverage gap, not an error.
    """
    spi_a: int
    spi_b: int | None
    records_a: tuple[EspRecord, ...]
    records_b: tuple[EspRecord, ...]


@dataclass(frozen=True)
class DemuxResult:
    ike_frames: tuple[int, ...]
    esp_records: tuple[EspRecord, ...]
    ah_frames: tuple[int, ...]

    def esp_records_by_spi(self) -> dict[int, tuple[EspRecord, ...]]:
        """Single-direction grouping. Prefer `esp_tunnels()` for anything
        that needs both directions (e.g. the ACK anchor) — this exists for
        callers that genuinely only want per-direction padding analysis.
        """
        grouped: dict[int, list[EspRecord]] = {}
        for record in self.esp_records:
            grouped.setdefault(record.spi, []).append(record)
        return {spi: tuple(records) for spi, records in grouped.items()}

    def esp_tunnels(self) -> list[EspTunnel]:
        by_spi = self.esp_records_by_spi()
        first_frame = {spi: min(r.frame_no for r in records) for spi, records in by_spi.items()}
        endpoint_groups: dict[frozenset[str], list[int]] = {}
        for spi, records in by_spi.items():
            endpoints = frozenset({records[0].src, records[0].dst})
            endpoint_groups.setdefault(endpoints, []).append(spi)

        tunnels: list[EspTunnel] = []
        for spis in endpoint_groups.values():
            ordered = sorted(spis, key=lambda spi: first_frame[spi])
            for i in range(0, len(ordered), 2):
                spi_a = ordered[i]
                spi_b = ordered[i + 1] if i + 1 < len(ordered) else None
                tunnels.append(
                    EspTunnel(
                        spi_a=spi_a,
                        spi_b=spi_b,
                        records_a=by_spi[spi_a],
                        records_b=by_spi[spi_b] if spi_b is not None else (),
                    )
                )
        return tunnels


def _has_non_esp_marker(udp_payload: bytes) -> bool:
    """RFC 3948 §2.2: on UDP/4500, an IKE message is preceded by a 4-byte
    all-zero "Non-ESP Marker" so the receiver can tell it apart from
    ESP-in-UDP, which has none (its first 4 bytes are the ESP SPI, which
    is never legitimately zero). A fixed-position, fixed-value check
    straight from the RFC — not protocol dissection in the sense
    invariant 4 rules out, since nothing about IKE's internal structure is
    interpreted here, only one reserved field's value.
    """
    return len(udp_payload) >= 4 and udp_payload[:4] == b"\x00\x00\x00\x00"


def demux(records: Sequence[PacketRecord]) -> DemuxResult:
    ike_frames: list[int] = []
    esp_records: list[EspRecord] = []
    ah_frames: list[int] = []

    for record in records:
        if record.proto == 17 and record.dport == IKE_PORT or record.sport == IKE_PORT:
            ike_frames.append(record.frame_no)
        elif record.proto == 17 and (record.dport == NAT_T_PORT or record.sport == NAT_T_PORT):
            if _has_non_esp_marker(record.payload):
                ike_frames.append(record.frame_no)
            else:
                esp_record = _to_esp_record(record, record.payload)
                if esp_record is not None:
                    esp_records.append(esp_record)
        elif record.proto == ESP_PROTO:
            esp_record = _to_esp_record(record, record.payload)
            if esp_record is not None:
                esp_records.append(esp_record)
        elif record.proto == AH_PROTO:
            ah_frames.append(record.frame_no)
        # else: not a protocol this tool looks at — silently dropped

    return DemuxResult(
        ike_frames=tuple(ike_frames),
        esp_records=tuple(esp_records),
        ah_frames=tuple(ah_frames),
    )


def _to_esp_record(record: PacketRecord, payload: bytes) -> EspRecord | None:
    if len(payload) < _MIN_ESP_HEADER_LEN:
        return None  # too short to even carry an SPI+Sequence header — skip, don't crash
    spi = int.from_bytes(payload[:4], "big")
    return EspRecord(frame_no=record.frame_no, src=record.src, dst=record.dst, spi=spi, payload=payload)


def extract_ah_detected_claim(result: DemuxResult) -> Claim | None:
    """OBSERVED claim that AH (IP protocol 51) is in use, or None if no AH
    traffic was seen. Added for Phase 5's rule 11 ("AH in use
    (deprecated)") — a direct read of the IP protocol field, not an
    inference, so OBSERVED at confidence 1.0 like `ike_parse.py`'s claims.
    Deep AH analysis stays out of scope (per MVP_BUILD_PROMPT.md Phase 4's
    "Do not build"); this only reports that AH frames exist.
    """
    if not result.ah_frames:
        return None
    return Claim(
        field="ah.detected",
        value=True,
        tier=Tier.OBSERVED,
        confidence=1.0,
        method="demux.extract_ah_detected_claim",
        evidence=result.ah_frames,
    )

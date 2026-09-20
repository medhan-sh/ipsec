"""pipeline.py — real-capture-to-inference adapters (added on Phase 4
review, item 5).

Before this file existed, the only code path proven to connect real
parsed captures to `notify_posture`/`esp_constraints` lived inside
`tests/integration/test_end_to_end.py`. That was fine while nothing else
needed it, but Phase 6 will need to write a CLI that does the exact same
wiring — and if that wiring is written a second time there, nothing
checks that the two agree. This module is the one place that wiring
lives; both the integration tests and (eventually) `cli.py` import it,
so there is exactly one implementation to keep correct.

`inference/` importing from `protocol/` is within ARCHITECTURE.md's
dependency rule (inference -> core + protocol); this module is why that
allowance exists.
"""

from __future__ import annotations

from ipsec_analyzer.core.claims import Claim
from ipsec_analyzer.inference.esp_constraints.engine import (
    EspConstraintResult,
    EspPacketObservation,
    analyze_esp_flow,
)
from ipsec_analyzer.inference.notify_posture import assess_notify_posture
from ipsec_analyzer.protocol.demux import EspRecord, EspTunnel
from ipsec_analyzer.protocol.ike_parse import ParsedIke, notify_posture_inputs

_ESP_HEADER_LEN = 8  # SPI (4) + Sequence Number (4), RFC 4303 §2


def _esp_record_to_observation(record: EspRecord, direction_label: str) -> EspPacketObservation:
    """`direction_label` just needs to be a consistent label per physical
    direction — engine.py never interprets the label itself beyond
    telling directions apart, so there's no need to guess which one is
    "forward". `ciphertext_prefix` is the 4 bytes right after the 8-byte
    SPI+Sequence header, which is exactly what engine.py's
    NULL-encryption check reads (see esp_constraints/engine.py and
    reports/phase-3.md).
    """
    wire_len = len(record.payload) - _ESP_HEADER_LEN
    ciphertext_prefix = record.payload[_ESP_HEADER_LEN : _ESP_HEADER_LEN + 4]
    return EspPacketObservation(direction=direction_label, wire_len=wire_len, ciphertext_prefix=ciphertext_prefix)


def esp_tunnel_to_observations(tunnel: EspTunnel) -> list[EspPacketObservation]:
    """Both directions of one paired Child SA (see demux.py's
    `esp_tunnels()`) as one flow. Feeding both directions in is what
    Phase 4's review fix #2 was about: the ACK anchor needs a reverse
    direction inside the same flow to find, which a single SPI's records
    alone can never provide.
    """
    observations = [_esp_record_to_observation(r, "a") for r in tunnel.records_a]
    observations += [_esp_record_to_observation(r, "b") for r in tunnel.records_b]
    return observations


def analyze_esp_tunnel(tunnel: EspTunnel) -> EspConstraintResult:
    observations = esp_tunnel_to_observations(tunnel)
    evidence = tuple(r.frame_no for r in tunnel.records_a) + tuple(r.frame_no for r in tunnel.records_b)
    return analyze_esp_flow(observations, evidence=evidence)


def assess_notify_posture_from_capture(parsed: ParsedIke) -> list[Claim] | None:
    """None means "no (fully-captured) IKE_SA_INIT observed in this
    capture" — the caller-facing signal to treat this as a coverage gap
    rather than calling `assess_notify_posture` with all-missing fields
    (which would produce the same NOT_OBSERVABLE result anyway, but this
    makes the "nothing to assess" case explicit rather than incidental).
    """
    inputs = notify_posture_inputs(parsed)
    if inputs is None:
        return None
    return assess_notify_posture(**inputs)

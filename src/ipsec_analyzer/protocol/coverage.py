"""coverage.py — one structured record for facts nothing else can
recompute later (added on Phase 4's review, item 3).

The PRD calls coverage "the one number that matters most." Its inputs
exist right here, at parse time: `ingest.py` knows how many packets it
had to skip, `demux.py` knows whether both directions of each ESP tunnel
pairing were actually observed, and `ike_parse.py` knows whether
IKE_SA_INIT's request/response were observed *and fully captured* — not
just present as a frame. None of this is recoverable later from a list of
Claims alone; a Phase 6 report trying to reconstruct "was this capture
truncated" after the fact would have to guess. `build_capture_coverage()`
assembles it once, here, from the three protocol/ modules that each hold
one piece of it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ipsec_analyzer.protocol.demux import DemuxResult
from ipsec_analyzer.protocol.ike_parse import ParsedIke


@dataclass(frozen=True)
class CaptureCoverage:
    total_packets_ingested: int
    packets_skipped: int
    tshark_exit_clean: bool
    ike_sa_init_request_observed: bool
    ike_sa_init_response_observed: bool
    esp_tunnels_total: int
    esp_tunnels_missing_a_direction: int


def build_capture_coverage(
    total_packets_ingested: int,
    packets_skipped: int,
    demux_result: DemuxResult,
    parsed_ike: ParsedIke,
) -> CaptureCoverage:
    from ipsec_analyzer.protocol.ike_parse import EXCHANGE_TYPE_IKE_SA_INIT

    init_messages = [m for m in parsed_ike.messages if m.exchange_type == EXCHANGE_TYPE_IKE_SA_INIT]
    request_observed = any(m.is_request and m.is_fully_captured for m in init_messages)
    response_observed = any(not m.is_request and m.is_fully_captured for m in init_messages)

    tunnels = demux_result.esp_tunnels()
    missing_direction = sum(1 for t in tunnels if t.spi_b is None)

    return CaptureCoverage(
        total_packets_ingested=total_packets_ingested,
        packets_skipped=packets_skipped,
        tshark_exit_clean=parsed_ike.tshark_exit_clean,
        ike_sa_init_request_observed=request_observed,
        ike_sa_init_response_observed=response_observed,
        esp_tunnels_total=len(tunnels),
        esp_tunnels_missing_a_direction=missing_direction,
    )

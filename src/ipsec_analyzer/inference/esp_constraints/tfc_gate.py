"""3b — TFC gate (MVP_BUILD_PROMPT.md Phase 3; RFC 4303's
traffic-flow-confidentiality padding).

Must run before the GCD granularity estimate (gcd_estimator.py) is
trusted: TFC padding destroys the residue structure the estimator depends
on, and does so silently — a flow padded to a fixed size can still produce
*some* GCD, just not a meaningful one. This module never tries to
distinguish deliberate TFC from some other cause; per invariant 6 it only
recognizes patterns consistent with TFC and refuses to guess past them.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

# Heuristic thresholds, not framing constants (there's no RFC section that
# defines "how uniform is suspiciously uniform"). A length distribution
# this dominated by one length, sitting at a typical near-MTU size, reads
# as padding-to-fixed-size rather than organic traffic.
DOMINANT_FRACTION_THRESHOLD = 0.9
NEAR_MTU_THRESHOLD = 1400


def suspect_tfc_by_length_distribution(wire_lengths: Sequence[int]) -> bool:
    """True when one length dominates the distribution and sits near the
    MTU — the length-distribution half of Phase 3's TFC gate. The other
    half (an invalid raw GCD) is already handled by gcd_estimator.py
    refusing to return anything outside {4, 8, 16}; callers should treat
    that refusal as TFC-consistent too, per the spec's phrasing ("Flag TFC
    when ... or when the GCD does not land in {4, 8, 16}").
    """
    if not wire_lengths:
        return False
    counts = Counter(wire_lengths)
    dominant_len, dominant_count = counts.most_common(1)[0]
    fraction = dominant_count / len(wire_lengths)
    return fraction >= DOMINANT_FRACTION_THRESHOLD and dominant_len >= NEAR_MTU_THRESHOLD

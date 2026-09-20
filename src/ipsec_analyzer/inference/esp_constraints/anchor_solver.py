"""3c — ICV by anchor (MVP_BUILD_PROMPT.md Phase 3).

Only the TCP pure-ACK anchor is in scope for this MVP — no other anchor
(RTP, DNS, etc.) is built here; see the phase's explicit "Do not build".
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from ipsec_analyzer.core.constants import SUITE_FRAMINGS

MIN_ANCHOR_PACKETS = 5  # K, per the spec

# "The large majority of bytes" — a burst direction must clear this share
# of total bytes before it's treated as sustained-unidirectional.
BURST_MAJORITY_FRACTION = 0.75

# Bare TCP ACK inner lengths: 40 bytes with no TCP timestamp option, 52
# bytes with one (12 extra bytes: kind+len+2x4-byte timestamps).
ACK_INNER_LEN_HYPOTHESES = (40, 52)


def _ciphertext_len(inner_plaintext_len: int, granularity: int) -> int:
    """RFC 4303 §2.4, the same formula as synth/synth_esp.py's
    ciphertext_len — deliberately duplicated rather than imported.
    `inference/` may not depend on `synth/` (a test oracle, not shipped
    logic) per ARCHITECTURE.md's dependency rule, and this formula doesn't
    belong in the frozen core/constants.py table either: it's arithmetic
    that applies to every suite, not a per-suite value. Both copies cite
    the same RFC section and are independently tested against the same
    worked cases.
    """
    n = inner_plaintext_len + 2
    return ((n + granularity - 1) // granularity) * granularity


def _explicit_ivs_for_granularity(granularity: int) -> frozenset[int]:
    """The explicit_iv values that actually occur among suites at this
    granularity — not assumed to be a single value. It very nearly is (every
    cbc suite has explicit_iv == pad_granularity, and nearly every counter
    suite has explicit_iv == 8), but NULL-ENC breaks that for granularity=4:
    it has explicit_iv=0 despite being bucketed under "counter" for GCD
    purposes (see constants.py's NULL-ENC classification note). Deriving
    this set from the table rather than hand-copying a single value is what
    caught that the first version of this function got wrong — it assumed
    exactly one explicit_iv per granularity and raised on NULL-ENC's flow.
    """
    return frozenset(s.explicit_iv for s in SUITE_FRAMINGS.values() if s.pad_granularity == granularity)


def find_sustained_reverse_anchor(
    directions: Sequence[str], wire_lengths: Sequence[int]
) -> int | None:
    """Finds the reverse direction's modal E value, given a sustained
    unidirectional burst exists in the other direction. Returns None
    (abstain — no anchor) when: there's no second direction at all, no
    direction carries a large majority of the bytes, more than one
    direction remains after removing the burst direction (ambiguous), or
    the candidate reverse direction has fewer than MIN_ANCHOR_PACKETS
    packets at its single most common length.
    """
    if not directions or len(directions) != len(wire_lengths):
        return None

    bytes_by_direction: dict[str, int] = {}
    lens_by_direction: dict[str, list[int]] = {}
    for direction, length in zip(directions, wire_lengths):
        bytes_by_direction[direction] = bytes_by_direction.get(direction, 0) + length
        lens_by_direction.setdefault(direction, []).append(length)

    if len(bytes_by_direction) < 2:
        return None  # only one direction present — no anchor possible

    total_bytes = sum(bytes_by_direction.values())
    burst_direction = max(bytes_by_direction, key=bytes_by_direction.get)
    if bytes_by_direction[burst_direction] / total_bytes < BURST_MAJORITY_FRACTION:
        return None  # no direction carries a large majority of the bytes

    reverse_directions = [d for d in lens_by_direction if d != burst_direction]
    if len(reverse_directions) != 1:
        return None  # ambiguous which direction is the anchor candidate
    reverse_direction = reverse_directions[0]

    counts = Counter(lens_by_direction[reverse_direction])
    modal_len, modal_count = counts.most_common(1)[0]
    if modal_count < MIN_ANCHOR_PACKETS:
        return None
    return modal_len


def solve_icv_candidates(e_ack: int, granularity: int) -> frozenset[int]:
    """Solves icv = E_ack - explicit_iv - ciphertext_len(P) over every
    (explicit_iv, P) combination that actually occurs among suites at this
    granularity — both P hypotheses (40: no TCP timestamps, 52: with) and
    every real explicit_iv value in this bucket (see
    `_explicit_ivs_for_granularity` — usually just one, but NULL-ENC means
    granularity=4 has two). Keeps only results that match a real suite's
    icv_len within this granularity's family: an arithmetically valid but
    never-observed icv_len isn't "plausible" by this method's own
    definition. Every combination that lands on a real icv_len is kept —
    the caller widens the candidate set rather than picking one, same
    principle as the two P hypotheses, just applied on both axes that
    actually vary.
    """
    explicit_ivs = _explicit_ivs_for_granularity(granularity)
    known_icv_values = {
        s.icv_len for s in SUITE_FRAMINGS.values() if s.pad_granularity == granularity
    }
    plausible = set()
    for explicit_iv in explicit_ivs:
        for inner_len in ACK_INNER_LEN_HYPOTHESES:
            icv = e_ack - explicit_iv - _ciphertext_len(inner_len, granularity)
            if icv in known_icv_values:
                plausible.add(icv)
    return frozenset(plausible)

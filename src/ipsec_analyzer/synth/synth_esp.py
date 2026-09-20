"""Synthetic ESP wire-length oracle (RFC 4303 §2.4 padding/ICV arithmetic).

Given a SuiteFraming and an inner (pre-ESP) plaintext length, computes the
ESP wire length E — the arithmetic Phase 3's constraint engine will later be
tested against. Nothing here builds packets, writes pcaps, or is consumed by
any later phase yet; it is purely a labelled-data generator.

E is ESP bytes *after* the 8-byte SPI + Sequence Number header (RFC 4303
§2); this module never adds that header — callers reason about the full
on-wire packet size separately if that is ever needed.
"""

from __future__ import annotations

from dataclasses import dataclass

from ipsec_analyzer.core.constants import SuiteFraming


def ciphertext_len(inner_plaintext_len: int, framing: SuiteFraming) -> int:
    """RFC 4303 §2.4: 2 trailer bytes (Pad Length, Next Header) are appended
    to the plaintext before encryption, then the whole thing is padded up to
    the suite's alignment granularity (block size for CBC, 4 bytes for
    counter/AEAD modes — both already captured by `pad_granularity`).
    """
    if inner_plaintext_len < 0:
        raise ValueError("inner_plaintext_len must be >= 0")
    b = framing.pad_granularity
    n = inner_plaintext_len + 2
    return ((n + b - 1) // b) * b


def esp_wire_len(inner_plaintext_len: int, framing: SuiteFraming) -> int:
    """E = explicit_iv + ciphertext_len + icv_len."""
    return framing.explicit_iv + ciphertext_len(inner_plaintext_len, framing) + framing.icv_len


@dataclass(frozen=True)
class SyntheticPacket:
    direction: str   # "forward" | "reverse"
    inner_len: int   # P, the pre-ESP plaintext length
    wire_len: int    # E, per esp_wire_len()


def synth_esp_flow(
    framing: SuiteFraming,
    count: int,
    forward_run: int = 8,
    reverse_run: int = 1,
    forward_inner_range: tuple[int, int] = (40, 1400),
    ack_inner_len: int = 40,
) -> list[SyntheticPacket]:
    """A bulk-transfer flow: mostly forward packets carrying the majority of
    bytes, sparse fixed-size ACKs the other way, interleaved in a repeating
    `forward_run` : `reverse_run` pattern.

    Forward inner lengths sweep densely and deterministically through
    `forward_inner_range` (wrapping if `count` needs more values than the
    range spans) rather than clustering near one size. This is deliberate,
    not decorative: Phase 3's GCD estimator only recovers the true padding
    granularity `b` when two observed E values differ by exactly `b`, which
    requires the sampled inner lengths to actually cross a padding-bucket
    boundary. A narrow near-MTU cluster (e.g. two fixed sizes 1400 bytes
    apart) can produce a pairwise-difference GCD that is some large multiple
    of `b` instead of `b` itself — a bug in this oracle, not in Phase 3's
    estimator, and one that would otherwise surface as a confusing Phase 3
    test failure. A dense sweep spanning at least one full bucket width (the
    default range is far wider than the largest `pad_granularity`, 16)
    guarantees the boundary is crossed for every suite in constants.py; see
    tests/test_synth_esp.py::TestGcdRecoverability.

    This is the shape Phase 3's TCP-pure-ACK anchor will look for later —
    a sustained unidirectional burst plus a modal-length reverse trickle.
    Nothing here analyzes that shape; it only generates it.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    forward_low, forward_high = forward_inner_range
    span = forward_high - forward_low + 1
    if span < 1:
        raise ValueError("forward_inner_range must be non-empty")
    cycle = forward_run + reverse_run
    packets: list[SyntheticPacket] = []
    forward_index = 0
    for i in range(count):
        if (i % cycle) < forward_run:
            inner_len = forward_low + (forward_index % span)
            forward_index += 1
            direction = "forward"
        else:
            inner_len = ack_inner_len
            direction = "reverse"
        packets.append(
            SyntheticPacket(
                direction=direction,
                inner_len=inner_len,
                wire_len=esp_wire_len(inner_len, framing),
            )
        )
    return packets

"""3 — ESP constraint engine (F6b), orchestrator (MVP_BUILD_PROMPT.md
Phase 3).

Ties together the TFC gate (3b), GCD granularity estimator (3a), ACK
anchor ICV solver (3c), and a NULL-encryption check (added on review after
Phase 3) into the candidate-set narrowing described in 3d.

**Composition, not gating (amendment after Phase 4's review).** Each
channel fires or abstains independently; the surviving candidate set is
whatever's left after applying every channel that had something to say.
An earlier version of this function returned early — with `candidate_set
= None` — the moment the TFC gate or GCD estimator abstained, which meant
the NULL-encryption check (fully independent of granularity: it only
needs `SUITE_FRAMINGS[suite_id].icv_len`, a fixed per-candidate constant,
and the observed payload bytes) never ran at all on a capture where
granularity couldn't be determined. Every real capture obtained for Phase
4 hit exactly that path, so the fix wasn't defensive — it was live: this
change is what makes "the payload doesn't decode as NULL-plaintext" an
actual reported elimination on real data, instead of a channel that only
ever fires on synthetic fixtures with a cooperative GCD result.

The one channel that has a genuine (not just historical) dependency on
another is the ICV/anchor solve: `solve_icv_candidates` needs the
granularity to compute `ciphertext_len`, so it cannot run when granularity
is unknown. That's real math, not control-flow laziness — left as a
dependency, not "fixed" into false independence.

Everything this emits is Tier.INFERRED_SIDE_CHANNEL — a side-channel
derivation from packet sizes, never read from a protocol field — except
an abstaining channel's own claim, which is NOT_OBSERVABLE per invariant
6. `candidate_set` is now always returned (never `None`): even when every
sizing channel abstains, the NULL-encryption channel may still have
narrowed it, and an unnarrowed `CandidateSet` (universe == surviving) is
itself a meaningful, honest statement — "we learned nothing" — rather
than an absent one.

Confidence is 1.0 for the granularity claim: the GCD estimator is
deterministic, so when it succeeds its result is exactly right given the
observed data. The ICV claim is also 1.0 at the same tier — the
arithmetic is exact — but carries a caveat the granularity claim doesn't
need: the arithmetic is only exact *conditional on* the ACK anchor's
packet identification being correct, and that identification is a
heuristic real traffic can mislead. Any remaining ambiguity that isn't a
matter of trusting a heuristic (e.g. two plausible ICV hypotheses, or
several suites sharing one framing) lives structurally in the
CandidateSet — in `eliminated_by` and `indistinguishable` — not as a
further discount on confidence.

Deliberately does not build verdict lifting (Phase 5), fingerprint
ranking, ESN inference, or any anchor other than the TCP pure-ACK one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ipsec_analyzer.core.candidates import CandidateSet, eliminate
from ipsec_analyzer.core.claims import Claim, Tier
from ipsec_analyzer.core.constants import SUITE_FRAMINGS
from ipsec_analyzer.inference.esp_constraints.anchor_solver import (
    find_sustained_reverse_anchor,
    solve_icv_candidates,
)
from ipsec_analyzer.inference.esp_constraints.gcd_estimator import estimate_granularity
from ipsec_analyzer.inference.esp_constraints.tfc_gate import suspect_tfc_by_length_distribution

# RFC 4303 §2.4: the ESP trailer is always exactly 2 bytes (Pad Length,
# Next Header), plus 0..(pad_granularity-1) bytes of alignment padding.
# NULL-ENC's granularity is 4 (see constants.py), so the gap between an
# inner IP header's declared Total Length and the observed ciphertext_len
# is at least 2 and at most 2 + 3 = 5 bytes.
_NULL_ENC_TRAILER_OVERHEAD_RANGE = (2, 5)


@dataclass(frozen=True)
class EspPacketObservation:
    """The things available from a real (or synthetic) ESP flow without
    successfully decrypting it: which direction a packet went, its wire
    length E, and — when the capture actually has it, which Phase 3's own
    synthetic data now also carries for testing — a few bytes sampled at
    the ciphertext offset (right after the explicit IV). That last field
    defaults to empty: most of this phase's own tests don't need it, and
    a real adapter may not always have it either (e.g. if the IV itself
    pushes the sample past what was captured).

    Defined here rather than imported from synth's SyntheticPacket —
    `inference/` may not depend on `synth/` (a test oracle) — and real
    capture data unpacks into this same shape (see
    `inference/pipeline.py`).
    """
    direction: str
    wire_len: int
    ciphertext_prefix: bytes = b""


@dataclass(frozen=True)
class EspConstraintResult:
    granularity_claim: Claim
    icv_claim: Claim | None  # None iff no anchor was found/usable
    null_encryption_claim: Claim | None  # True/False whenever the check ran; None only if NULL-ENC never reached it (see _apply_null_encryption_channel)
    candidate_set: CandidateSet  # always returned — see module docstring


def _family_for_granularity(granularity: int) -> str:
    """Derived from constants.py's table rather than hand-copied, same
    reasoning as anchor_solver._explicit_ivs_for_granularity.
    """
    families = {s.family for s in SUITE_FRAMINGS.values() if s.pad_granularity == granularity}
    if len(families) != 1:
        raise AssertionError(
            f"expected exactly one family for granularity {granularity}, found {sorted(families)}"
        )
    return families.pop()


def _indistinguishable_groups(suite_ids: frozenset[str]) -> tuple[frozenset[str], ...]:
    """Suites sharing (family, pad_granularity, explicit_iv, icv_len) can
    never be separated by this method — key length never changes framing
    at all. Computed over whatever survives elimination; groups of size 1
    aren't "indistinguishable from" anything and are omitted.

    **Amendment (Phase 6a closeout review):** the returned tuple's *order*
    must not depend on `suite_ids`' frozenset iteration order — that order
    is seeded by Python's per-process hash randomization (`PYTHONHASHSEED`
    is random by default) and is therefore different across separate runs
    of the exact same process on the exact same capture. That's invisible
    to any test comparing sets/frozensets with `==` (membership, not
    order, is what those compare), but it broke `tests/fixtures/
    golden_findings.json` — a real cross-process determinism bug this
    module shipped in Phase 3/4 and nothing caught until a byte-for-byte
    JSON diff was checked. Iterating `sorted(suite_ids)` fixes each
    group's first-seen order deterministically; sorting the final tuple by
    each group's own sorted members is a second, independent guarantee
    that doesn't rely on dict-insertion-order semantics at all.
    """
    groups: dict[tuple[str, int, int, int], set[str]] = {}
    for suite_id in sorted(suite_ids):
        framing = SUITE_FRAMINGS[suite_id]
        key = (framing.family, framing.pad_granularity, framing.explicit_iv, framing.icv_len)
        groups.setdefault(key, set()).add(suite_id)
    return tuple(
        frozenset(group)
        for group in sorted((g for g in groups.values() if len(g) > 1), key=lambda g: sorted(g))
    )


def _looks_like_null_encrypted_ip_header(prefix: bytes, candidate_ciphertext_len: int) -> bool:
    """True only if `prefix` plausibly opens a real, unencrypted inner IP
    packet whose declared length is consistent with `candidate_ciphertext_len`
    (the ciphertext region size NULL-ENC's `icv_len` would imply). Real ESP
    ciphertext is effectively random: getting a valid version nibble AND a
    length-consistent Total Length field by chance is astronomically
    unlikely, which is what lets this be treated as a hard elimination
    rather than a probabilistic guess (per review).

    Independent of granularity/TFC entirely — TFC padding changes how
    much padding is added, not the byte content of the ciphertext offset
    itself, so this channel runs regardless of what the sizing channels
    concluded (see analyze_esp_flow).

    IPv6 is recognized by version nibble but not cross-checked against
    length here (no cheap length field at this offset) — a v6 nibble alone
    is treated as inconclusive, not confirming.
    """
    if len(prefix) < 4:
        return False
    version = prefix[0] >> 4
    if version == 6:
        return False  # inconclusive, not confirming — see docstring
    if version != 4:
        return False
    declared_total_length = int.from_bytes(prefix[2:4], "big")
    overhead = candidate_ciphertext_len - declared_total_length
    low, high = _NULL_ENC_TRAILER_OVERHEAD_RANGE
    return low <= overhead <= high


def _granularity_channel(wire_lengths: Sequence[int], evidence: tuple[int, ...]) -> tuple[Claim, int | None]:
    """3a+3b composed: the TFC gate must run before the GCD result is
    trusted. Returns the granularity Claim and the raw granularity value
    (None if either channel abstained), so callers can tell "abstained"
    from "succeeded" without re-deriving it from the Claim's tier.
    """
    if suspect_tfc_by_length_distribution(wire_lengths):
        return (
            Claim(
                field="esp.granularity",
                value=None,
                tier=Tier.NOT_OBSERVABLE,
                confidence=0.0,
                method="esp_constraints.tfc_gate",
                evidence=evidence,
                caveats=("TFC padding suspected: one length dominates and sits near the MTU",),
            ),
            None,
        )

    granularity = estimate_granularity(wire_lengths)
    if granularity is None:
        return (
            Claim(
                field="esp.granularity",
                value=None,
                tier=Tier.NOT_OBSERVABLE,
                confidence=0.0,
                method="esp_constraints.gcd_estimator",
                evidence=evidence,
                caveats=(
                    "GCD of pairwise E differences did not land in {4, 8, 16}, or fewer "
                    "than 8 distinct E values were observed — possible TFC padding or "
                    "insufficient data; not interpolated or rounded to the nearest valid "
                    "granularity",
                ),
            ),
            None,
        )

    return (
        Claim(
            field="esp.granularity",
            value=granularity,
            tier=Tier.INFERRED_SIDE_CHANNEL,
            confidence=1.0,
            method="esp_constraints.gcd_estimator",
            evidence=evidence,
        ),
        granularity,
    )


def _icv_channel(
    directions: Sequence[str],
    wire_lengths: Sequence[int],
    granularity: int | None,
    evidence: tuple[int, ...],
) -> tuple[Claim | None, frozenset[int] | None]:
    """3c: only runs when granularity is known — solve_icv_candidates
    needs it to compute ciphertext_len. Returns (claim, plausible_icv);
    both None if the channel couldn't run or found no anchor.
    """
    if granularity is None:
        return None, None
    anchor_len = find_sustained_reverse_anchor(directions, wire_lengths)
    if anchor_len is None:
        return None, None
    plausible_icv = solve_icv_candidates(anchor_len, granularity)
    if not plausible_icv:
        return None, None
    claim = Claim(
        field="esp.icv_len",
        value=tuple(sorted(plausible_icv)),
        tier=Tier.INFERRED_SIDE_CHANNEL,
        confidence=1.0,
        method="esp_constraints.anchor_solver",
        evidence=evidence,
        caveats=(
            f"ICV derived from a presumed TCP pure-ACK anchor at length {anchor_len}; "
            f"anchor identification (modal smallest reverse-direction length during a "
            f"sustained unidirectional burst) is heuristic, not a protocol-level fact. "
            f"The arithmetic from an identified anchor is exact, but only conditional "
            f"on that identification being correct — a flow with small data packets or "
            f"a chatty reverse channel could mislead it.",
        ),
    )
    return claim, frozenset(plausible_icv)


def _null_encryption_claim(value: bool, evidence: tuple[int, ...], reason: str) -> Claim:
    return Claim(
        field="esp.null_encryption_confirmed",
        value=value,
        tier=Tier.INFERRED_SIDE_CHANNEL,
        confidence=1.0,
        method="esp_constraints.null_check",
        evidence=evidence,
        caveats=(reason,),
    )


def _apply_null_encryption_channel(
    candidate_set: CandidateSet,
    observations: Sequence[EspPacketObservation],
    evidence: tuple[int, ...],
) -> tuple[CandidateSet, Claim | None]:
    """Independent of granularity/TFC — see module docstring. Only ever
    narrows whatever is passed in; never widens or resurrects.

    Returns the (possibly narrowed) candidate set, plus a `Claim` for
    Phase 5's rule 10 ("NULL encryption") whenever this channel actually
    had something to check — i.e. NULL-ENC survived every earlier channel
    and reached this one still alive. `True` when it's positively
    confirmed (survives with real supporting payload evidence), `False`
    when this channel ran and eliminated it (no payload evidence at all,
    or payload evidence that doesn't parse as NULL-ENC's plaintext). Only
    `None` (no claim) when there was nothing to check in the first place
    — NULL-ENC already excluded by a different, earlier channel (e.g. the
    granularity/family exclusion), in which case that channel's own claim
    already answers the same question and attributing a "false" result
    here would misstate which method actually produced it.

    **Amendment (Phase 6b review):** the previous version only ever
    returned a claim on positive confirmation. On every real capture
    obtained for this project where granularity abstains (the common
    case — too few distinct packet sizes), this channel is the one doing
    real work, eliminating NULL-ENC via the IP-header check — and that
    elimination was visible in the candidate set's own `eliminated_by`
    while `assessment/engine.py` simultaneously reported rule 10 as a
    coverage gap for lack of any claim to check. Same claim, contradicting
    itself between two sections of one report. Invariant 3's is-it-a-
    finding-or-an-absence distinction is not "did anything get
    eliminated" — it's "did the check run": here, that's exactly
    `null_like_survivors` being non-empty at entry.
    """
    null_like_survivors = frozenset(
        suite_id for suite_id in candidate_set.surviving if SUITE_FRAMINGS[suite_id].explicit_iv == 0
    )
    if not null_like_survivors:
        return candidate_set, None  # nothing survived to this channel — see amendment note above

    representative = next((o for o in observations if o.ciphertext_prefix), None)
    if representative is None:
        reason = (
            "no payload byte evidence available to confirm NULL encryption; real ESP "
            "ciphertext is essentially never coincidentally NULL, so absent positive "
            "evidence NULL-ENC candidates are eliminated"
        )
        candidate_set = eliminate(candidate_set, set(null_like_survivors), reason)
        return candidate_set, _null_encryption_claim(False, evidence, reason)

    confirmed = frozenset(
        suite_id
        for suite_id in null_like_survivors
        if _looks_like_null_encrypted_ip_header(
            representative.ciphertext_prefix,
            representative.wire_len - SUITE_FRAMINGS[suite_id].icv_len,
        )
    )
    doomed_null = null_like_survivors - confirmed
    if doomed_null:
        version_nibble = representative.ciphertext_prefix[0] >> 4 if representative.ciphertext_prefix else None
        elimination_reason = (
            f"payload at the ciphertext offset does not parse as a length-consistent "
            f"IP header (version nibble {hex(version_nibble) if version_nibble is not None else 'n/a'}); "
            f"real ESP ciphertext is effectively random and essentially never parses "
            f"this way, so NULL encryption is eliminated absent positive evidence"
        )
        candidate_set = eliminate(candidate_set, set(doomed_null), elimination_reason)

    if not confirmed:
        return candidate_set, _null_encryption_claim(
            False,
            evidence,
            "payload at the ciphertext offset does not parse as a length-consistent IP header "
            "for any surviving NULL-ENC candidate",
        )

    null_encryption_claim = _null_encryption_claim(
        True,
        evidence,
        f"payload at the ciphertext offset parses as a length-consistent IP header "
        f"for {sorted(confirmed)}; consistent with NULL encryption (no confidentiality "
        f"protection on this traffic)",
    )
    return candidate_set, null_encryption_claim


def analyze_esp_flow(
    observations: Sequence[EspPacketObservation],
    evidence: tuple[int, ...] = (),
) -> EspConstraintResult:
    wire_lengths = [o.wire_len for o in observations]
    directions = [o.direction for o in observations]

    universe = frozenset(SUITE_FRAMINGS)
    candidate_set = CandidateSet(universe=universe, surviving=universe, eliminated_by=())

    granularity_claim, granularity = _granularity_channel(wire_lengths, evidence)

    if granularity is not None:
        family = _family_for_granularity(granularity)
        family_bucket = frozenset(
            suite_id
            for suite_id, framing in SUITE_FRAMINGS.items()
            if framing.family == family and framing.pad_granularity == granularity
        )
        candidate_set = eliminate(
            candidate_set,
            set(universe - family_bucket),
            f"gcd(E differences) = {granularity} implies ({family}, pad_granularity={granularity}) "
            f"framing; excludes every suite outside that family/granularity",
        )

    icv_claim, plausible_icv = _icv_channel(directions, wire_lengths, granularity, evidence)
    if plausible_icv is not None:
        doomed_by_icv = frozenset(
            suite_id
            for suite_id in candidate_set.surviving
            if SUITE_FRAMINGS[suite_id].icv_len not in plausible_icv
        )
        candidate_set = eliminate(
            candidate_set,
            set(doomed_by_icv),
            f"ACK anchor with inner P in {{40, 52}} implies icv_len in "
            f"{sorted(plausible_icv)}; excludes every surviving suite with a different "
            f"icv_len",
        )

    # NULL-encryption channel: runs regardless of whether granularity/TFC
    # succeeded (see module docstring — this is the composition fix).
    candidate_set, null_encryption_claim = _apply_null_encryption_channel(candidate_set, observations, evidence)

    candidate_set = CandidateSet(
        universe=candidate_set.universe,
        surviving=candidate_set.surviving,
        eliminated_by=candidate_set.eliminated_by,
        indistinguishable=_indistinguishable_groups(candidate_set.surviving),
    )

    return EspConstraintResult(
        granularity_claim=granularity_claim,
        icv_claim=icv_claim,
        null_encryption_claim=null_encryption_claim,
        candidate_set=candidate_set,
    )

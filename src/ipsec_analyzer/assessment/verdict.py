"""verdict.py — verdict lifting over candidate sets (MVP_BUILD_PROMPT.md
Phase 5).

The PRD's third core idea: IKEv2 hides the ESP cipher, and some cipher
suites are provably indistinguishable on the wire. Rather than guess, the
system narrows to a candidate set (Phase 3) and evaluates the *risk
question* across the whole set. Evaluates one boolean predicate over
*every* `CandidateSet.surviving` member:

- Every survivor agrees -> lift the verdict at confidence 1.0, without
  naming which cipher is actually in use. The certainty comes from
  unanimity across the candidate set, not from identifying the cipher.
- Survivors disagree -> `AmbiguousVerdict`, naming which candidates drive
  which side of the disagreement — never silently picking one, and never
  averaging into a fractional "confidence".

`confidentiality_acceptable` and `integrity_acceptable` are the two
predicates this MVP ships. `confidentiality_acceptable` matches both of
MVP_BUILD_PROMPT.md Phase 5's worked acceptance scenarios (an
all-strong-AEAD set lifts True; a `g == 8` set — 64-bit block ciphers —
lifts False, which *is* "a weak-crypto verdict": unanimous agreement that
confidentiality is not acceptable). `integrity_acceptable` was added on
Phase 5a's review specifically to be a *separate* axis from
confidentiality: a suite's cipher and its integrity transform are graded
independently (AES-CTR is strong confidentiality paired with a HMAC-SHA1
integrity transform RFC 8221 §5 lists as MUST NOT for new
implementations — strong on one axis, weak on the other), which is why
verdict-lifting is done per-predicate rather than one combined
"is this suite okay" boolean. A predicate is a mapping (`dict[str, bool]`)
precomputed over `constants.py`'s table, not a callable — see
`PREDICATES` — so the same "data, not code" reasoning
`assessment/rules/schema.py` applies here to verdict logic too, not just
policy rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ipsec_analyzer.core.candidates import CandidateSet
from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.core.constants import SUITE_FRAMINGS


def _confidentiality_acceptable(suite_id: str) -> bool:
    """False for the two families this MVP already treats as broken
    findings on their own (rules 8 and 10): 64-bit block ciphers
    (pad_granularity == 8 — Sweet32-class birthday-bound attacks well
    within realistic traffic volumes) and NULL encryption (explicit_iv ==
    0 — no confidentiality protection at all). True for everything else:
    AES-CBC-16 and every counter/AEAD suite, including AES-CTR+HMAC
    combinations that aren't literally AEAD in the single-primitive sense
    but are still cryptographically sound for confidentiality. This is a
    policy judgment call, not an objective fact pulled from an RFC —
    flagged as such, same as any other severity assignment in this
    project.
    """
    framing = SUITE_FRAMINGS[suite_id]
    return framing.pad_granularity != 8 and framing.explicit_iv != 0


# VERIFY BY HAND, same standard as core/constants.py: RFC 8221 §5 ("ESP and
# AH Algorithm Requirements") lists AUTH_HMAC_MD5_96 and AUTH_HMAC_SHA1_96
# as MUST NOT for new implementations. This checks the suite_id's own
# integrity-transform name rather than icv_len, deliberately: several
# suites here share an icv_len of 12 (AES-*-GCM-12, AES-*-CCM-12, and
# AES-CTR + HMAC-SHA1-96 all truncate to 96 bits) but are not equally
# acceptable — an AEAD tag (GCM/CCM/ChaCha20-Poly1305) is intrinsic to the
# cipher and unaffected by this MUST-NOT, while a *generic-composition*
# HMAC-SHA1/MD5 transform is exactly what RFC 8221 deprecates, regardless
# of its output length. This is what makes confidentiality_acceptable and
# integrity_acceptable genuinely different axes rather than the same
# framing fact read twice.
_WEAK_GENERIC_MAC_MARKERS = ("HMAC-MD5", "HMAC-SHA1")


def _integrity_acceptable(suite_id: str) -> bool:
    """False for suites whose integrity comes from a generic-composition
    HMAC-MD5 or HMAC-SHA1 transform (RFC 8221 §5, MUST NOT for new
    implementations) — independent of how strong that same suite's
    confidentiality is. True for every AEAD suite (the tag is intrinsic to
    GCM/CCM/ChaCha20-Poly1305, not a bolted-on HMAC) and for SHA-2-family
    HMAC and AES-XCBC-96 suites. Policy judgment call, not an objective
    fact pulled directly from the RFC's own boolean — flagged as such,
    same as confidentiality_acceptable.
    """
    suite_id_text = SUITE_FRAMINGS[suite_id].suite_id
    return not any(marker in suite_id_text for marker in _WEAK_GENERIC_MAC_MARKERS)


PREDICATES: dict[str, dict[str, bool]] = {
    "confidentiality_acceptable": {suite_id: _confidentiality_acceptable(suite_id) for suite_id in SUITE_FRAMINGS},
    "integrity_acceptable": {suite_id: _integrity_acceptable(suite_id) for suite_id in SUITE_FRAMINGS},
}


@dataclass(frozen=True)
class Verdict:
    predicate: str
    outcome: bool
    confidence: float
    basis: str
    # Phase 5a review fix #5: the weakest tier among the claims that
    # narrowed the candidate set this verdict was lifted over. Distinct
    # from `confidence`, which stays 1.0 on unanimity regardless —
    # unanimity is a logical fact about the surviving set (every candidate
    # agrees), while basis_tier describes how good the *evidence* was that
    # produced that surviving set in the first place. A verdict can be
    # fully confident (1.0) yet built entirely on INFERRED_SIDE_CHANNEL
    # evidence — that's still worth surfacing to a reader deciding how
    # much to trust it. Defaults to NOT_OBSERVABLE: a candidate set built
    # without passing which claims narrowed it (e.g. a raw universe with
    # no elimination behind it at all) has no evidentiary basis to report.
    basis_tier: Tier = Tier.NOT_OBSERVABLE


@dataclass(frozen=True)
class AmbiguousVerdict:
    predicate: str
    surviving_true: frozenset[str]
    surviving_false: frozenset[str]
    basis: str
    # Phase 6b review fix: these were only ever set on `Verdict`, so every
    # ambiguous result silently dropped both fields from the emitted JSON
    # — a real contract defect, not a design choice (the Phase 6 report
    # claimed `basis_tier` was present on "every verdict" when it wasn't).
    # `confidence` is 1.0 here for the same reason it is on `Verdict`:
    # disagreement is itself a certain fact about the candidate set — we
    # are not "50% sure" the survivors disagree, we know they do.
    # `basis_tier` means the same thing as on `Verdict`: the weakest tier
    # among the claims that narrowed the set, independent of confidence.
    confidence: float = 1.0
    basis_tier: Tier = Tier.NOT_OBSERVABLE


def lift_verdict(
    candidate_set: CandidateSet,
    predicate_name: str,
    *,
    narrowing_tiers: Sequence[Tier] = (),
) -> Verdict | AmbiguousVerdict | None:
    """None iff `candidate_set.surviving` is empty — nothing to lift a
    verdict over (every candidate was eliminated, which is itself a
    finding for whatever eliminated them all, not a verdict-lifting
    concern).

    `narrowing_tiers` is the tier of each claim that actually narrowed
    `candidate_set` down to its surviving set (e.g. an ESP flow's
    granularity/ICV/NULL-encryption claims — see
    `inference/esp_constraints/engine.py`). Not read from `candidate_set`
    itself: `CandidateSet.eliminated_by` (core/candidates.py, frozen for
    this pass) only records a human-readable reason string per eliminated
    suite, not the tier of the claim behind it, so the caller — which
    already has the actual Claim objects on hand — passes the tiers in
    directly rather than this function trying to parse tiers back out of
    free text. `min(narrowing_tiers)` becomes `basis_tier` on whichever
    result is returned — `Verdict` on unanimity, `AmbiguousVerdict` on
    disagreement, both fields present either way (Phase 6b review fix:
    an earlier version only set this on `Verdict`); omitted (or empty)
    means "no claims are known to have narrowed this set," which
    normalizes to NOT_OBSERVABLE via each dataclass's own default.
    """
    predicate = PREDICATES[predicate_name]
    surviving = candidate_set.surviving
    if not surviving:
        return None

    outcomes = {suite_id: predicate[suite_id] for suite_id in surviving}
    distinct_outcomes = set(outcomes.values())

    if len(distinct_outcomes) == 1:
        outcome = distinct_outcomes.pop()
        basis_tier = min(narrowing_tiers) if narrowing_tiers else Tier.NOT_OBSERVABLE
        return Verdict(
            predicate=predicate_name,
            outcome=outcome,
            confidence=1.0,
            basis=f"All {len(surviving)} surviving candidates agree: {predicate_name} = {outcome}",
            basis_tier=basis_tier,
        )

    surviving_true = frozenset(s for s, v in outcomes.items() if v)
    surviving_false = frozenset(s for s, v in outcomes.items() if not v)
    basis_tier = min(narrowing_tiers) if narrowing_tiers else Tier.NOT_OBSERVABLE
    return AmbiguousVerdict(
        predicate=predicate_name,
        surviving_true=surviving_true,
        surviving_false=surviving_false,
        basis=(
            f"Surviving candidates disagree on {predicate_name}: "
            f"{len(surviving_true)} agree, {len(surviving_false)} disagree"
        ),
        basis_tier=basis_tier,
    )

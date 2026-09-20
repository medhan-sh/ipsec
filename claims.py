"""Frozen contract. Do not modify without asking — see CLAUDE.md invariant 8 (§2 of MVP_BUILD_PROMPT.md).

Every value the system holds is a Claim carrying a provenance tier. Evidence
either eliminates candidates (a hard constraint) or ranks whatever survives
(a soft prior); these never mix — see eliminate() / rank() below.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class Tier(IntEnum):
    """Provenance tiers. Ordered: higher means stronger evidence.

    NOT_OBSERVABLE is the absence of a claim, not a weak claim.
    """
    NOT_OBSERVABLE = 0
    ML_PREDICTION = 1
    INFERRED_IMPLEMENTATION_DEFAULT = 2
    INFERRED_SIDE_CHANNEL = 3
    OBSERVED = 4


class TierPromotionError(Exception):
    """Raised when a derived claim would sit above the weakest of its inputs."""


@dataclass(frozen=True)
class Claim:
    field: str                       # dotted path, e.g. "child_sa.encryption"
    value: Any                       # None iff tier is NOT_OBSERVABLE
    tier: Tier
    confidence: float                # 0.0..1.0; exactly 1.0 when tier is OBSERVED
    method: str                      # short identifier of what produced this
    evidence: tuple[int, ...]        # frame numbers, may be empty for NOT_OBSERVABLE
    caveats: tuple[str, ...] = ()
    derived_from: tuple["Claim", ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")
        if self.tier is Tier.OBSERVED and self.confidence != 1.0:
            raise ValueError("OBSERVED claims must have confidence exactly 1.0")
        if self.tier is Tier.NOT_OBSERVABLE and self.value is not None:
            raise ValueError("NOT_OBSERVABLE claims must carry no value")
        if self.derived_from:
            ceiling = min(c.tier for c in self.derived_from)
            if self.tier > ceiling:
                raise TierPromotionError(
                    f"{self.field}: tier {self.tier.name} exceeds weakest input "
                    f"{ceiling.name}"
                )


@dataclass(frozen=True)
class CandidateSet:
    universe: frozenset[str]                    # all suite ids considered
    surviving: frozenset[str]                   # those not yet eliminated
    eliminated_by: tuple[tuple[str, str], ...]  # (suite_id, human-readable derivation)
    indistinguishable: tuple[frozenset[str], ...] = ()


def eliminate(cs: CandidateSet, doomed: set[str], reason: str) -> CandidateSet:
    """Hard constraint. Removes candidates. Returns a new CandidateSet.

    Only candidates currently surviving are recorded as eliminated by this
    call; ids in `doomed` that are already gone (or never in the universe)
    are silently ignored rather than double-recorded.
    """
    newly_eliminated = cs.surviving & doomed
    new_surviving = cs.surviving - doomed
    new_eliminated_by = cs.eliminated_by + tuple(
        (suite_id, reason) for suite_id in sorted(newly_eliminated)
    )
    return CandidateSet(
        universe=cs.universe,
        surviving=new_surviving,
        eliminated_by=new_eliminated_by,
        indistinguishable=cs.indistinguishable,
    )


def rank(cs: CandidateSet, scores: dict[str, float]) -> list[tuple[str, float]]:
    """Soft prior. Returns an ORDERING over cs.surviving.

    Deliberately does NOT return a CandidateSet: ranking can never change
    membership. Scores for suites not in cs.surviving are silently dropped.
    """
    filtered = [(suite_id, score) for suite_id, score in scores.items() if suite_id in cs.surviving]
    filtered.sort(key=lambda item: item[1], reverse=True)
    return filtered

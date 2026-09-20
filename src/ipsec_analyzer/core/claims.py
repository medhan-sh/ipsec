"""Frozen contract. Do not modify without asking — see CLAUDE.md invariant 8 (§2 of MVP_BUILD_PROMPT.md).

Every value the system holds is a Claim carrying a provenance tier.

Amendment (post Phase 1 review, logged in reports/phase-1.md addendum):
CandidateSet/eliminate()/rank() moved out to core/candidates.py and this
file relocated from repo root into core/, to match ARCHITECTURE.md's
layering, which is authoritative for repository layout. No field, default,
or validation behaviour changed — organizational move only.
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


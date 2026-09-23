"""3a — granularity by GCD (MVP_BUILD_PROMPT.md Phase 3).

Deterministic. Per invariant 6: if this can't find a clean answer, that IS
the correct answer, and it is reported as NOT_OBSERVABLE — never a fallback
heuristic, never a loosened tolerance, never "closest to 4, 8, or 16".

Amendment (this pass): abstention used to be a bare `None`, discarding
*why* it abstained even though the function already knows — either there
weren't enough distinct lengths to trust a GCD at all, or a GCD was
computed but landed off the (4, 8, 16) lattice. Those two cases call for
opposite remediation advice (see `engine.py`'s `_granularity_channel`), so
`estimate_granularity` now returns a small frozen result naming which
branch fired, in a closed vocabulary validated the same way
`assessment/rules/schema.py` validates `gap_kind` and condition `op` —
an unknown branch tag is a bug caught at construction, not a typo that
silently prints "None".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

# Fewer distinct E values than this and the residues aren't sampled densely
# enough to trust a GCD estimate — includes the degenerate all-identical
# case (1 distinct value), which is why there's no separate check for it.
MIN_DISTINCT_VALUES = 8

# The only granularities any suite in constants.py actually has. A raw GCD
# landing anywhere else means the assumption behind this estimator (clean
# residue structure) doesn't hold for this flow — see tfc_gate.py.
VALID_GRANULARITIES = (4, 8, 16)

# Closed vocabulary for GranularityEstimate.branch. "resolved" is success;
# the other two are the structurally different abstention reasons this
# pass exists to distinguish.
VALID_GRANULARITY_BRANCHES = frozenset(
    {"resolved", "insufficient_distinct_values", "off_lattice_gcd"}
)


class GranularityEstimateError(ValueError):
    """Raised when a GranularityEstimate's branch tag isn't in the closed
    vocabulary — same standard as RuleValidationError in
    assessment/rules/schema.py.
    """


@dataclass(frozen=True)
class GranularityEstimate:
    """granularity is the padding granularity g, or None on abstention —
    per invariant 3, callers must not treat any other field as a value
    substitute for that None. distinct_count is always populated. raw_gcd
    is the GCD actually computed, populated only for `off_lattice_gcd`
    (the branch where the rejected number is the whole point of the
    caveat); None for `insufficient_distinct_values` (no GCD was computed
    at all) and for `resolved` (redundant with `granularity`).
    """

    granularity: int | None
    branch: str
    distinct_count: int
    raw_gcd: int | None

    def __post_init__(self) -> None:
        if self.branch not in VALID_GRANULARITY_BRANCHES:
            raise GranularityEstimateError(
                f"unknown granularity branch: {self.branch!r} (valid: {sorted(VALID_GRANULARITY_BRANCHES)})"
            )


def estimate_granularity(wire_lengths: Sequence[int]) -> GranularityEstimate:
    """Returns a GranularityEstimate. `granularity` is the padding
    granularity g, or None (NOT_OBSERVABLE) if it can't be determined
    cleanly — see `branch` for which of the two structurally different
    abstention reasons applies.
    """
    distinct = set(wire_lengths)
    distinct_count = len(distinct)
    if distinct_count < MIN_DISTINCT_VALUES:
        return GranularityEstimate(
            granularity=None,
            branch="insufficient_distinct_values",
            distinct_count=distinct_count,
            raw_gcd=None,
        )
    baseline = min(distinct)
    diffs = [value - baseline for value in distinct if value != baseline]
    g = math.gcd(*diffs)
    if g not in VALID_GRANULARITIES:
        return GranularityEstimate(
            granularity=None,
            branch="off_lattice_gcd",
            distinct_count=distinct_count,
            raw_gcd=g,
        )
    return GranularityEstimate(
        granularity=g,
        branch="resolved",
        distinct_count=distinct_count,
        raw_gcd=None,
    )

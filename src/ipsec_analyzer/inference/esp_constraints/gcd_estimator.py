"""3a — granularity by GCD (MVP_BUILD_PROMPT.md Phase 3).

Deterministic. Per invariant 6: if this can't find a clean answer, that IS
the correct answer, and it is reported as NOT_OBSERVABLE — never a fallback
heuristic, never a loosened tolerance, never "closest to 4, 8, or 16".
"""

from __future__ import annotations

import math
from typing import Sequence

# Fewer distinct E values than this and the residues aren't sampled densely
# enough to trust a GCD estimate — includes the degenerate all-identical
# case (1 distinct value), which is why there's no separate check for it.
MIN_DISTINCT_VALUES = 8

# The only granularities any suite in constants.py actually has. A raw GCD
# landing anywhere else means the assumption behind this estimator (clean
# residue structure) doesn't hold for this flow — see tfc_gate.py.
VALID_GRANULARITIES = (4, 8, 16)


def estimate_granularity(wire_lengths: Sequence[int]) -> int | None:
    """Returns the padding granularity g, or None (NOT_OBSERVABLE) if it
    can't be determined cleanly.
    """
    distinct = set(wire_lengths)
    if len(distinct) < MIN_DISTINCT_VALUES:
        return None
    baseline = min(distinct)
    diffs = [value - baseline for value in distinct if value != baseline]
    g = math.gcd(*diffs)
    if g not in VALID_GRANULARITIES:
        return None
    return g

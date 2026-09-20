"""Frozen contract. Do not modify without asking — see CLAUDE.md invariant 8 (§2 of MVP_BUILD_PROMPT.md).

Evidence either eliminates candidates (a hard, reproducible constraint) or
ranks whatever survives (a soft prior); these never mix. See eliminate() /
rank() below — the asymmetry (one returns a set, one returns a list) is the
whole point.

Split out of core/claims.py per ARCHITECTURE.md's layering (logged as an
amendment in reports/phase-1.md addendum). No behaviour changed.
"""

from __future__ import annotations

from dataclasses import dataclass


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

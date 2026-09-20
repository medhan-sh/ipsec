"""Frozen contract amendment. Do not modify without asking — see CLAUDE.md
invariant 8 (§2 of MVP_BUILD_PROMPT.md).

`ClaimLedger` — "a collection of Claims plus the CandidateSets, queryable
by dotted field path" per ARCHITECTURE.md §5's Inference→Assessment
contract, and named under `core/`'s own scope in ARCHITECTURE.md §4. No
phase through Phase 4 needed it (each inference module simply returned
its own `list[Claim]`, and tests unpacked those directly); Phase 5's
policy engine is the first consumer, since it needs to look claims up by
field name generically across whatever inference modules produced them,
rather than each caller knowing which specific list to search.

Added now rather than in Phase 0/1, on the same basis as the earlier
notify-type-constants and DH-groups amendments: this completes something
ARCHITECTURE.md always specified for `core/`, rather than changing a
decided value. No existing frozen file's content changed.
"""

from __future__ import annotations

from dataclasses import dataclass

from ipsec_analyzer.core.candidates import CandidateSet
from ipsec_analyzer.core.claims import Claim


@dataclass(frozen=True)
class ClaimLedger:
    claims: tuple[Claim, ...]
    candidate_sets: tuple[CandidateSet, ...] = ()

    def get(self, field: str) -> Claim | None:
        """The first claim for this field, or None if the ledger holds no
        claim for it at all. Callers needing every claim for a field that
        can legitimately appear more than once (e.g. `esp.granularity`
        across several Child SA tunnels in one capture) should use
        `get_all` instead — `get` alone would silently pick just one.
        """
        for claim in self.claims:
            if claim.field == field:
                return claim
        return None

    def get_all(self, field: str) -> tuple[Claim, ...]:
        return tuple(claim for claim in self.claims if claim.field == field)

    def has_field(self, field: str) -> bool:
        return any(claim.field == field for claim in self.claims)

    @staticmethod
    def from_claims(*claim_groups: "Claim | None | list[Claim] | tuple[Claim, ...]") -> "ClaimLedger":
        """Convenience builder: flattens a mix of single claims, `None`
        (skipped — several inference functions return `Claim | None`),
        and lists/tuples of claims into one ledger. Keeps call sites that
        assemble a ledger from several inference modules' outputs from
        each having to hand-write the same filtering.
        """
        flattened: list[Claim] = []
        for group in claim_groups:
            if group is None:
                continue
            if isinstance(group, Claim):
                flattened.append(group)
            else:
                flattened.extend(c for c in group if c is not None)
        return ClaimLedger(claims=tuple(flattened))

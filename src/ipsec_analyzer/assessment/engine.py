"""engine.py — rule evaluation, coverage gaps (MVP_BUILD_PROMPT.md Phase 5).

Turns the 15 rules in `rules/rules.yaml` into `Finding`s or
`CoverageGap`s by checking each rule's `target` field against a
`ClaimLedger`. Never touches a packet, a pcap path, or any `protocol/`
type — per ARCHITECTURE.md's dependency rule ("assessment imports core,
reads a ClaimLedger — it never touches packets"), this module only knows
about `core.claims`/`core.ledger` and the rules it was handed.

A rule is a **coverage gap** when the ledger has no claim for `target`, or
the claim it has is below `min_tier` — this is not "the finding didn't
fire," it's "we couldn't check." A rule that *was* checked and whose
condition came back false is a **passed check** (`PassedCheck` — amendment
below): it was assessed, and the answer was negative. `checks_assessable`
counts rules that were actually checked (at least one qualifying claim
existed, found or passed), `checks_total` is always the full rule count,
and `checks_gap` is the difference — the headline coverage number
MVP_BUILD_PROMPT.md's acceptance criteria call for.

**Amendment (Phase 6b review): `PassedCheck` added.** Previously a rule
that was assessable and whose condition came back false produced nothing
at all — no `Finding`, no `CoverageGap`, no record of any kind. A clean
capture (every check assessable, nothing wrong found) then rendered as an
empty findings table with no indication that 11 checks actually ran and
passed versus were never checkable — indistinguishable, at the report
layer, from a tool that silently did nothing. `checks_found`/
`checks_passed` split what `checks_assessable` used to report as one
number; `checks_assessable` is now a derived property (`checks_found +
checks_passed`), kept for every existing caller that already reads it.
Counted **per rule**, not per raw `Finding`/`PassedCheck` object — a rule
with several qualifying claims (e.g. two ESP tunnels) that produces even
one `Finding` counts entirely under "found" for the headline, and its
passing claims (if any) are not separately added to `passes[]`; only a
rule where *every* qualifying claim passed counts as "passed" and gets a
`PassedCheck` per such claim. This keeps `checks_found + checks_passed +
checks_gap == checks_total` exactly, matching every existing per-rule
coverage invariant — it does mean a genuinely mixed rule (one tunnel
triggers, a different tunnel of the same rule doesn't) surfaces only its
findings in the report, not a redundant "also passed for the other
tunnel" line; disclosed as a known simplification since no real capture
available to this project has produced that mix yet.

Rules 14 ("PFS") and 15 ("Anti-replay") are always coverage gaps in this
MVP: no code path anywhere in the project emits a claim for
`child_sa.pfs` or `esp.anti_replay_enabled` — the former because parsing
CREATE_CHILD_SA's KE payload is out of scope for this MVP (a real, if
temporary, gap: `gap_kind: not_implemented`), the latter because
anti-replay enforcement is a receiver-side policy decision that is *never*
signaled on the wire, regardless of how much parsing this tool ever grows
(a permanent, structural gap: `gap_kind: structurally_unobservable`).

**Amendment (Phase 5a review fix #2): this module no longer injects
claims.** An earlier version fabricated two `NOT_OBSERVABLE` Claims for
these fields and appended them to the ledger before evaluating rules —
but assessment/ reads a ClaimLedger, it does not construct Claims (per
ARCHITECTURE.md's own dependency rule, and invariant 3's spirit: a
synthetic "we looked" claim that nothing in `protocol/`/`inference/` ever
actually produced is indistinguishable, from inside the ledger, from a
claim earned by parsing evidence). The same observable result —
`actual_tier: NOT_OBSERVABLE` on the gap, matching ARCHITECTURE.md's own
findings.json sketch — is now produced by `CoverageGap` itself: its
constructor normalizes a missing claim (`actual_tier=None`) to
`Tier.NOT_OBSERVABLE`, since "no claim at all" and "an observation that
came back NOT_OBSERVABLE" are the same fact for a rule's purposes, without
requiring a fabricated Claim object to exist anywhere. Every rule's
`gap_kind` (`rules.yaml`) is what actually tells these two apart now —
`structurally_unobservable` for anti-replay, `not_implemented` for PFS —
which is a strictly more honest signal than the two claims' near-identical
caveat text ever was.
"""

from __future__ import annotations

from dataclasses import dataclass

from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.core.ledger import ClaimLedger
from ipsec_analyzer.assessment.rules.schema import Rule


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: str
    category: str
    references: tuple[str, ...]
    recommendation: str
    tier: Tier
    evidence: tuple[int, ...]
    # Phase 5a review fix #3: the narrowing claim's own evidence (frame
    # numbers), carried onto the Finding so two claims for the same field
    # (e.g. esp.granularity from two different Child SA tunnels) produce
    # two distinguishable findings instead of one Finding silently standing
    # in for both. Not a literal SPI number: core/claims.py is frozen for
    # this pass and has no SPI-scope field, and evidence (which pipeline.py
    # already assigns per-tunnel) already uniquely identifies which
    # observation a finding came from — see reports/phase-5a.md's
    # Deviations for why this wasn't threaded through as a new Claim field.
    scope: tuple[int, ...] = ()


@dataclass(frozen=True)
class PassedCheck:
    """A rule that was assessable and whose condition evaluated false for
    every qualifying claim — the check ran, and the answer was clean.
    Mirrors `Finding`'s evidence/scope/tier shape (minus severity/
    category/recommendation/references, which only make sense for
    something that needs fixing) so the report can render passes and
    findings with the same tier-badge machinery.
    """
    rule_id: str
    title: str
    tier: Tier
    evidence: tuple[int, ...]
    scope: tuple[int, ...] = ()


@dataclass(frozen=True)
class CoverageGap:
    rule_id: str
    title: str
    reason: str
    required_tier: Tier
    gap_kind: str
    actual_tier: Tier | None = None  # normalized to NOT_OBSERVABLE below when no claim existed at all

    def __post_init__(self) -> None:
        # Phase 5a review fix #2: this is now the one place "no claim
        # observed" becomes NOT_OBSERVABLE — the engine no longer injects a
        # Claim to produce this value, it's a fact about the gap itself.
        if self.actual_tier is None:
            object.__setattr__(self, "actual_tier", Tier.NOT_OBSERVABLE)


@dataclass(frozen=True)
class AssessmentResult:
    findings: tuple[Finding, ...]
    passes: tuple[PassedCheck, ...]
    gaps: tuple[CoverageGap, ...]
    checks_total: int
    checks_found: int
    checks_passed: int

    @property
    def checks_assessable(self) -> int:
        return self.checks_found + self.checks_passed

    @property
    def checks_gap(self) -> int:
        return self.checks_total - self.checks_found - self.checks_passed


def evaluate_rules(ledger: ClaimLedger, rules: list[Rule]) -> AssessmentResult:
    findings: list[Finding] = []
    passes: list[PassedCheck] = []
    gaps: list[CoverageGap] = []
    checks_found = 0
    checks_passed = 0

    for rule in rules:
        claims = ledger.get_all(rule.target)
        qualifying = [c for c in claims if c.tier >= rule.min_tier]

        if not qualifying:
            best = max(claims, key=lambda c: c.tier) if claims else None
            gaps.append(
                CoverageGap(
                    rule_id=rule.id,
                    title=rule.title,
                    reason=(
                        f"no claim observed for '{rule.target}'"
                        if best is None
                        else f"claim tier {best.tier.name} is below required {rule.min_tier.name}"
                    ),
                    required_tier=rule.min_tier,
                    gap_kind=rule.gap_kind,
                    actual_tier=best.tier if best is not None else None,
                )
            )
            continue

        # Phase 5a review fix #3: every qualifying claim gets its own
        # finding/pass check — a rule with two matching claims (e.g. two
        # ESP tunnels) can now produce zero, one, or two findings.
        rule_findings: list[Finding] = []
        rule_passes: list[PassedCheck] = []
        for claim in qualifying:
            raw_value = claim.value
            if rule.condition.field is not None and isinstance(claim.value, dict):
                raw_value = claim.value.get(rule.condition.field)
            if rule.condition.evaluate(claim.value):
                rule_findings.append(
                    Finding(
                        rule_id=rule.id,
                        title=rule.render(rule.title, raw_value),
                        severity=rule.severity,
                        category=rule.category,
                        references=rule.references,
                        recommendation=rule.render(rule.recommendation, raw_value),
                        tier=claim.tier,
                        evidence=claim.evidence,
                        scope=claim.evidence,
                    )
                )
            else:
                rule_passes.append(
                    PassedCheck(
                        rule_id=rule.id,
                        # `passed_title`, not `title` — and rendered, so a
                        # `{value}` placeholder can't leak into the report
                        # verbatim the way it previously did for
                        # `partial_downgrade_protection`.
                        title=rule.render(rule.passed_title, raw_value),
                        tier=claim.tier,
                        evidence=claim.evidence,
                        scope=claim.evidence,
                    )
                )

        # Phase 6b review: a rule counts as "found" for the headline the
        # moment any one of its qualifying claims triggers it, even if
        # another claim for the same rule (e.g. a different ESP tunnel)
        # passed — see this module's own amendment note above for why
        # that passing claim isn't separately surfaced in `passes[]`.
        if rule_findings:
            findings.extend(rule_findings)
            checks_found += 1
        else:
            passes.extend(rule_passes)
            checks_passed += 1

    return AssessmentResult(
        findings=tuple(findings),
        passes=tuple(passes),
        gaps=tuple(gaps),
        checks_total=len(rules),
        checks_found=checks_found,
        checks_passed=checks_passed,
    )

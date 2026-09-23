"""schema.py — rule dataclass + validation (MVP_BUILD_PROMPT.md Phase 5).

Rules are data, not code (MVP_BUILD_PROMPT.md §3's own reasoning for
choosing pyyaml). Conditions are therefore small structured dicts with a
fixed, closed set of operators — never a string handed to `eval()` — so a
rules.yaml author can add or edit a rule without writing Python, and this
module can validate every rule's shape before assessment/engine.py ever
runs one against real data.

Amendment beyond MVP_BUILD_PROMPT.md's literal schema list (`id`,
`target`, `min_tier`, `condition`, `severity`, `category`, `references`,
`recommendation`): `title` was added. ARCHITECTURE.md's own findings.json
sketch (§5) shows a `title` on every finding, distinct from
`recommendation`, and there's no way to produce one without it.

Amendment (report pass): `passed_title` added. `title` names the problem
("NULL encryption in use for ESP"), which is the right phrasing for a
finding and exactly the wrong one for a `PassedCheck` — the report's
largest table was a list of problem strings that all meant "fine", so a
reader skimming it saw a breach report. `passed_title` is the same rule's
*negative* phrasing ("NULL encryption ruled out for ESP"). It lives here,
beside the rule it describes, rather than as a rule_id -> phrasing map in
`output/`: that map would be a second copy of knowledge that already has
a home, free to drift out of sync with the rule it claims to describe.

Amendment (explanations pass): `explanation` added. The report's checks
grid names 15 rules in three or four words each, which tells a reader
what was checked but not what it means or why it matters. `explanation`
is the long-form, plain-language version, and it describes the **check**,
never a particular capture's result — capture-specific text already has
homes (`recommendation`, a gap's `reason`, a claim's caveats). Keeping
that boundary is what stops an explanation from becoming a finding
without a provenance tier. Authored text, marked `# VERIFY BY HAND` in
rules.yaml on the same standard as core/constants.py.

Amendment (Phase 5a review fix #2): `gap_kind` added. A coverage gap
without a reason a human can act on ("not observed" could mean "this
capture didn't have it" or "no capture ever could") is a worse artifact
than no gap at all. Every rule now says, in closed vocabulary, which kind
of gap it becomes when the ledger doesn't have what it needs:
`structurally_unobservable` (no passive observer can ever see this, e.g.
anti-replay enforcement — a receiver-side policy decision never signaled
on the wire), `not_implemented` (this MVP doesn't parse what's needed,
e.g. PFS's CREATE_CHILD_SA KE payload), or `not_observed_in_capture` (the
default — the capture just didn't contain it). Unknown values are a
`RuleValidationError` at load time, same standard as an unknown `op`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ipsec_analyzer.core.claims import Tier

VALID_OPS = frozenset({"eq", "in", "intersects"})

VALID_GAP_KINDS = frozenset({"structurally_unobservable", "not_implemented", "not_observed_in_capture"})


class RuleValidationError(ValueError):
    """Raised when rules.yaml contains a rule that doesn't match the
    schema — caught at load time, not silently ignored or defaulted, so a
    malformed rule can't be misread as "always a gap" or "never fires".
    """


@dataclass(frozen=True)
class Condition:
    op: str
    field: str | None = None  # if the claim's value is a dict, check this key instead of the whole value
    value: Any = None         # for op == "eq"
    values: tuple[Any, ...] = ()  # for op in ("in", "intersects")

    def __post_init__(self) -> None:
        if self.op not in VALID_OPS:
            raise RuleValidationError(f"unknown condition op: {self.op!r} (valid: {sorted(VALID_OPS)})")

    def evaluate(self, claim_value: Any) -> bool:
        target = claim_value
        if self.field is not None:
            if not isinstance(target, dict) or self.field not in target:
                return False
            target = target[self.field]
        if self.op == "eq":
            return target == self.value
        if self.op == "in":
            return target in self.values
        if self.op == "intersects":
            try:
                return bool(set(target) & set(self.values))
            except TypeError:
                return False
        raise RuleValidationError(f"unreachable: op {self.op!r} passed validation but has no evaluator")


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    passed_title: str   # the same rule's negative phrasing, for a PassedCheck
    explanation: str    # plain-language description of the CHECK, not of any capture
    target: str          # dotted field path into the ClaimLedger
    min_tier: Tier
    condition: Condition
    severity: str
    category: str
    references: tuple[str, ...]
    recommendation: str
    gap_kind: str
    value_labels: dict[Any, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.gap_kind not in VALID_GAP_KINDS:
            raise RuleValidationError(
                f"rule {self.id!r}: unknown gap_kind {self.gap_kind!r} (valid: {sorted(VALID_GAP_KINDS)})"
            )

    def render(self, template: str, raw_value: Any) -> str:
        """Fills a `{value}` placeholder in `title`/`passed_title`/`recommendation` with
        `raw_value` — relabeled via `value_labels` when the rule defines
        one (e.g. `partial_downgrade_protection` naming "the responder"
        instead of printing the raw enum string) — so this is generically
        available to any rule, not special-cased to one.
        """
        try:
            label = self.value_labels.get(raw_value, str(raw_value))
        except TypeError:
            # `raw_value` is unhashable, so it cannot be a `value_labels`
            # key and there is nothing to relabel. This is reachable when a
            # rule's condition has no `field` and the claim's value is a
            # collection — `truncated_96_bit_icv` targets `esp.icv_len`,
            # which carries every plausible ICV length. It holds today only
            # because that claim is built as a `tuple` (hashable) rather
            # than a `set`; nothing enforced that, so an estimator switching
            # to a set would have crashed report generation on exactly the
            # captures the rule exists to flag. Guarded rather than
            # documented as a constraint on claim authors.
            label = str(raw_value)
        try:
            return template.format(value=label)
        except (KeyError, IndexError):
            return template


_REQUIRED_KEYS = frozenset(
    {
        "id", "title", "passed_title", "explanation", "target", "min_tier", "condition",
        "severity", "category", "references", "recommendation", "gap_kind",
    }
)


def _parse_condition(raw: Any, rule_id: str) -> Condition:
    if not isinstance(raw, dict) or "op" not in raw:
        raise RuleValidationError(f"rule {rule_id!r}: condition must be a mapping with an 'op' key")
    return Condition(
        op=raw["op"],
        field=raw.get("field"),
        value=raw.get("value"),
        values=tuple(raw["values"]) if "values" in raw else (),
    )


def _parse_rule(raw: dict) -> Rule:
    missing = _REQUIRED_KEYS - set(raw)
    if missing:
        raise RuleValidationError(f"rule {raw.get('id', '<unknown>')!r} missing required keys: {sorted(missing)}")
    rule_id = raw["id"]
    try:
        min_tier = Tier[raw["min_tier"]]
    except KeyError as exc:
        raise RuleValidationError(f"rule {rule_id!r}: unknown min_tier {raw['min_tier']!r}") from exc
    return Rule(
        id=rule_id,
        title=raw["title"],
        passed_title=raw["passed_title"],
        explanation=raw["explanation"],
        target=raw["target"],
        min_tier=min_tier,
        condition=_parse_condition(raw["condition"], rule_id),
        severity=raw["severity"],
        category=raw["category"],
        references=tuple(raw["references"]),
        recommendation=raw["recommendation"],
        gap_kind=raw["gap_kind"],
        value_labels=dict(raw.get("value_labels", {})),
    )


def load_rules(path: str | Path) -> list[Rule]:
    with open(path) as f:
        raw_rules = yaml.safe_load(f)
    if not isinstance(raw_rules, list):
        raise RuleValidationError(f"{path}: expected a YAML list of rules at the top level")
    rules = [_parse_rule(raw) for raw in raw_rules]
    ids = [r.id for r in rules]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise RuleValidationError(f"{path}: duplicate rule ids: {sorted(duplicates)}")
    return rules


DEFAULT_RULES_PATH = Path(__file__).parent / "rules.yaml"


def load_default_rules() -> list[Rule]:
    return load_rules(DEFAULT_RULES_PATH)

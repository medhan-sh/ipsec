"""models.py — Data structures and parsing for findings.json (schema 1.0).

Presentation consumer layer: this module imports NOTHING project-local.
It parses plain dicts loaded from findings.json into structured dataclasses
ready for Textual widgets to render.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaptureMeta:
    filename: str
    sha256: str
    packet_count: int
    duration_s: float
    truncated: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaptureMeta:
        return cls(
            filename=str(data.get("filename", "")),
            sha256=str(data.get("sha256", "")),
            packet_count=int(data.get("packet_count", 0)),
            duration_s=float(data.get("duration_s", 0.0)),
            truncated=bool(data.get("truncated", False)),
        )


@dataclass(frozen=True)
class CoverageMeta:
    checks_total: int
    checks_found: int
    checks_passed: int
    checks_assessable: int
    checks_gap: int
    packets_skipped: int
    tshark_exit_clean: bool
    ike_sa_init_request_observed: bool
    ike_sa_init_response_observed: bool
    esp_tunnels_total: int
    esp_tunnels_missing_a_direction: int
    tshark_version: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoverageMeta:
        return cls(
            checks_total=int(data.get("checks_total", 0)),
            checks_found=int(data.get("checks_found", 0)),
            checks_passed=int(data.get("checks_passed", 0)),
            checks_assessable=int(data.get("checks_assessable", 0)),
            checks_gap=int(data.get("checks_gap", 0)),
            packets_skipped=int(data.get("packets_skipped", 0)),
            tshark_exit_clean=bool(data.get("tshark_exit_clean", False)),
            ike_sa_init_request_observed=bool(data.get("ike_sa_init_request_observed", False)),
            ike_sa_init_response_observed=bool(data.get("ike_sa_init_response_observed", False)),
            esp_tunnels_total=int(data.get("esp_tunnels_total", 0)),
            esp_tunnels_missing_a_direction=int(data.get("esp_tunnels_missing_a_direction", 0)),
            tshark_version=str(data.get("tshark_version", "unknown")),
        )


@dataclass(frozen=True)
class ClaimItem:
    field: str
    value: Any
    tier: str
    confidence: float | None
    method: str
    evidence: tuple[int, ...]
    caveats: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClaimItem:
        return cls(
            field=str(data.get("field", "")),
            value=data.get("value"),
            tier=str(data.get("tier", "NOT_OBSERVABLE")),
            confidence=float(data["confidence"]) if data.get("confidence") is not None else None,
            method=str(data.get("method", "")),
            evidence=tuple(int(x) for x in data.get("evidence", ())),
            caveats=tuple(str(x) for x in data.get("caveats", ())),
        )

    def display_value(self) -> str:
        if self.value is None:
            return "—"
        if isinstance(self.value, dict):
            name = self.value.get("name")
            tid = self.value.get("transform_id")
            klen = self.value.get("key_length")
            if name:
                extra = []
                if tid is not None:
                    extra.append(f"id {tid}")
                if klen:
                    extra.append(f"{klen}-bit")
                extra_str = f" ({', '.join(extra)})" if extra else ""
                return f"{name}{extra_str}"
            return str(self.value)
        if isinstance(self.value, (list, tuple)):
            return ", ".join(str(x) for x in self.value)
        return str(self.value)


@dataclass(frozen=True)
class CandidateSetItem:
    sa_id: str
    universe_size: int
    surviving: tuple[str, ...]
    eliminated: tuple[tuple[str, str], ...]
    indistinguishable: tuple[tuple[str, ...], ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateSetItem:
        elim = []
        for pair in data.get("eliminated", []):
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                elim.append((str(pair[0]), str(pair[1])))
        indist = []
        for group in data.get("indistinguishable", []):
            if isinstance(group, (list, tuple)):
                indist.append(tuple(str(s) for s in group))

        return cls(
            sa_id=str(data.get("sa_id", "")),
            universe_size=int(data.get("universe_size", 0)),
            surviving=tuple(str(s) for s in data.get("surviving", ())),
            eliminated=tuple(elim),
            indistinguishable=tuple(indist),
        )


@dataclass(frozen=True)
class FindingItem:
    rule_id: str
    severity: str
    category: str
    title: str
    tier: str
    evidence: tuple[int, ...]
    scope: tuple[int, ...]
    references: tuple[str, ...]
    recommendation: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FindingItem:
        return cls(
            rule_id=str(data.get("rule_id", "")),
            severity=str(data.get("severity", "INFO")),
            category=str(data.get("category", "")),
            title=str(data.get("title", "")),
            tier=str(data.get("tier", "OBSERVED")),
            evidence=tuple(int(x) for x in data.get("evidence", ())),
            scope=tuple(int(x) for x in data.get("scope", ())),
            references=tuple(str(x) for x in data.get("references", ())),
            recommendation=str(data.get("recommendation", "")),
        )


@dataclass(frozen=True)
class PassItem:
    rule_id: str
    title: str
    tier: str
    evidence: tuple[int, ...]
    scope: tuple[int, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PassItem:
        return cls(
            rule_id=str(data.get("rule_id", "")),
            title=str(data.get("title", "")),
            tier=str(data.get("tier", "OBSERVED")),
            evidence=tuple(int(x) for x in data.get("evidence", ())),
            scope=tuple(int(x) for x in data.get("scope", ())),
        )


@dataclass(frozen=True)
class GapItem:
    rule_id: str
    title: str
    reason: str
    gap_kind: str
    required_tier: str
    actual_tier: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GapItem:
        return cls(
            rule_id=str(data.get("rule_id", "")),
            title=str(data.get("title", "")),
            reason=str(data.get("reason", "")),
            gap_kind=str(data.get("gap_kind", "")),
            required_tier=str(data.get("required_tier", "OBSERVED")),
            actual_tier=str(data.get("actual_tier", "NOT_OBSERVABLE")),
        )


@dataclass(frozen=True)
class VerdictItem:
    sa_id: str
    predicate: str
    ambiguous: bool
    confidence: float
    basis_tier: str
    basis: str
    outcome: bool | None = None
    surviving_true: tuple[str, ...] = ()
    surviving_false: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerdictItem:
        return cls(
            sa_id=str(data.get("sa_id", "")),
            predicate=str(data.get("predicate", "")),
            ambiguous=bool(data.get("ambiguous", False)),
            confidence=float(data.get("confidence", 1.0)),
            basis_tier=str(data.get("basis_tier", "OBSERVED")),
            basis=str(data.get("basis", "")),
            outcome=data.get("outcome"),
            surviving_true=tuple(str(s) for s in data.get("surviving_true", ())),
            surviving_false=tuple(str(s) for s in data.get("surviving_false", ())),
        )


@dataclass(frozen=True)
class FindingsDocument:
    schema_version: str
    capture: CaptureMeta
    coverage: CoverageMeta
    claims: tuple[ClaimItem, ...] = ()
    candidate_sets: tuple[CandidateSetItem, ...] = ()
    findings: tuple[FindingItem, ...] = ()
    passes: tuple[PassItem, ...] = ()
    gaps: tuple[GapItem, ...] = ()
    verdicts: tuple[VerdictItem, ...] = ()
    raw_dict: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FindingsDocument:
        version = str(data.get("schema_version", ""))
        if version != "1.0":
            raise ValueError(f"Unsupported findings.json schema_version: '{version}' (expected '1.0')")
        return cls(
            schema_version=version,
            capture=CaptureMeta.from_dict(data.get("capture", {})),
            coverage=CoverageMeta.from_dict(data.get("coverage", {})),
            claims=tuple(ClaimItem.from_dict(c) for c in data.get("claims", [])),
            candidate_sets=tuple(CandidateSetItem.from_dict(cs) for cs in data.get("candidate_sets", [])),
            findings=tuple(FindingItem.from_dict(f) for f in data.get("findings", [])),
            passes=tuple(PassItem.from_dict(p) for p in data.get("passes", [])),
            gaps=tuple(GapItem.from_dict(g) for g in data.get("gaps", [])),
            verdicts=tuple(VerdictItem.from_dict(v) for v in data.get("verdicts", [])),
            raw_dict=data,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> FindingsDocument:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Findings file does not exist: {path}")
        try:
            content = p.read_text()
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in {path}: {exc}") from exc
        return cls.from_dict(data)

    def get_ike_sa_claims(self) -> dict[str, ClaimItem]:
        res = {}
        for c in self.claims:
            if c.field.startswith("ike_sa.") or c.field.startswith("ike.") or c.field.startswith("ike_sa_init."):
                res[c.field] = c
        return res

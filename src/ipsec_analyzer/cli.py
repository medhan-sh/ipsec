"""cli.py — ipsec-analyze: pcap -> report.html + findings.json
(MVP_BUILD_PROMPT.md Phase 6; default output paths since Phase 6c).

The composition root. This is the one file in this project allowed to
import from every layer (core, protocol, inference, assessment, output)
at once — ARCHITECTURE.md §1 ("The analyzer is a library. The CLI is one
consumer of it.") and `tests/test_import_graph.py` agree: that test only
walks files inside the tracked sub-packages, so a top-level module like
this one is structurally outside its scope, by design. Every typed object
(`Claim`, `CandidateSet`, `Finding`, `CoverageGap`, `Verdict`/
`AmbiguousVerdict`) is turned into a plain, JSON-safe dict right here, in
the one place that has all of their types in scope at once —
`output/findings.py` and `output/report.py` never see the typed objects
themselves (see their own module docstrings; `output` imports nothing
project-local at all).

No async, no streaming (CLAUDE.md): loads the whole capture, runs the
whole pipeline, writes the output files, exits.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import time
from pathlib import Path

from ipsec_analyzer.assessment.engine import CoverageGap, Finding, PassedCheck, evaluate_rules
from ipsec_analyzer.assessment.rules.schema import load_default_rules
from ipsec_analyzer.assessment.verdict import AmbiguousVerdict, Verdict, lift_verdict
from ipsec_analyzer.core.candidates import CandidateSet
from ipsec_analyzer.core.claims import Claim, Tier
from ipsec_analyzer.core.constants import (
    IKE_DH_GROUP_NAMES,
    IKE_ENCRYPTION_NAMES,
    IKE_INTEGRITY_NAMES,
    IKE_PRF_NAMES,
)
from ipsec_analyzer.core.ledger import ClaimLedger
from ipsec_analyzer.inference.pipeline import analyze_esp_tunnel, assess_notify_posture_from_capture
from ipsec_analyzer.output.findings import assemble_findings_document, write_findings_json
from ipsec_analyzer.output.report import render_report_html, write_report_html
from ipsec_analyzer.protocol.coverage import build_capture_coverage
from ipsec_analyzer.protocol.demux import EspTunnel, demux, extract_ah_detected_claim
from ipsec_analyzer.protocol.ike_parse import (
    extract_ike_sa_init_claims,
    extract_ike_version_claim,
    extract_ikev1_aggressive_mode_claim,
    parse_ike_messages,
)
from ipsec_analyzer.protocol.ingest import load_capture_with_skip_count

# ---------------------------------------------------------------------------
# Terminal progress reporting
#
# The pipeline is several seconds of silence followed by two file paths,
# which tells a watching operator nothing about what was actually
# determined. This reports each stage as it happens.
#
# The marker vocabulary is the point, not decoration. A tool whose whole
# thesis is that it distinguishes "observed" from "inferred" from "could
# not tell" must not collapse that distinction the moment it prints to a
# terminal: `ok` is reserved for something actually determined, and an
# abstention gets `skip`, never a green tick. A run where the ESP
# estimators abstain should *look* different from one where they resolve.
#
# Stdlib only (invariant 8 — no `rich`, no `colorama`). ANSI is emitted
# only to a TTY, suppressed under NO_COLOR (https://no-color.org), and the
# Unicode markers degrade to ASCII if stdout cannot encode them.
# ---------------------------------------------------------------------------

_ANSI = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "cyan": "\033[36m", "grey": "\033[90m",
}

_MARKERS_UNICODE = {"ok": "\u2713", "skip": "\u25cb", "fail": "\u2717", "warn": "\u26a0"}
_MARKERS_ASCII = {"ok": "+", "skip": "-", "fail": "x", "warn": "!"}


class _NullProgress:
    """No-op reporter. `analyze_capture` takes one of these by default so
    the pipeline stays silent when called as a library (every test does),
    without threading `if progress is not None` through the function.
    """

    def stage(self, name): pass
    def ok(self, label, detail="", note="", truncate=True): pass
    def skip(self, label, detail="", note="", truncate=True): pass
    def fail(self, label, detail="", note="", truncate=True): pass
    def warn(self, label, detail="", note="", truncate=True): pass
    def header(self, capture): pass
    def summary(self, text): pass


class TerminalProgress:
    """Writes the run to a stream as it happens.

    Laid out after `docker compose up --build`: a bracketed header, a
    marker column, and elapsed time right-aligned against the terminal
    width. The one deliberate departure is the marker vocabulary — Compose
    only ever has to say "done" or "failed", while this tool's whole
    thesis is a third outcome, so an abstention gets its own marker and
    never borrows the success tick.
    """

    _LABEL_WIDTH = 18
    _MIN_WIDTH, _MAX_WIDTH = 80, 110

    def __init__(self, stream=None, color=None, width=None):
        self._stream = stream if stream is not None else sys.stdout
        if color is None:
            color = bool(
                getattr(self._stream, "isatty", lambda: False)()
                and not os.environ.get("NO_COLOR")
            )
        self._color = color
        self._markers = _MARKERS_UNICODE if self._can_encode_unicode() else _MARKERS_ASCII
        self._width = width or self._detect_width()
        self._started = time.perf_counter()
        self._marked = self._started
        self._stages = 0

    def _detect_width(self):
        try:
            columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        except OSError:
            columns = 80
        return max(self._MIN_WIDTH, min(self._MAX_WIDTH, columns))

    def _can_encode_unicode(self):
        encoding = getattr(self._stream, "encoding", None) or "ascii"
        try:
            "".join(_MARKERS_UNICODE.values()).encode(encoding)
        except (UnicodeEncodeError, LookupError):
            return False
        return True

    def _paint(self, text, *names):
        if not self._color or not text:
            return text
        return "".join(_ANSI[n] for n in names) + text + _ANSI["reset"]

    def _write(self, line=""):
        self._stream.write(line + "\n")
        self._stream.flush()

    def _lap(self):
        """Seconds since the previous row — the duration of the work that
        produced this line, which is what Compose shows per step.
        """
        now = time.perf_counter()
        elapsed, self._marked = now - self._marked, now
        return elapsed

    def _right_align(self, left_plain, left_painted, right):
        """Pads using the *unpainted* width: ANSI escapes take no columns
        on screen but do count in len(), so measuring the painted string
        would push every timed row out of alignment exactly when colour is
        on — i.e. always, in a demo.
        """
        if not right:
            return left_painted
        pad = max(1, self._width - len(left_plain) - len(right))
        return left_painted + " " * pad + self._paint(right, "grey")

    def _row(self, kind, color, label, detail, note, truncate=True):
        if truncate and detail and len(detail) > self._width - self._LABEL_WIDTH - 16:
            detail = detail[: self._width - self._LABEL_WIDTH - 17].rstrip() + "\u2026"
        body = label if not detail else f"{label.ljust(self._LABEL_WIDTH)}  {detail}"
        if note:
            body_plain = f"{body}  {note}"
            body = f"{body}  {self._paint(note, 'grey')}"
        else:
            body_plain = body
        marker = self._markers[kind]
        left_plain = f"   {marker}  {body_plain}"
        left_painted = f"   {self._paint(marker, color)}  {body}"
        self._write(self._right_align(left_plain, left_painted, f"{self._lap():.1f}s"))

    def header(self, capture):
        self._write()
        self._write(
            f"{self._paint('[+]', 'bold', 'blue')} "
            f"{self._paint('Analysing', 'bold')} {self._paint(capture, 'cyan')}"
        )
        self._marked = time.perf_counter()

    def stage(self, name):
        self._stages += 1
        self._write(f" {self._paint(name, 'bold')}")

    def ok(self, label, detail="", note="", truncate=True):
        self._row("ok", "green", label, detail, note, truncate)

    def skip(self, label, detail="", note="", truncate=True):
        # An honest abstention. Deliberately not the success marker:
        # nothing was determined, and the terminal should say so as
        # plainly as the report does.
        self._row("skip", "grey", label, detail, note, truncate)

    def fail(self, label, detail="", note="", truncate=True):
        self._row("fail", "red", label, detail, note, truncate)

    def warn(self, label, detail="", note="", truncate=True):
        self._row("warn", "yellow", label, detail, note, truncate)

    def summary(self, text):
        total = time.perf_counter() - self._started
        left_plain = f"[+] Finished {self._stages} stages \u00b7 {text}"
        left_painted = (
            f"{self._paint('[+]', 'bold', 'blue')} "
            f"{self._paint(f'Finished {self._stages} stages', 'bold')} "
            f"\u00b7 {self._paint(text, 'bold')}"
        )
        self._write()
        self._write(self._right_align(left_plain, left_painted, f"{total:.1f}s"))
        self._write()


_VERDICT_PREDICATES = ("confidentiality_acceptable", "integrity_acceptable")

# Item 3 of the Phase 6b review: findings.json/the report must never show
# a bare IANA transform ID alone. Resolved here, not in ike_parse.py (the
# underlying Claim's value shape stays untouched — this only enriches the
# serialized document) and not in output/ (which may import nothing
# project-local, including these tables — see core/constants.py).
_TRANSFORM_NAME_TABLES: dict[str, dict[int, str]] = {
    "ike_sa.encryption": IKE_ENCRYPTION_NAMES,
    "ike_sa.prf": IKE_PRF_NAMES,
    "ike_sa.integrity": IKE_INTEGRITY_NAMES,
    "ike_sa.dh_group": IKE_DH_GROUP_NAMES,
}


def _json_safe(value):
    """Claim.value can be a plain scalar, a dict (e.g. {"transform_id":
    20, "key_length": 256}), or a tuple (e.g. esp.icv_len's `(12, 16)`) —
    json.dump chokes on a bare tuple, so this recursively normalizes
    tuples to lists. Never invents or drops a value, only changes the
    container type.
    """
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def _resolve_transform_name(field: str, value):
    """None unless `field` is one of the four IANA-transform-ID-bearing
    `ike_sa.*` fields. `ike_sa.encryption`'s value is already a dict
    (`{"transform_id", "key_length"}`) — this adds `"name"` alongside
    what's there. The other three are bare ints in the underlying Claim
    (untouched, per this function's own scope) — this wraps them into the
    same `{"transform_id", "name"}` shape for a consistent serialized
    representation. An id with no table entry resolves to an explicit
    `"UNKNOWN(<id>)"`, never a guess or a `KeyError`.
    """
    table = _TRANSFORM_NAME_TABLES.get(field)
    if table is None or value is None:
        return value
    transform_id = value.get("transform_id") if isinstance(value, dict) else value
    name = table.get(transform_id, f"UNKNOWN({transform_id})")
    if isinstance(value, dict):
        return {**value, "name": name}
    return {"transform_id": transform_id, "name": name}


def _claim_to_dict(claim: Claim) -> dict:
    value = _resolve_transform_name(claim.field, _json_safe(claim.value))
    return {
        "field": claim.field,
        "value": value,
        "tier": claim.tier.name,
        # Phase 6b review fix: NOT_OBSERVABLE claims previously serialized
        # confidence as the dataclass's own 0.0 — a tier that carries no
        # value (invariant 3) shouldn't carry a confidence number either.
        "confidence": None if claim.tier is Tier.NOT_OBSERVABLE else claim.confidence,
        "method": claim.method,
        "evidence": list(claim.evidence),
        "caveats": list(claim.caveats),
    }


def _candidate_set_to_dict(sa_id: str, cs: CandidateSet) -> dict:
    return {
        "sa_id": sa_id,
        "universe_size": len(cs.universe),
        "surviving": sorted(cs.surviving),
        "eliminated": [[suite_id, reason] for suite_id, reason in cs.eliminated_by],
        "indistinguishable": [sorted(group) for group in cs.indistinguishable],
    }


def _finding_to_dict(finding: Finding) -> dict:
    # Amendment (Phase 6a closeout review): ARCHITECTURE.md §5's sketch
    # names a `detail` key distinct from `title`/`recommendation`; this
    # MVP's rule schema (rules.yaml) has no separate narrative-detail text
    # beyond those two, and a version of this function that set
    # `detail = finding.title` shipped in Phase 6 before this review
    # caught it — a schema field with no independent value doesn't belong
    # in a document ARCHITECTURE.md calls to be frozen at "1.0". Dropped
    # rather than kept as a disclosed duplicate; see reports/phase-6a.md's
    # Deviations.
    return {
        "rule_id": finding.rule_id,
        "severity": finding.severity,
        "category": finding.category,
        "title": finding.title,
        "tier": finding.tier.name,
        "evidence": list(finding.evidence),
        "scope": list(finding.scope),
        "references": list(finding.references),
        "recommendation": finding.recommendation,
    }


def _pass_to_dict(passed: PassedCheck) -> dict:
    return {
        "rule_id": passed.rule_id,
        "title": passed.title,
        "tier": passed.tier.name,
        "evidence": list(passed.evidence),
        "scope": list(passed.scope),
    }


def _gap_to_dict(gap: CoverageGap) -> dict:
    return {
        "rule_id": gap.rule_id,
        "title": gap.title,
        "reason": gap.reason,
        "gap_kind": gap.gap_kind,
        "required_tier": gap.required_tier.name,
        "actual_tier": gap.actual_tier.name,
    }


def _verdict_to_dict(sa_id: str, verdict: Verdict | AmbiguousVerdict) -> dict:
    if isinstance(verdict, Verdict):
        return {
            "sa_id": sa_id,
            "predicate": verdict.predicate,
            "ambiguous": False,
            "outcome": verdict.outcome,
            "confidence": verdict.confidence,
            "basis_tier": verdict.basis_tier.name,
            "basis": verdict.basis,
        }
    return {
        "sa_id": sa_id,
        "predicate": verdict.predicate,
        "ambiguous": True,
        "surviving_true": sorted(verdict.surviving_true),
        "surviving_false": sorted(verdict.surviving_false),
        # Phase 6b review fix: these were previously only emitted for the
        # unanimous (Verdict) branch — every ambiguous verdict silently
        # dropped both fields, though the Phase 6 report claimed
        # basis_tier was present on "every verdict".
        "confidence": verdict.confidence,
        "basis_tier": verdict.basis_tier.name,
        "basis": verdict.basis,
    }


def _sa_id_for_tunnel(tunnel: EspTunnel) -> str:
    if tunnel.spi_b is None:
        return f"spi:0x{tunnel.spi_a:08x}"
    return f"spi:0x{tunnel.spi_a:08x}+0x{tunnel.spi_b:08x}"


def analyze_capture(pcap_path: str, progress=None) -> dict:
    """Runs the whole pipeline against one capture and returns the
    findings document as a plain dict (ARCHITECTURE.md §5's schema,
    "1.0"). The one function that touches every layer — everything below
    it is a pure translation of already-built pipeline pieces
    (`inference/pipeline.py`, `assessment/engine.py`, `assessment/
    verdict.py`) into plain data.

    `progress` is an optional reporter (see TerminalProgress). It defaults
    to a no-op, so calling this as a library — which every test does —
    prints nothing and the return value is unaffected either way.
    """
    progress = progress or _NullProgress()
    progress.header(Path(pcap_path).name)

    sha256 = hashlib.sha256(Path(pcap_path).read_bytes()).hexdigest()

    progress.stage("ingest")
    records, skipped = load_capture_with_skip_count(pcap_path)
    progress.ok("packets read", f"{len(records) + skipped}",
                f"{skipped} skipped" if skipped else "")
    progress.ok("sha256", f"{sha256[:16]}\u2026")

    progress.stage("demux")
    demux_result = demux(records)
    progress.ok("protocols", f"{len(demux_result.ike_frames)} IKE \u00b7 "
                             f"{len(demux_result.esp_records)} ESP \u00b7 "
                             f"{len(demux_result.ah_frames)} AH")
    tunnels = list(demux_result.esp_tunnels())
    if tunnels:
        progress.ok("ESP tunnels", f"{len(tunnels)}")
    else:
        progress.skip("ESP tunnels", "none \u2014 no ESP traffic")

    progress.stage("dissect")
    parsed = parse_ike_messages(pcap_path)
    coverage = build_capture_coverage(len(records) + skipped, skipped, demux_result, parsed)
    progress.ok("tshark", coverage.tshark_version)
    if parsed.messages:
        both = coverage.ike_sa_init_request_observed and coverage.ike_sa_init_response_observed
        progress.ok("IKE messages", f"{len(parsed.messages)}",
                    "IKE_SA_INIT complete" if both else "IKE_SA_INIT incomplete")
    else:
        progress.skip("IKE messages", "none \u2014 no IKE traffic")

    progress.stage("infer")
    claims: list[Claim] = []
    ike_sa_claims = extract_ike_sa_init_claims(parsed)
    claims.extend(ike_sa_claims)
    if ike_sa_claims:
        named = {c.field: _resolve_transform_name(c.field, c.value) for c in ike_sa_claims}
        parts = [
            (named.get(f) or {}).get("name")
            for f in ("ike_sa.encryption", "ike_sa.integrity", "ike_sa.dh_group")
        ]
        progress.ok("IKE SA", " \u00b7 ".join(p for p in parts if p))
    else:
        progress.skip("IKE SA", "not observed \u2014 no IKE_SA_INIT")
    for claim in (extract_ike_version_claim(parsed), extract_ikev1_aggressive_mode_claim(parsed)):
        if claim is not None:
            claims.append(claim)
    # Phase 6b review fix: always a Claim now (True or False), never None
    # — demux() always runs, so "no AH seen" is itself an observation.
    claims.append(extract_ah_detected_claim(demux_result))

    notify_claims = assess_notify_posture_from_capture(parsed)
    if notify_claims is not None:
        claims.extend(notify_claims)
        state = next((c.value for c in notify_claims
                      if c.field == "ike_sa_init.downgrade_protection_state"), None)
        progress.ok("notify posture", f"downgrade protection {state}")
    else:
        progress.skip("notify posture", "not determinable \u2014 IKE_SA_INIT incomplete")

    candidate_set_dicts: list[dict] = []
    verdict_dicts: list[dict] = []
    # Per-tunnel outcomes are aggregated and reported after the loop —
    # four tunnels that all reached the same conclusion should read as one
    # line carrying x4, the same way the report collapses them.
    esp_outcomes: dict[str, list[str]] = {}
    for tunnel in demux_result.esp_tunnels():
        sa_id = _sa_id_for_tunnel(tunnel)
        esp_result = analyze_esp_tunnel(tunnel)
        claims.append(esp_result.granularity_claim)
        if esp_result.icv_claim is not None:
            claims.append(esp_result.icv_claim)
        if esp_result.null_encryption_claim is not None:
            claims.append(esp_result.null_encryption_claim)

        candidate_set_dicts.append(_candidate_set_to_dict(sa_id, esp_result.candidate_set))

        granularity = esp_result.granularity_claim
        if granularity.tier is Tier.NOT_OBSERVABLE:
            reason = granularity.caveats[0] if granularity.caveats else "not determinable"
            esp_outcomes.setdefault(f"abstain::{reason}", []).append(sa_id)
        else:
            esp_outcomes.setdefault(f"resolved::{granularity.value}", []).append(sa_id)
        surviving = len(esp_result.candidate_set.surviving)
        universe = len(esp_result.candidate_set.universe)
        esp_outcomes.setdefault(f"narrow::{surviving}/{universe}", []).append(sa_id)

        narrowing_tiers = [
            c.tier
            for c in (esp_result.granularity_claim, esp_result.icv_claim, esp_result.null_encryption_claim)
            if c is not None and c.tier is not Tier.NOT_OBSERVABLE
        ]
        for predicate_name in _VERDICT_PREDICATES:
            verdict = lift_verdict(esp_result.candidate_set, predicate_name, narrowing_tiers=narrowing_tiers)
            if verdict is not None:
                verdict_dicts.append(_verdict_to_dict(sa_id, verdict))

    for key, sa_ids in esp_outcomes.items():
        kind, _, value = key.partition("::")
        times = f"\u00d7{len(sa_ids)}" if len(sa_ids) > 1 else ""
        if kind == "abstain":
            progress.skip("ESP granularity", value, times)
        elif kind == "resolved":
            progress.ok("ESP granularity", f"{value}-byte alignment", times)
        else:
            progress.ok("ESP candidates", f"{value} suites survive", times)

    progress.stage("assess")
    ledger = ClaimLedger.from_claims(claims)
    rules = load_default_rules()
    assessment_result = evaluate_rules(ledger, rules)
    for finding in assessment_result.findings:
        progress.fail(finding.severity, finding.title)
    progress.ok("rules evaluated",
                f"{assessment_result.checks_total} \u00b7 "
                f"{assessment_result.checks_found} found \u00b7 "
                f"{assessment_result.checks_passed} passed \u00b7 "
                f"{assessment_result.checks_gap} not assessable")
    for gap_kind, label in (("not_observed_in_capture", "a different capture could close"),):
        count = sum(1 for g in assessment_result.gaps if g.gap_kind == gap_kind)
        if count:
            progress.warn("coverage", f"{count} gap{'' if count == 1 else 's'} {label}")

    if verdict_dicts:
        progress.stage("verdicts")
        seen: dict[tuple, int] = {}
        for verdict in verdict_dicts:
            key = (
                verdict["predicate"], verdict.get("ambiguous"), verdict.get("outcome"),
                len(verdict.get("surviving_true", [])), len(verdict.get("surviving_false", [])),
            )
            seen[key] = seen.get(key, 0) + 1
        for (predicate, ambiguous, outcome, n_true, n_false), count in seen.items():
            times = f"\u00d7{count}" if count > 1 else ""
            if ambiguous:
                progress.skip(predicate, f"undecided \u2014 {n_true} acceptable / {n_false} not", times)
            else:
                progress.ok(predicate, str(outcome), times)

    # "Truncated" is a fact about whether the capture *file* was cut
    # short (tshark's own exit code, an ingest-level skip, or a message
    # observed but not fully captured within its own frame — the two
    # shapes Phase 4 found) — deliberately not "IKE_SA_INIT wasn't
    # observed" or "no ESP traffic exists," which are legitimate,
    # non-truncated capture shapes (an IKE-handshake-only vector, a
    # mid-session start) already visible in `coverage` on their own.
    truncated = not parsed.tshark_exit_clean or skipped > 0 or any(not m.is_fully_captured for m in parsed.messages)

    packet_count = len(records) + skipped
    duration_s = round(max(r.ts for r in records) - min(r.ts for r in records), 3) if records else 0.0

    return assemble_findings_document(
        capture={
            "filename": Path(pcap_path).name,
            "sha256": sha256,
            "packet_count": packet_count,
            "duration_s": duration_s,
            "truncated": truncated,
        },
        coverage={
            "checks_total": assessment_result.checks_total,
            # checks_found/checks_passed (Phase 6b): the headline split
            # this pass added — checks_found + checks_passed + checks_gap
            # == checks_total always. checks_assessable kept alongside as
            # their sum, for anything still reading the older field.
            "checks_found": assessment_result.checks_found,
            "checks_passed": assessment_result.checks_passed,
            "checks_assessable": assessment_result.checks_assessable,
            "checks_gap": assessment_result.checks_gap,
            "packets_skipped": coverage.packets_skipped,
            "tshark_exit_clean": coverage.tshark_exit_clean,
            "ike_sa_init_request_observed": coverage.ike_sa_init_request_observed,
            "ike_sa_init_response_observed": coverage.ike_sa_init_response_observed,
            "esp_tunnels_total": coverage.esp_tunnels_total,
            "esp_tunnels_missing_a_direction": coverage.esp_tunnels_missing_a_direction,
            # Phase 6c: which dissector actually produced these
            # observations — load-bearing for this project specifically,
            # since tshark's -T json output shape has already caused one
            # real bug (Phase 4's Bug 1) that only version pinning caught.
            "tshark_version": coverage.tshark_version,
        },
        claims=[_claim_to_dict(c) for c in ledger.claims],
        candidate_sets=candidate_set_dicts,
        findings=[_finding_to_dict(f) for f in assessment_result.findings],
        passes=[_pass_to_dict(p) for p in assessment_result.passes],
        gaps=[_gap_to_dict(g) for g in assessment_result.gaps],
        verdicts=verdict_dicts,
        # The rule catalogue, keyed by id: per-rule text that does not
        # vary with the capture. Carried once at the top level rather than
        # copied onto every finding/pass/gap that cites the rule — see
        # output/findings.py's own amendment note.
        rules={rule.id: _rule_to_dict(rule) for rule in rules},
    )


def _rule_to_dict(rule) -> dict:
    """The capture-independent half of a rule: what the check means, and
    what it cites. Deliberately excludes `condition`/`target`/`min_tier` —
    those describe how the engine evaluates the rule, not what a reader
    needs, and putting the machinery in the document would invite a
    consumer to reimplement evaluation from it.
    """
    return {
        "title": rule.title,
        "passed_title": rule.passed_title,
        "explanation": rule.explanation,
        "severity": rule.severity,
        "category": rule.category,
        "references": list(rule.references),
        "recommendation": rule.recommendation,
        "gap_kind": rule.gap_kind,
    }


def _default_sibling_path(capture: str, suffix: str) -> str:
    """`captures/x.pcap` + `.report.html` -> `captures/x.report.html` —
    strips the capture's own extension (whatever it is: .pcap, .pcapng,
    none) and writes beside it, not into the current directory. Phase 6c:
    half the command's length used to be spelling out `-o`/`--json`
    explicitly for exactly this path.
    """
    capture_path = Path(capture)
    stem = capture_path.with_suffix("").name
    return str(capture_path.parent / f"{stem}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ipsec-analyze",
        description="Passive, non-decrypting security assessment of an IPsec (IKEv2/ESP) packet capture.",
    )
    parser.add_argument("capture", help="Path to a pcap/pcapng file")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Path to write the HTML report (default: <capture-basename>.report.html next to the capture)",
    )
    parser.add_argument(
        "--json", dest="json_path", default=None,
        help="Path to write the findings JSON document (default: <capture-basename>.findings.json next to the capture)",
    )
    args = parser.parse_args(argv)

    report_path = args.output or _default_sibling_path(args.capture, ".report.html")
    json_path = args.json_path or _default_sibling_path(args.capture, ".findings.json")

    progress = TerminalProgress()
    document = analyze_capture(args.capture, progress=progress)

    progress.stage("output")
    write_report_html(render_report_html(document), report_path)
    progress.ok("report", report_path, truncate=False)
    write_findings_json(document, json_path)
    progress.ok("findings", json_path, truncate=False)

    coverage = document["coverage"]
    found = coverage["checks_found"]
    headline = (
        f"{found} policy violation{'' if found == 1 else 's'} found"
        if found else "no policy violations found"
    )
    progress.summary(
        f"{headline} \u00b7 {coverage['checks_assessable']} of {coverage['checks_total']} checks assessable"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

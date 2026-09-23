"""report.py — the findings document (a plain dict) -> one self-contained
HTML file (MVP_BUILD_PROMPT.md Phase 6).

Zero project imports, same reasoning as findings.py's module docstring:
this module only ever sees the plain dict `findings.py` assembled, never a
`Claim`/`Finding`/`CandidateSet` directly. `jinja2` (approved,
MVP_BUILD_PROMPT.md §3 / ARCHITECTURE.md §2) renders
`templates/report.html.j2` with everything — CSS and JS included — inlined
into one HTML document. The template loads no CDN `<script src=...>` or
`<link href=...>`, and this module fetches nothing over the network
itself, so "opens standalone in a browser with no network access" holds by
construction (see `tests/output/test_report.py`).

Amendment (report pass): this module now builds a **view model** rather
than handing the raw document to the template. The document is the
authoritative record and stays exactly as `findings.py` assembled it; the
view model is the same information *grouped for reading*. Three groupings
matter, and all three are lossless:

- Identical ESP tunnels collapse to one block. A capture with four tunnels
  that narrowed to the same surviving set previously rendered the same
  42-name list four times, plus its indistinguishability partition four
  times, plus two verdicts per tunnel — the same 42-element universe
  enumerated 16 times over. The tunnels' *evidence* differs and is kept.
- Identical claims across tunnels collapse to one row carrying `xN`.
- Passed checks group per rule, so the section heading can no longer
  disagree with the coverage headline (`checks_passed` counts rules;
  `passes[]` carries one entry per qualifying claim, so a 4-tunnel capture
  previously headed an 11-passed report with "Checks passed (14)").

Amendment (report pass): the template now carries a small inline
`<script>`. Phase 6 refused JS on the reasoning that `<details>` covers
every collapsible need, which was true of what the report did then. It no
longer is: a provenance filter that dims the whole document, two-way
frame<->claim highlighting and copy/download affordances have no
no-JS equivalent. The acceptance criterion was always *no network access*,
not *no script* — so the script is inline, additive, and the document
renders complete and readable without it (every value is in the HTML; JS
only filters and highlights what is already there). See reports/phase-6e.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import jinja2

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "report.html.j2"

# Weakest-to-strongest, matching core.claims.Tier's five member names.
# Duplicated as plain strings rather than imported (see module docstring —
# this module imports nothing project-local); Tier's member names are a
# frozen contract (core/claims.py), and tests/test_tier_sync.py fails if
# this list ever drifts out of sync with the enum.
TIER_ORDER = [
    "NOT_OBSERVABLE",
    "ML_PREDICTION",
    "INFERRED_IMPLEMENTATION_DEFAULT",
    "INFERRED_SIDE_CHANNEL",
    "OBSERVED",
]

TIER_COLORS = {
    "NOT_OBSERVABLE": "#9aa0a6",
    "ML_PREDICTION": "#e8878b",
    "INFERRED_IMPLEMENTATION_DEFAULT": "#f2b84b",
    "INFERRED_SIDE_CHANNEL": "#e0c341",
    "OBSERVED": "#5fb87a",
}

# Short, human phrasing for the tier badges. The enum name is still
# rendered beside it (and is what the filter matches on) — this is the
# reading aid, not a replacement.
TIER_LABELS = {
    "NOT_OBSERVABLE": "not observable",
    "ML_PREDICTION": "model prediction",
    "INFERRED_IMPLEMENTATION_DEFAULT": "implementation default",
    "INFERRED_SIDE_CHANNEL": "side channel",
    "OBSERVED": "observed",
}

# VERIFY BY HAND — plain-language explanations of the provenance lattice,
# the single idea this whole project is built around. They sit beside
# TIER_LABELS for the same reason TIER_ORDER does: `output/` imports
# nothing project-local, and tests/test_tier_sync.py fails if this dict
# ever drifts from core.claims.Tier's members.
TIER_EXPLANATIONS = {
    "OBSERVED": (
        "Read straight off the wire from a field the protocol sends in the clear, "
        "dissected by tshark. There is no inference step and nothing to second-guess: "
        "either the field was there and said this, or it wasn't. Confidence at this "
        "tier is always exactly 1.0 — if something isn't certain, it isn't observed."
    ),
    "INFERRED_SIDE_CHANNEL": (
        "Worked out from things the encryption cannot hide — chiefly the sizes of "
        "packets, and the timing between them. The arithmetic itself is exact, but it "
        "rests on identifying which packets to measure, and that identification is a "
        "well-reasoned judgement rather than a protocol guarantee. Anything of that "
        "kind is written into the claim's own caveat, so you can see what the result "
        "is conditional on."
    ),
    "INFERRED_IMPLEMENTATION_DEFAULT": (
        "Assumed from what a particular vendor's stack normally does, once that vendor "
        "has been identified. Defined in the lattice for a later phase; no code path in "
        "this build produces a claim at this tier. Note the deliberate ordering — it "
        "sits below side-channel inference, because a measurement of this connection "
        "beats an assumption about connections in general."
    ),
    "ML_PREDICTION": (
        "The output of a statistical model. Defined in the lattice for a later phase; "
        "this build ships no classifier and never produces a claim at this tier. It is "
        "the weakest tier that carries a value at all, and by design a model may only "
        "ever rank possibilities that the deterministic engines have already admitted — "
        "it can never reintroduce one that arithmetic ruled out."
    ),
    "NOT_OBSERVABLE": (
        "Not a weak claim — the absence of one. Either nothing on the wire could ever "
        "answer this question, or this particular capture didn't contain enough to "
        "answer it. Claims at this tier carry no value at all, which is enforced in "
        "code rather than left to discipline. This is the tier that exists so the tool "
        "can say \"I don't know\" instead of guessing."
    ),
}

GAP_KIND_EXPLANATIONS = {
    "not_observed_in_capture": (
        "The check works and the method exists — this capture just didn't carry enough "
        "signal to run it. Nothing is being claimed about whether the underlying "
        "problem is present or absent; it simply wasn't determinable here. A different "
        "capture of the same tunnel could well answer it."
    ),
    "not_implemented": (
        "The information is there on the wire, and a passive observer could read it. "
        "This build doesn't parse what it would take. That makes this a limitation of "
        "the tool and a roadmap item — not a fact about IPsec, and not a fact about "
        "your deployment."
    ),
    "structurally_unobservable": (
        "No passive observer can ever determine this — not this tool, not a better "
        "tool, not with a longer capture. The information never appears on the wire in "
        "any form. Any product that reports a value here is guessing, and this gap "
        "will never close; it has to be verified against the endpoints' own "
        "configuration instead."
    ),
}


SEVERITY_COLORS = {
    "HIGH": "#c5221f",
    "MEDIUM": "#e37400",
    "LOW": "#1a73e8",
    "INFO": "#5f6368",
}

GAP_KIND_LABELS = {
    "structurally_unobservable": "never observable from any passive capture",
    "not_implemented": "not parsed by this MVP",
    # Phase 6b review: "not present" asserts absence; the honest claim is
    # ignorance, not a negative observation (rules 8/9 gap this way when
    # granularity/ICV weren't recovered, which says nothing about whether
    # the underlying property is actually present or absent on the wire).
    "not_observed_in_capture": "not observed in this capture",
}

# Grouping order and framing for the coverage-gap section. Three gaps that
# all render as "not assessable" are three completely different messages
# to a reader: re-capture and you'd know / we haven't built it / nobody
# can ever know. Ordered most-actionable first.
GAP_KIND_GROUPS = [
    {
        "kind": "not_observed_in_capture",
        "heading": "Not determinable from this capture",
        "lede": "The method exists and works. This capture did not carry enough signal to run it. "
                "A different capture of the same tunnel could answer these.",
        "color": "#6b7280",
    },
    {
        "kind": "not_implemented",
        "heading": "Not implemented in this build",
        "lede": "Observable in principle; this MVP does not parse what it would take. "
                "A roadmap item, not a limit of passive analysis.",
        "color": "#7c5cbf",
    },
    {
        "kind": "structurally_unobservable",
        "heading": "Never observable, passively, by anyone",
        "lede": "Not a limitation of this tool. No passive observer can determine these, "
                "and any tool that reports them is guessing.",
        "color": "#4b5563",
    },
]


def _frame_ranges(frames: Sequence[int], limit: int = 6) -> str:
    """"1, 2, 3, 4, 5, 10, 11, 32" -> "1-5, 10-11, 32". A claim citing 68
    frames previously rendered 68 inline links; the count plus a range
    summary says the same thing in one line, and the full list is still
    one click away.
    """
    ordered = sorted(set(frames))
    if not ordered:
        return ""
    runs: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        runs.append((start, previous))
        start = previous = value
    runs.append((start, previous))
    parts = [str(lo) if lo == hi else f"{lo}-{hi}" for lo, hi in runs]
    if len(parts) > limit:
        return ", ".join(parts[:limit]) + ", ..."
    return ", ".join(parts)


def _json_key(value: Any) -> str:
    """A stable, order-independent identity for grouping. `sort_keys`
    matters: two dicts equal in content but built in different orders must
    group together, and the rendered output must not depend on which one
    the pipeline happened to produce first.
    """
    return json.dumps(value, sort_keys=True, default=str)


def _tier_summary(document: dict) -> list[dict]:
    """All five tiers, always — including the two this MVP never emits.
    The lattice is the product, and a tier showing 0 is a fact about the
    capture (and about this build) worth stating rather than hiding.
    """
    counts: dict[str, int] = {tier: 0 for tier in TIER_ORDER}
    for claim in document.get("claims", []):
        tier = claim.get("tier")
        if tier in counts:
            counts[tier] += 1
    return [
        {
            "tier": tier,
            "label": TIER_LABELS[tier],
            "color": TIER_COLORS[tier],
            "count": counts[tier],
            "explanation": TIER_EXPLANATIONS[tier],
        }
        # strongest first: what a reader should trust most, first.
        for tier in reversed(TIER_ORDER)
    ]


def _group_claims(document: dict) -> list[dict]:
    """Claims identical in everything but evidence collapse to one row.
    Grouping deliberately includes `caveats`: two `esp.granularity`
    abstentions that saw different distinct-length counts carry different
    caveats and must stay separate rows, because they are different
    observations that happen to share an outcome.
    """
    groups: dict[str, dict] = {}
    for claim in document.get("claims", []):
        key = _json_key(
            {
                "field": claim.get("field"),
                "value": claim.get("value"),
                "tier": claim.get("tier"),
                "confidence": claim.get("confidence"),
                "method": claim.get("method"),
                "caveats": claim.get("caveats", []),
            }
        )
        existing = groups.get(key)
        if existing is None:
            groups[key] = {
                "claim": claim,
                "occurrences": 1,
                "evidence": list(claim.get("evidence", [])),
            }
        else:
            existing["occurrences"] += 1
            existing["evidence"].extend(claim.get("evidence", []))
    rows = []
    for group in groups.values():
        frames = sorted(set(group["evidence"]))
        rows.append(
            {
                "claim": group["claim"],
                "occurrences": group["occurrences"],
                "evidence": frames,
                "frame_ranges": _frame_ranges(frames),
                "tier": group["claim"].get("tier"),
                "tier_label": TIER_LABELS.get(group["claim"].get("tier"), ""),
                "tier_color": TIER_COLORS.get(group["claim"].get("tier"), "#9aa0a6"),
                "json": json.dumps(group["claim"], indent=2, sort_keys=True, default=str),
            }
        )
    return rows


def _group_passes(document: dict) -> list[dict]:
    """One row per rule, not per qualifying claim — `checks_passed` counts
    rules, so a per-claim list makes the section heading contradict the
    coverage headline on any multi-tunnel capture.
    """
    groups: dict[str, dict] = {}
    for passed in document.get("passes", []):
        rule_id = passed.get("rule_id")
        existing = groups.get(rule_id)
        if existing is None:
            groups[rule_id] = {
                "rule_id": rule_id,
                "title": passed.get("title"),
                "tier": passed.get("tier"),
                "occurrences": 1,
                "evidence": list(passed.get("evidence", [])),
            }
        else:
            existing["occurrences"] += 1
            existing["evidence"].extend(passed.get("evidence", []))
    rows = []
    for group in groups.values():
        frames = sorted(set(group["evidence"]))
        rows.append(
            {
                **group,
                "evidence": frames,
                "frame_ranges": _frame_ranges(frames),
                "tier_label": TIER_LABELS.get(group["tier"], ""),
                "tier_color": TIER_COLORS.get(group["tier"], "#9aa0a6"),
            }
        )
    return rows


def _group_gaps(document: dict) -> list[dict]:
    """Gaps bucketed by `gap_kind`, in GAP_KIND_GROUPS order. Empty
    buckets are dropped — a heading promising a kind of gap this capture
    doesn't have is noise.
    """
    gaps = document.get("gaps", [])
    grouped = []
    for spec in GAP_KIND_GROUPS:
        members = [gap for gap in gaps if gap.get("gap_kind") == spec["kind"]]
        if members:
            grouped.append({**spec, "gaps": members})
    # A gap_kind not in GAP_KIND_GROUPS would otherwise vanish silently.
    known = {spec["kind"] for spec in GAP_KIND_GROUPS}
    unknown = [gap for gap in gaps if gap.get("gap_kind") not in known]
    if unknown:
        grouped.append(
            {
                "kind": "unknown",
                "heading": "Not assessable",
                "lede": "Reported with an unrecognised gap kind.",
                "color": "#6b7280",
                "gaps": unknown,
            }
        )
    return grouped


def _suite_group_index(indistinguishable: Sequence[Sequence[str]]) -> dict[str, int]:
    """suite name -> which indistinguishability group it belongs to, so a
    verdict's dissenting suites can be pointed back at the group that
    drives the disagreement.
    """
    index: dict[str, int] = {}
    for position, group in enumerate(indistinguishable):
        for suite in group:
            index[suite] = position
    return index


def _group_tunnels(document: dict) -> list[dict]:
    """ESP tunnels whose *result* is identical collapse into one block.

    Identity is the surviving set plus the indistinguishability partition
    — the analytical outcome. It deliberately excludes `eliminated`,
    whose reason strings embed per-tunnel observations (the NULL check
    quotes the actual version nibble it read), so including it would make
    four tunnels that reached the same conclusion look like four different
    results. Those per-tunnel reasons are kept and rendered under the
    collapsed block, not discarded.
    """
    groups: dict[str, dict] = {}
    for candidate_set in document.get("candidate_sets", []):
        key = _json_key(
            {
                "surviving": sorted(candidate_set.get("surviving", [])),
                "indistinguishable": sorted(
                    sorted(group) for group in candidate_set.get("indistinguishable", [])
                ),
            }
        )
        existing = groups.get(key)
        if existing is None:
            groups[key] = {"representative": candidate_set, "members": [candidate_set]}
        else:
            existing["members"].append(candidate_set)

    verdicts_by_sa: dict[str, list[dict]] = {}
    for verdict in document.get("verdicts", []):
        verdicts_by_sa.setdefault(verdict.get("sa_id"), []).append(verdict)

    blocks = []
    for group in groups.values():
        representative = group["representative"]
        surviving = representative.get("surviving", [])
        universe = representative.get("universe_size", 0)
        indistinguishable = representative.get("indistinguishable", [])
        index = _suite_group_index(indistinguishable)

        sa_ids = [member.get("sa_id") for member in group["members"]]
        blocks.append(
            {
                "sa_ids": sa_ids,
                "tunnel_count": len(sa_ids),
                "universe_size": universe,
                "surviving": surviving,
                "surviving_count": len(surviving),
                "eliminated_count": universe - len(surviving),
                "surviving_pct": round(100.0 * len(surviving) / universe, 1) if universe else 0.0,
                "groups": [
                    {
                        "position": position,
                        "size": len(members),
                        "members": members,
                    }
                    for position, members in enumerate(indistinguishable)
                ],
                "ungrouped": sorted(suite for suite in surviving if suite not in index),
                "members": [
                    {
                        "sa_id": member.get("sa_id"),
                        "eliminated": member.get("eliminated", []),
                    }
                    for member in group["members"]
                ],
                "verdicts": _group_verdicts_for(sa_ids, verdicts_by_sa, index),
            }
        )
    return blocks


def _group_verdicts_for(
    sa_ids: Sequence[str],
    verdicts_by_sa: dict[str, list[dict]],
    suite_group_index: dict[str, int],
) -> list[dict]:
    """The verdicts for a set of tunnels that share a result, deduplicated
    the same way. Each carries which indistinguishability groups its
    dissenting suites belong to, which is what lets the report say *which
    single group is holding a verdict hostage* rather than printing two
    more walls of suite names.
    """
    groups: dict[str, dict] = {}
    for sa_id in sa_ids:
        for verdict in verdicts_by_sa.get(sa_id, []):
            key = _json_key(
                {
                    "predicate": verdict.get("predicate"),
                    "ambiguous": verdict.get("ambiguous"),
                    "outcome": verdict.get("outcome"),
                    "surviving_true": sorted(verdict.get("surviving_true", [])),
                    "surviving_false": sorted(verdict.get("surviving_false", [])),
                }
            )
            if key not in groups:
                groups[key] = verdict

    rendered = []
    for verdict in groups.values():
        true_side = verdict.get("surviving_true", [])
        false_side = verdict.get("surviving_false", [])
        total = len(true_side) + len(false_side)
        dissenting_groups = sorted(
            {suite_group_index[suite] for suite in false_side if suite in suite_group_index}
        )
        rendered.append(
            {
                **verdict,
                "true_count": len(true_side),
                "false_count": len(false_side),
                "true_pct": round(100.0 * len(true_side) / total, 1) if total else 0.0,
                "false_pct": round(100.0 * len(false_side) / total, 1) if total else 0.0,
                "dissenting_groups": dissenting_groups,
                "tier_color": TIER_COLORS.get(verdict.get("basis_tier"), "#9aa0a6"),
            }
        )
    return rendered


def _integrity_signals(document: dict) -> list[dict]:
    """The fields that justify trusting everything else. All present in
    `coverage` already and none of them previously rendered anywhere a
    reader would look. Quiet when clean, loud when not.
    """
    coverage = document.get("coverage", {})
    capture = document.get("capture", {})
    skipped = coverage.get("packets_skipped", 0)
    missing_direction = coverage.get("esp_tunnels_missing_a_direction", 0)
    signals = [
        {
            "label": "tshark exited cleanly",
            "value": "yes" if coverage.get("tshark_exit_clean") else "no",
            "ok": bool(coverage.get("tshark_exit_clean")),
        },
        {
            "label": "packets skipped at ingest",
            "value": str(skipped),
            "ok": skipped == 0,
        },
        {
            "label": "capture truncated",
            "value": "yes" if capture.get("truncated") else "no",
            "ok": not capture.get("truncated"),
        },
        {
            "label": "IKE_SA_INIT request seen",
            "value": "yes" if coverage.get("ike_sa_init_request_observed") else "no",
            "ok": bool(coverage.get("ike_sa_init_request_observed")),
        },
        {
            "label": "IKE_SA_INIT response seen",
            "value": "yes" if coverage.get("ike_sa_init_response_observed") else "no",
            "ok": bool(coverage.get("ike_sa_init_response_observed")),
        },
        {
            "label": "ESP tunnels missing a direction",
            "value": str(missing_direction),
            "ok": missing_direction == 0,
        },
    ]
    return signals


def _check_cells(document: dict, pass_rows: list[dict]) -> list[dict]:
    """One entry per rule that appears in the checks grid, carrying both
    the cell's own label/state and everything its explanation pane needs.

    Built here rather than in the template so the grid and the pane cannot
    disagree about what a cell means — they are two renderings of one list.
    A finding's pane adds its recommendation; a gap's pane adds why the
    gap happened, which is the question a reader clicking a grey cell is
    actually asking.
    """
    catalogue = document.get("rules", {})
    cells: list[dict] = []

    def entry(rule_id: str, label: str, state: str, status: str, **extra) -> dict:
        rule = catalogue.get(rule_id, {})
        return {
            "rule_id": rule_id,
            "label": label,
            "state": state,
            "status": status,
            "explanation": rule.get("explanation", ""),
            "references": rule.get("references", []),
            **extra,
        }

    for finding in document.get("findings", []):
        cells.append(
            entry(
                finding.get("rule_id"),
                finding.get("title"),
                "found",
                f"{finding.get('severity')} · found",
                severity=finding.get("severity"),
                recommendation=finding.get("recommendation"),
            )
        )
    for row in pass_rows:
        cells.append(
            entry(
                row["rule_id"],
                row["title"],
                "pass",
                "passed" + (f" · {row['occurrences']} tunnels" if row["occurrences"] > 1 else ""),
            )
        )
    for gap in document.get("gaps", []):
        kind = gap.get("gap_kind")
        cells.append(
            entry(
                gap.get("rule_id"),
                gap.get("title"),
                "gap",
                GAP_KIND_LABELS.get(kind, kind),
                gap_kind=kind,
                gap_reason=gap.get("reason"),
                gap_explanation=GAP_KIND_EXPLANATIONS.get(kind, ""),
            )
        )
    return cells


def _build_frame_index(document: dict) -> list[dict]:
    """Every frame number cited by any claim or finding, with what cites
    it — this is what makes "every finding links to its frame numbers"
    (MVP_BUILD_PROMPT.md Phase 6) an actual in-page hyperlink rather than
    a bare number: each evidence badge in the template links to
    `#frame-N` here, an anchor listing every claim/finding that names that
    frame. A full per-packet drill-down (showing the frame's own bytes)
    is out of scope per Phase 6's "do not build: dashboard" — this is the
    self-contained-HTML-appropriate version of the same idea.
    """
    citations: dict[int, list[str]] = {}
    for claim in document.get("claims", []):
        for frame in claim.get("evidence", []):
            citations.setdefault(frame, []).append(f"Claim: {claim['field']}")
    for finding in document.get("findings", []):
        for frame in finding.get("evidence", []):
            citations.setdefault(frame, []).append(f"Finding: {finding['title']}")
    return [{"frame": frame, "citations": labels} for frame, labels in sorted(citations.items())]


def _embedded_json(document: dict) -> str:
    """The findings document, inlined so the report can hand the reader
    the same data it was rendered from without a second file or a network
    round-trip. `<` is escaped so a value containing `</script>` cannot
    close the block it sits in — the one real hazard of inlining JSON.
    """
    return json.dumps(document, indent=2, sort_keys=True, default=str).replace("<", "\\u003c")


def render_report_html(document: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        # `select_autoescape(["html"])` matches on how the *filename ends*,
        # and this template is `report.html.j2` — so it ended in `.j2`,
        # matched nothing, and autoescaping was silently off from Phase 6
        # until this pass, despite the code plainly intending it. Every
        # capture-derived string (a claim's method, a caveat, a suite name,
        # an elimination reason) was interpolated raw into the document.
        # `autoescape=True` cannot be defeated by a filename: this template
        # is HTML, unconditionally. Found by the round-trip test in
        # tests/output/test_report.py::TestEmbeddedFindingsJson.
        autoescape=True,
    )
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(
        doc=document,
        tier_order=TIER_ORDER,
        tier_colors=TIER_COLORS,
        tier_labels=TIER_LABELS,
        tier_explanations=TIER_EXPLANATIONS,
        gap_kind_explanations=GAP_KIND_EXPLANATIONS,
        severity_colors=SEVERITY_COLORS,
        gap_kind_labels=GAP_KIND_LABELS,
        frame_index=_build_frame_index(document),
        tier_summary=_tier_summary(document),
        claim_rows=_group_claims(document),
        pass_rows=_group_passes(document),
        gap_groups=_group_gaps(document),
        tunnel_blocks=_group_tunnels(document),
        integrity_signals=_integrity_signals(document),
        check_cells=_check_cells(document, _group_passes(document)),
        embedded_json=_embedded_json(document),
    )


def write_report_html(html: str, path: str) -> None:
    with open(path, "w") as f:
        f.write(html)

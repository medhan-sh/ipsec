"""report.py — the findings document (a plain dict) -> one self-contained
HTML file (MVP_BUILD_PROMPT.md Phase 6).

Zero project imports, same reasoning as findings.py's module docstring:
this module only ever sees the plain dict `findings.py` assembled, never a
`Claim`/`Finding`/`CandidateSet` directly. `jinja2` (approved,
MVP_BUILD_PROMPT.md §3 / ARCHITECTURE.md §2) renders
`templates/report.html.j2` with everything — CSS included — inlined into
one HTML document. The template loads no CDN `<script src=...>` or
`<link href=...>`, and this module fetches nothing over the network
itself, so "opens standalone in a browser with no network access" holds
by construction, not by testing against a live network block (see
`tests/output/test_report.py` for the static check that nothing
`http(s)://`-shaped ever ends up in the rendered output).
"""

from __future__ import annotations

from pathlib import Path

import jinja2

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "report.html.j2"

# Weakest-to-strongest, matching core.claims.Tier's five member names.
# Duplicated as plain strings rather than imported (see module docstring —
# this module imports nothing project-local); Tier's member names are a
# frozen contract (core/claims.py), so this list silently drifting out of
# sync is a low, but non-zero, disclosed risk — see reports/phase-6.md.
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


def render_report_html(document: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(
        doc=document,
        tier_order=TIER_ORDER,
        tier_colors=TIER_COLORS,
        severity_colors=SEVERITY_COLORS,
        gap_kind_labels=GAP_KIND_LABELS,
        frame_index=_build_frame_index(document),
    )


def write_report_html(html: str, path: str) -> None:
    with open(path, "w") as f:
        f.write(html)

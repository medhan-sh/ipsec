"""findings.py — assembles the findings.json document (MVP_BUILD_PROMPT.md
Phase 6; ARCHITECTURE.md §5's schema, amended twice since being frozen at
"1.0" — see reports/phase-6a.md (`detail` removed) and reports/phase-6b.md
(`passes[]` added, `detail` removal noted there as well) for the disclosed
deviations from the original sketch.

Amendment (explanations pass): a top-level `rules` catalogue was added,
keyed by rule id, carrying each rule's plain-language `explanation` and
its `references`. It lives at the top level rather than being copied onto
every `findings[]`/`passes[]`/`gaps[]` entry because the text is
per-rule, not per-result — repeating it on each entry would write the
same paragraph three times for one rule on a multi-tunnel capture. It
also makes the document self-describing: a consumer can render a rule
without shipping its own copy of rules.yaml.

Deliberately imports nothing project-local — `tests/test_import_graph.py`
has enforced `"output": set()` since before this package existed, matching
ARCHITECTURE.md §1's dependency-rule paragraph verbatim: "`output` imports
nothing but the findings document." Every `Claim`, `CandidateSet`,
`Finding`, `PassedCheck`, `CoverageGap` and `Verdict`/`AmbiguousVerdict`
this module ever sees has already been turned into a plain, JSON-safe
dict by `cli.py` — the one file in this project allowed to import from
every layer at once (see its own docstring). This module's only job is
bundling those already-plain pieces under `schema_version` and writing
them to disk; it never imports `core.claims.Claim` or any other typed
object.
"""

from __future__ import annotations

import json

SCHEMA_VERSION = "1.0"


def assemble_findings_document(
    *,
    capture: dict,
    coverage: dict,
    claims: list[dict],
    candidate_sets: list[dict],
    findings: list[dict],
    passes: list[dict],
    gaps: list[dict],
    verdicts: list[dict],
    rules: dict[str, dict],
) -> dict:
    """Bundles already-plain pieces into the ARCHITECTURE.md §5 shape
    (amended — see module docstring). Takes plain dicts/lists, not typed
    objects — see module docstring.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture": capture,
        "coverage": coverage,
        "claims": claims,
        "candidate_sets": candidate_sets,
        "findings": findings,
        "passes": passes,
        "gaps": gaps,
        "verdicts": verdicts,
        "rules": rules,
    }


def write_findings_json(document: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(document, f, indent=2)
        f.write("\n")

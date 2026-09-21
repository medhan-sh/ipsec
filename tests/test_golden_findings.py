"""tests/fixtures/golden_findings.json — a real findings.json, generated
from weberblog_ikev2.pcap and committed to the repo (Phase 6a closeout
review, item 4: "A schema is not frozen until something fails when it
changes"). This test regenerates the document from the same capture and
diffs it against the committed fixture — any drift in the document's
shape or content, intentional or not, fails here first.

Building this test is what caught a real cross-process determinism bug:
`inference/esp_constraints/engine.py::_indistinguishable_groups()` built
its result by iterating a `frozenset` directly, so the *order* of
indistinguishable groups in `candidate_sets[].indistinguishable` differed
between separate process runs of the identical capture (Python's hash
randomization seeds frozenset iteration order per-process by default).
Fixed there, not worked around here, by sorting deterministically at the
source — see that module's own amendment note.
"""

import json
from pathlib import Path

from ipsec_analyzer.cli import analyze_capture

CAPTURES = Path(__file__).resolve().parent.parent / "captures"
GOLDEN_PATH = Path(__file__).resolve().parent / "fixtures" / "golden_findings.json"


def _regenerate() -> dict:
    return analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))


def test_findings_document_matches_the_committed_golden_fixture():
    regenerated = _regenerate()
    golden = json.loads(GOLDEN_PATH.read_text())
    assert regenerated == golden, (
        "findings.json content drifted from tests/fixtures/golden_findings.json. "
        "If this drift is an intentional, reviewed schema/content change, regenerate the "
        "fixture (see this test module's docstring) and explain why in the phase report — "
        "never edit the fixture to match without understanding the diff first."
    )


def test_regenerated_document_is_itself_deterministic():
    # Guards the fix directly: two regenerations in the same process (and,
    # per this phase's manual verification across several `PYTHONHASHSEED`
    # values, across separate processes too) must be byte-for-byte equal.
    assert _regenerate() == _regenerate()

import json

from ipsec_analyzer.output.findings import SCHEMA_VERSION, assemble_findings_document, write_findings_json


def _minimal_document(**overrides):
    base = dict(
        capture={"filename": "x.pcap", "sha256": "abc", "packet_count": 1, "duration_s": 0.0, "truncated": False},
        coverage={"checks_total": 15, "checks_assessable": 0, "checks_gap": 15},
        claims=[],
        candidate_sets=[],
        findings=[],
        passes=[],
        gaps=[],
        verdicts=[],
    )
    base.update(overrides)
    return assemble_findings_document(**base)


class TestAssembleFindingsDocument:
    def test_schema_version_is_frozen_at_1_0(self):
        doc = _minimal_document()
        assert doc["schema_version"] == "1.0"
        assert SCHEMA_VERSION == "1.0"

    def test_every_top_level_key_is_present(self):
        # Amended (Phase 6b): `passes[]` added alongside `findings[]`/
        # `gaps[]` — a rule that was checked and came back clean is a
        # third outcome, not silence. See reports/phase-6b.md.
        doc = _minimal_document()
        assert set(doc) == {
            "schema_version", "capture", "coverage", "claims", "candidate_sets",
            "findings", "passes", "gaps", "verdicts",
        }

    def test_inputs_are_passed_through_unmodified(self):
        claim = {"field": "ike_sa.dh_group", "value": 19, "tier": "OBSERVED", "confidence": 1.0,
                  "method": "test", "evidence": [3], "caveats": []}
        doc = _minimal_document(claims=[claim])
        assert doc["claims"] == [claim]


class TestWriteFindingsJson:
    def test_writes_valid_json_matching_the_document(self, tmp_path):
        doc = _minimal_document()
        out = tmp_path / "findings.json"
        write_findings_json(doc, str(out))
        assert json.loads(out.read_text()) == doc

    def test_output_ends_with_a_trailing_newline(self, tmp_path):
        out = tmp_path / "findings.json"
        write_findings_json(_minimal_document(), str(out))
        assert out.read_text().endswith("\n")

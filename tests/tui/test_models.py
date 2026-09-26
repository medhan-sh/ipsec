"""test_models.py — Tests for TUI models parsing findings.json (schema 1.0)."""

from pathlib import Path

import pytest

from ipsec_analyzer.tui.models import (
    CandidateSetItem,
    CaptureMeta,
    ClaimItem,
    CoverageMeta,
    FindingsDocument,
    FindingItem,
    GapItem,
    PassItem,
    VerdictItem,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
GOLDEN_PATH = FIXTURES_DIR / "golden_findings.json"


class TestFindingsDocumentGoldenFixture:
    """Verifies that FindingsDocument cleanly parses the committed golden_findings.json fixture."""

    @pytest.fixture
    def doc(self) -> FindingsDocument:
        return FindingsDocument.from_file(GOLDEN_PATH)

    def test_schema_version_is_1_0(self, doc: FindingsDocument):
        assert doc.schema_version == "1.0"

    def test_capture_meta(self, doc: FindingsDocument):
        cap = doc.capture
        assert cap.filename == "weberblog_ikev2.pcap"
        assert cap.packet_count == 197
        assert cap.duration_s == 73.227
        assert cap.truncated is False
        assert cap.sha256.startswith("b2c006dade28a708")

    def test_coverage_meta(self, doc: FindingsDocument):
        cov = doc.coverage
        assert cov.checks_total == 15
        assert cov.checks_assessable == 11
        assert cov.checks_passed == 11
        assert cov.checks_found == 0
        assert cov.checks_gap == 4
        assert cov.packets_skipped == 0
        assert cov.tshark_exit_clean is True
        assert cov.ike_sa_init_request_observed is True
        assert cov.ike_sa_init_response_observed is True
        assert cov.esp_tunnels_total == 4
        assert cov.esp_tunnels_missing_a_direction == 0
        assert cov.tshark_version == "4.4.18"

    def test_candidate_sets(self, doc: FindingsDocument):
        assert len(doc.candidate_sets) == 4
        cs0 = doc.candidate_sets[0]
        assert cs0.sa_id == "spi:0x3d713155+0xf918698d"
        assert cs0.universe_size == 44
        assert len(cs0.surviving) == 42
        assert len(cs0.eliminated) == 2
        assert len(cs0.indistinguishable) == 8

        suite, reason = cs0.eliminated[0]
        assert "NULL-ENC" in suite
        assert "version nibble" in reason

    def test_claims_and_display_values(self, doc: FindingsDocument):
        assert len(doc.claims) > 0
        by_field = {c.field: c for c in doc.claims}

        enc = by_field["ike_sa.encryption"]
        assert enc.tier == "OBSERVED"
        assert enc.confidence == 1.0
        assert enc.display_value() == "ENCR_AES_CBC (id 12, 256-bit)"

        integ = by_field["ike_sa.integrity"]
        assert integ.display_value() == "AUTH_HMAC_SHA2_512_256 (id 14)"

        gran = [c for c in doc.claims if c.field == "esp.granularity"][0]
        assert gran.tier == "NOT_OBSERVABLE"
        assert gran.confidence is None
        assert gran.display_value() == "—"
        assert len(gran.caveats) > 0

    def test_ike_sa_claims_helper(self, doc: FindingsDocument):
        ike_claims = doc.get_ike_sa_claims()
        assert "ike_sa.encryption" in ike_claims
        assert "ike_sa.integrity" in ike_claims
        assert "ike_sa.prf" in ike_claims
        assert "ike_sa.dh_group" in ike_claims

    def test_passes_and_gaps(self, doc: FindingsDocument):
        assert doc.coverage.checks_passed == 11
        assert len(doc.passes) == 14
        assert len(doc.gaps) == 4
        assert len(doc.findings) == 0

        p = doc.passes[0]
        assert p.rule_id == "weak_dh_group_negotiated"
        assert p.tier == "OBSERVED"
        assert p.evidence == (3,)

        g = doc.gaps[0]
        assert g.rule_id == "sixty_four_bit_block_cipher_in_esp"
        assert g.required_tier == "INFERRED_SIDE_CHANNEL"
        assert g.actual_tier == "NOT_OBSERVABLE"
        assert g.gap_kind == "not_observed_in_capture"

    def test_verdicts(self, doc: FindingsDocument):
        assert len(doc.verdicts) > 0
        v = doc.verdicts[0]
        assert v.sa_id.startswith("spi:")
        assert v.predicate in ("confidentiality_acceptable", "integrity_acceptable")
        assert v.ambiguous in (True, False)
        assert v.confidence == 1.0


class TestMinimalDocumentParsing:
    def test_empty_document_does_not_crash(self):
        doc = FindingsDocument.from_dict({
            "schema_version": "1.0",
            "capture": {"filename": "test.pcap"},
            "coverage": {},
        })
        assert doc.schema_version == "1.0"
        assert doc.capture.filename == "test.pcap"
        assert doc.coverage.checks_total == 0
        assert len(doc.claims) == 0
        assert len(doc.candidate_sets) == 0
        assert len(doc.findings) == 0
        assert len(doc.passes) == 0
        assert len(doc.gaps) == 0
        assert len(doc.verdicts) == 0

import re

from ipsec_analyzer.output.findings import assemble_findings_document
from ipsec_analyzer.output.report import render_report_html


def _empty_document():
    return assemble_findings_document(
        capture={"filename": "x.pcap", "sha256": "a" * 64, "packet_count": 0, "duration_s": 0.0, "truncated": False},
        coverage={
            "checks_total": 15, "checks_found": 0, "checks_passed": 0, "checks_assessable": 0, "checks_gap": 15,
            "packets_skipped": 0, "tshark_exit_clean": True,
            "ike_sa_init_request_observed": False, "ike_sa_init_response_observed": False,
            "esp_tunnels_total": 0, "esp_tunnels_missing_a_direction": 0,
        },
        claims=[], candidate_sets=[], findings=[], passes=[], gaps=[], verdicts=[],
    )


def _populated_document():
    doc = _empty_document()
    doc["capture"]["truncated"] = True
    doc["coverage"]["checks_found"] = 1
    doc["coverage"]["checks_passed"] = 1
    doc["coverage"]["checks_assessable"] = 2
    doc["coverage"]["checks_gap"] = 13
    doc["claims"] = [
        {"field": "ike_sa.dh_group", "value": 2, "tier": "OBSERVED", "confidence": 1.0,
         "method": "ike_parse", "evidence": [3, 4], "caveats": []},
        {"field": "ike_sa.encryption", "value": {"transform_id": 12, "key_length": 256, "name": "ENCR_AES_CBC"},
         "tier": "OBSERVED", "confidence": 1.0, "method": "ike_parse", "evidence": [4], "caveats": []},
        {"field": "esp.granularity", "value": None, "tier": "NOT_OBSERVABLE", "confidence": None,
         "method": "esp_constraints.gcd_estimator", "evidence": [], "caveats": ["insufficient diversity"]},
    ]
    doc["findings"] = [
        {"rule_id": "weak_dh_group_negotiated", "severity": "HIGH", "category": "key_exchange",
         "title": "Weak Diffie-Hellman group negotiated",
         "tier": "OBSERVED", "evidence": [3], "scope": [3], "references": ["RFC 3526"],
         "recommendation": "Negotiate DH group 14 or higher."},
    ]
    doc["passes"] = [
        {"rule_id": "ah_in_use", "title": "AH in use (deprecated)", "tier": "OBSERVED", "evidence": [1], "scope": [1]},
    ]
    doc["gaps"] = [
        {"rule_id": "anti_replay_not_observable", "title": "Anti-replay window enforcement",
         "reason": "no claim observed for 'esp.anti_replay_enabled'", "gap_kind": "structurally_unobservable",
         "required_tier": "OBSERVED", "actual_tier": "NOT_OBSERVABLE"},
        {"rule_id": "sixty_four_bit_block_cipher_in_esp", "title": "64-bit block cipher family in use for ESP",
         "reason": "claim tier NOT_OBSERVABLE is below required INFERRED_SIDE_CHANNEL",
         "gap_kind": "not_observed_in_capture", "required_tier": "INFERRED_SIDE_CHANNEL",
         "actual_tier": "NOT_OBSERVABLE"},
    ]
    doc["candidate_sets"] = [
        {"sa_id": "spi:0x00000001+0x00000002", "universe_size": 44,
         "surviving": ["AES-128-GCM-16", "AES-128-CCM-16"],
         "eliminated": [["3DES-CBC + HMAC-SHA1-96", "gcd(E differences) = 4 excludes cbc/8"]],
         "indistinguishable": [["AES-128-GCM-16", "AES-128-CCM-16"]]},
    ]
    doc["verdicts"] = [
        {"sa_id": "spi:0x00000001+0x00000002", "predicate": "confidentiality_acceptable", "ambiguous": False,
         "outcome": True, "confidence": 1.0, "basis_tier": "INFERRED_SIDE_CHANNEL", "basis": "All agree"},
        {"sa_id": "spi:0x00000001+0x00000002", "predicate": "integrity_acceptable", "ambiguous": True,
         "surviving_true": ["AES-128-GCM-16"], "surviving_false": ["AES-128-CTR + HMAC-SHA1-96"],
         "confidence": 1.0, "basis_tier": "INFERRED_SIDE_CHANNEL", "basis": "Surviving candidates disagree"},
    ]
    return doc


_URL_PATTERN = re.compile(r'(src|href)\s*=\s*["\'](https?:)?//', re.IGNORECASE)
# A schemeless `//host/path` reference (protocol-relative URL) still hits
# the network — it just inherits whatever scheme the page loaded under —
# so it's a distinct, separately-checked case from the explicit http(s)://
# pattern above, not a redundant one.
_PROTOCOL_RELATIVE_PATTERN = re.compile(r'''(src|href)\s*=\s*["\']//''', re.IGNORECASE)
_STYLE_BLOCK_PATTERN = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_CSS_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


class TestSelfContained:
    """Acceptance: 'Report opens standalone in a browser with no network
    access.' Checked statically here since running a real network-blocked
    browser is out of this test suite's reach — no http(s):// resource is
    ever referenced from a `src=`/`href=` attribute, and no CDN import
    exists to reference one from.
    """

    def test_no_external_resource_references(self):
        html = render_report_html(_populated_document())
        assert not _URL_PATTERN.search(html), "report must not reference any http(s):// resource"

    def test_no_protocol_relative_references(self):
        html = render_report_html(_populated_document())
        assert not _PROTOCOL_RELATIVE_PATTERN.search(html), (
            "report must not reference any //host protocol-relative resource"
        )

    def test_no_script_tags_at_all(self):
        # This MVP's report needs no JS (collapsible sections use <details>);
        # zero <script> tags is the simplest possible guarantee against an
        # accidental network dependency creeping in later.
        html = render_report_html(_populated_document())
        assert "<script" not in html.lower()

    def test_css_is_inlined_not_linked(self):
        html = render_report_html(_populated_document())
        assert "<style>" in html
        assert "<link" not in html.lower()

    def test_no_at_import_in_any_style_block(self):
        # @import (even of a local file) is exactly the kind of "one more
        # network-shaped hop" this report must never need — this MVP's
        # stylesheet is one inline block by construction, but this pins
        # that down explicitly rather than leaving it as an unstated
        # assumption about how the template happens to be written today.
        html = render_report_html(_populated_document())
        style_blocks = _STYLE_BLOCK_PATTERN.findall(html)
        assert style_blocks, "expected at least one <style> block"
        for block in style_blocks:
            assert "@import" not in block.lower()

    def test_every_css_url_is_a_data_uri_or_absent(self):
        # This MVP's report embeds no images/fonts at all — the honest
        # baseline is zero url() calls. If a future change ever adds one
        # (e.g. an inlined icon), it must be a data: URI, never a path or
        # a network reference, or this test starts failing immediately.
        html = render_report_html(_populated_document())
        style_blocks = _STYLE_BLOCK_PATTERN.findall(html)
        urls = [match[1] for block in style_blocks for match in _CSS_URL_PATTERN.findall(block)]
        for url in urls:
            assert url.startswith("data:"), f"non-data url() found in CSS: {url!r}"


class TestRendersKeySections:
    def test_populated_document_renders_every_section(self):
        html = render_report_html(_populated_document())
        assert "Weak Diffie-Hellman group negotiated" in html
        assert "Anti-replay window enforcement" in html
        assert "AES-128-GCM-16" in html
        assert "confidentiality_acceptable" in html
        assert "integrity_acceptable" in html

    def test_truncated_banner_shown_when_truncated(self):
        html = render_report_html(_populated_document())
        assert "truncated" in html.lower()

    def test_truncated_banner_absent_when_not_truncated(self):
        html = render_report_html(_empty_document())
        # The CSS rule for .truncated-banner is always present (inlined,
        # static stylesheet); what must be absent is the actual element.
        assert '<div class="truncated-banner">' not in html

    def test_tier_legend_lists_all_five_tiers(self):
        html = render_report_html(_empty_document())
        for tier in ("NOT_OBSERVABLE", "ML_PREDICTION", "INFERRED_IMPLEMENTATION_DEFAULT",
                     "INFERRED_SIDE_CHANNEL", "OBSERVED"):
            assert tier in html

    def test_finding_evidence_frame_is_a_working_in_page_link(self):
        html = render_report_html(_populated_document())
        assert 'href="#frame-3"' in html
        assert 'id="frame-3"' in html

    def test_indistinguishable_group_rendered_explicitly(self):
        html = render_report_html(_populated_document())
        assert "indist-group" in html

    def test_ambiguous_verdict_names_both_sides(self):
        html = render_report_html(_populated_document())
        assert "AES-128-GCM-16" in html
        assert "AES-128-CTR + HMAC-SHA1-96" in html

    def test_ambiguous_verdict_shows_basis_tier_and_confidence(self):
        # Phase 6b review fix #4a: basis_tier/confidence were previously
        # only rendered for the unanimous branch.
        html = render_report_html(_populated_document())
        assert "confidence 1.0" in html
        # the ambiguous verdict's own basis-tier badge, not just the
        # unanimous verdict's — both use the same "basis: TIER" text.
        assert html.count("basis: INFERRED_SIDE_CHANNEL") >= 2

    def test_passes_section_lists_passed_checks(self):
        # Item 2: a PASS result gets its own section with a tier badge,
        # not silently dropped.
        html = render_report_html(_populated_document())
        assert "AH in use (deprecated)" in html
        assert 'href="#frame-1"' in html

    def test_coverage_headline_shows_found_passed_gap_breakdown(self):
        # Item 2: "N rules total, X found, Y passed, Z gaps" — the exact
        # counts from doc.coverage must appear, not just the labels.
        html = render_report_html(_populated_document())
        assert "<strong>1</strong> found" in html
        assert "<strong>1</strong> passed" in html
        assert "<strong>13</strong> gaps" in html

    def test_transform_id_is_never_shown_bare(self):
        # Item 3: the report must show the resolved name with the raw ID
        # beside it, never the bare integer alone.
        html = render_report_html(_populated_document())
        assert "ENCR_AES_CBC" in html
        assert "id 12" in html
        assert "256-bit" in html

    def test_not_observed_in_capture_gap_kind_reads_as_ignorance_not_absence(self):
        # Item 5: "not present" asserts absence; must read as ignorance.
        html = render_report_html(_populated_document())
        assert "not observed in this capture" in html
        assert "not present in this capture" not in html

    def test_not_observable_claim_confidence_renders_as_a_dash_not_zero(self):
        # Item 4b, report side: a null confidence must not silently print
        # as an empty cell or as a fabricated 0.0 (0.0 is a real, distinct
        # confidence value elsewhere in this project's model).
        html = render_report_html(_populated_document())
        assert "0.0</td>" not in html


class TestEmptyDocumentDoesNotCrash:
    def test_empty_document_renders_honest_empty_states(self):
        html = render_report_html(_empty_document())
        assert "No findings triggered" in html
        assert "No ESP data-plane traffic was observed" in html
        assert "No ESP candidate set survived" in html
        assert "No rule was both assessable and clean" in html

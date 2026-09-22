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
        rules=_rule_catalogue(),
    )


def _rule_catalogue():
    """The capture-independent per-rule text, as cli.py emits it. Only the
    rules the fixtures below actually reference — the report must render a
    document whose catalogue covers exactly the rules it cites, not the
    whole of rules.yaml.
    """
    def rule(title, passed_title, explanation, severity="INFO", gap_kind="not_observed_in_capture"):
        return {
            "title": title, "passed_title": passed_title, "explanation": explanation,
            "severity": severity, "category": "test", "references": ["RFC 0000"],
            "recommendation": "Do the recommended thing.", "gap_kind": gap_kind,
        }

    return {
        "weak_dh_group_negotiated": rule(
            "Weak Diffie-Hellman group negotiated", "No weak Diffie-Hellman group negotiated",
            "Diffie-Hellman is how the two ends agree on a shared secret.", severity="HIGH",
        ),
        "ah_in_use": rule("AH in use (deprecated)", "AH not in use",
                          "AH authenticates a packet but provides no confidentiality."),
        "null_encryption": rule("NULL encryption in use for ESP", "NULL encryption ruled out for ESP",
                                "ESP can be configured with a NULL cipher, meaning no confidentiality."),
        "anti_replay_not_observable": rule(
            "Anti-replay window enforcement", "Anti-replay window enforcement observed as enabled",
            "Anti-replay protection means a receiver refuses packets it has already seen.",
            gap_kind="structurally_unobservable",
        ),
        "sixty_four_bit_block_cipher_in_esp": rule(
            "64-bit block cipher family in use for ESP", "No 64-bit block cipher family in ESP",
            "Block ciphers encrypt in fixed-size chunks; a 64-bit block is small.", severity="HIGH",
        ),
    }


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

    # `test_no_script_tags_at_all` used to live here, asserting zero
    # `<script>` tags outright. It was removed deliberately, not weakened
    # to accommodate a change (invariant 7): the acceptance criterion is
    # "opens standalone in a browser with no network access", and zero-JS
    # was a *proxy* for that, chosen in Phase 6 when `<details>` genuinely
    # covered everything the report did. It no longer does — a provenance
    # filter, two-way frame<->claim highlighting and copy/download have no
    # no-JS equivalent. The three tests below assert the real requirement
    # directly (no external script, no network API reachable from the
    # inline script) instead of a proxy that now forbids more than the
    # criterion does. See reports/phase-6e.md.

    def test_no_script_element_loads_an_external_file(self):
        html = render_report_html(_populated_document())
        for tag in re.findall(r"<script\b[^>]*>", html, re.IGNORECASE):
            assert "src" not in tag.lower(), f"script must be inline, got: {tag!r}"

    def test_inline_script_reaches_no_network_api(self):
        # The exhaustive list of ways a page can originate a request
        # without a src=/href= attribute. Any one of them appearing is a
        # network dependency the static URL checks above cannot see.
        html = render_report_html(_populated_document())
        for api in (
            "fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
            "sendBeacon", "importScripts", "navigator.connection",
        ):
            assert api not in html, f"report must not reach the network: found {api!r}"

    def test_dynamic_import_is_never_used(self):
        # `import(...)` fetches a module over the network; it is also the
        # one network call that looks like ordinary syntax rather than an
        # API name, so it gets its own check.
        html = render_report_html(_populated_document())
        assert not re.search(r"\bimport\s*\(", html)

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


def _markup_only(html):
    """Everything before the embedded findings.json. Counting occurrences
    across the whole file would also count the document embedded at the
    end, which legitimately repeats what the markup deduplicates.
    """
    return html[: html.index('<script type="application/json"')]


def _four_identical_tunnels_document():
    """The shape that drove this pass: several ESP tunnels reaching the
    *same* analytical outcome, differing only in the per-tunnel evidence
    behind one elimination. Modelled on weberblog_ikev2.pcap, which has
    four.
    """
    doc = _empty_document()
    doc["coverage"]["esp_tunnels_total"] = 4
    surviving = ["AES-128-GCM-16", "AES-128-CCM-16", "3DES-CBC + HMAC-SHA1-96"]
    indistinguishable = [["AES-128-GCM-16", "AES-128-CCM-16"], ["3DES-CBC + HMAC-SHA1-96"]]
    doc["candidate_sets"] = [
        {
            "sa_id": f"spi:0x0000000{n}+0x1000000{n}",
            "universe_size": 44,
            "surviving": surviving,
            # Same conclusion, different observed nibble per tunnel.
            "eliminated": [["NULL-ENC + HMAC-SHA1-96", f"version nibble 0x{n}"]],
            "indistinguishable": indistinguishable,
        }
        for n in range(1, 5)
    ]
    doc["verdicts"] = [
        {
            "sa_id": f"spi:0x0000000{n}+0x1000000{n}",
            "predicate": "confidentiality_acceptable",
            "ambiguous": True,
            "surviving_true": ["AES-128-GCM-16", "AES-128-CCM-16"],
            "surviving_false": ["3DES-CBC + HMAC-SHA1-96"],
            "confidence": 1.0,
            "basis_tier": "INFERRED_SIDE_CHANNEL",
            "basis": "Surviving candidates disagree",
        }
        for n in range(1, 5)
    ]
    doc["claims"] = [
        {
            "field": "esp.null_encryption_confirmed", "value": False,
            "tier": "INFERRED_SIDE_CHANNEL", "confidence": 1.0,
            "method": "esp_constraints.null_check", "evidence": [n, n + 10], "caveats": ["not a valid IP header"],
        }
        for n in range(1, 5)
    ]
    doc["passes"] = [
        {"rule_id": "null_encryption", "title": "NULL encryption ruled out for ESP",
         "tier": "INFERRED_SIDE_CHANNEL", "evidence": [n], "scope": [n]}
        for n in range(1, 5)
    ]
    doc["coverage"]["checks_passed"] = 1
    doc["coverage"]["checks_assessable"] = 1
    doc["coverage"]["checks_gap"] = 14
    return doc


class TestIdenticalTunnelsCollapse:
    """Four tunnels with the same outcome previously rendered the same
    surviving set four times, its indistinguishability partition four
    times, and one verdict each. The collapse must be lossless: the
    conclusion once, the per-tunnel evidence still all there.
    """

    def test_surviving_set_is_rendered_once_not_once_per_tunnel(self):
        html = render_report_html(_four_identical_tunnels_document())
        # The full surviving list appears in exactly one place (the
        # "All N surviving suite names" disclosure) rather than four.
        assert html.count("AES-128-GCM-16, AES-128-CCM-16, 3DES-CBC + HMAC-SHA1-96") == 1

    def test_all_four_tunnel_ids_are_still_named(self):
        html = render_report_html(_four_identical_tunnels_document())
        for n in range(1, 5):
            assert f"spi:0x0000000{n}+0x1000000{n}" in html

    def test_per_tunnel_elimination_evidence_is_preserved(self):
        # The four tunnels agree on the conclusion but each observed a
        # different nibble. Collapsing the conclusion must not discard
        # the four distinct observations behind it.
        html = render_report_html(_four_identical_tunnels_document())
        for n in range(1, 5):
            assert f"version nibble 0x{n}" in html

    def test_identical_verdicts_collapse_to_one(self):
        # Scoped to the markup: the embedded findings.json below it still
        # carries all four verdicts verbatim, and must — the document is
        # the record, the markup is the reading of it.
        markup = _markup_only(render_report_html(_four_identical_tunnels_document()))
        assert markup.count("confidentiality_acceptable") == 1

    def test_identical_claims_collapse_with_an_occurrence_count(self):
        html = render_report_html(_four_identical_tunnels_document())
        markup = _markup_only(html)
        # One *row* in the claims table, not one mention anywhere: the
        # field name legitimately recurs in the frame index (once per
        # cited frame) and inside the row's own copy-as-JSON payload.
        assert markup.count('<td class="fld">esp.null_encryption_confirmed') == 1
        assert "&times;4" in markup

    def test_merged_claim_keeps_every_frame_from_every_occurrence(self):
        # 4 claims x 2 frames each: the collapsed row must cite all 8,
        # not just the first claim's.
        html = render_report_html(_four_identical_tunnels_document())
        assert "8 frames" in html


class TestPassesGroupPerRule:
    def test_pass_section_counts_rules_not_qualifying_claims(self):
        # The bug this fixes: coverage said "1 passed" while the section
        # heading said "Checks passed (4)" because `passes[]` carries one
        # entry per claim and `checks_passed` counts rules.
        doc = _four_identical_tunnels_document()
        html = render_report_html(doc)
        assert len(doc["passes"]) == 4
        assert doc["coverage"]["checks_passed"] == 1
        assert "Checks passed <span class=\"count\">1 rules</span>" in html

    def test_multi_tunnel_pass_says_how_many_tunnels_it_covers(self):
        html = render_report_html(_four_identical_tunnels_document())
        assert "4 tunnels" in html


class TestGapsGroupedByKind:
    def test_each_gap_kind_gets_its_own_framing(self):
        # Three gaps that all render as "not assessable" are three
        # different messages: re-capture / not built / nobody ever can.
        html = render_report_html(_populated_document())
        assert "Not determinable from this capture" in html
        assert "Never observable, passively, by anyone" in html

    def test_a_kind_with_no_gaps_gets_no_heading(self):
        # _populated_document has no `not_implemented` gap.
        html = render_report_html(_populated_document())
        assert "Not implemented in this build" not in html


class TestCaptureIntegrityPanel:
    def test_integrity_signals_are_rendered(self):
        html = render_report_html(_populated_document())
        assert "tshark exited cleanly" in html
        assert "packets skipped at ingest" in html
        assert "ESP tunnels missing a direction" in html

    def test_a_failing_signal_is_marked_bad(self):
        doc = _populated_document()  # truncated=True
        html = render_report_html(doc)
        assert 'class="sig bad"' in html


class TestEmbeddedFindingsJson:
    def test_document_is_embedded_and_parses(self):
        import json

        html = render_report_html(_populated_document())
        block = re.search(
            r'<script type="application/json" id="findings-data">(.*?)</script>', html, re.DOTALL
        )
        assert block, "expected the findings document to be embedded"
        parsed = json.loads(block.group(1))
        assert parsed["schema_version"] == _populated_document()["schema_version"]

    def test_a_value_containing_a_closing_script_tag_cannot_break_out(self):
        # The one real hazard of inlining JSON into HTML.
        doc = _populated_document()
        doc["claims"][0]["method"] = "</script><script>alert(1)</script>"
        html = render_report_html(doc)
        assert "</script><script>alert(1)" not in html


class TestFrameEvidenceIsSummarised:
    def test_long_frame_lists_render_as_a_count_and_ranges(self):
        doc = _populated_document()
        doc["claims"][0]["evidence"] = list(range(1, 41))
        html = render_report_html(doc)
        assert "40 frames" in html
        assert "1-40" in html

    def test_evidence_link_still_anchors_into_the_frame_index(self):
        doc = _populated_document()
        doc["claims"][0]["evidence"] = list(range(1, 41))
        html = render_report_html(doc)
        assert 'href="#frame-1"' in html
        assert 'id="frame-1"' in html


class TestReadableWithoutScripting:
    """The script is additive. Everything it filters or highlights must
    already be in the markup, so a reader with JS disabled loses
    interaction but never information.
    """

    def test_every_claim_value_is_in_the_markup_not_generated(self):
        html = render_report_html(_populated_document())
        script_start = html.index("<script")
        body_before_script = html[:script_start]
        assert "ENCR_AES_CBC" in body_before_script
        assert "esp.granularity" in body_before_script
        assert "Weak Diffie-Hellman group negotiated" in body_before_script

    def test_suite_names_are_in_the_markup_not_generated(self):
        html = render_report_html(_four_identical_tunnels_document())
        script_start = html.index("<script")
        assert "3DES-CBC + HMAC-SHA1-96" in html[:script_start]


class TestCheckExplanations:
    """Every check in the grid is a control that opens a plain-language
    explanation. The panes are ordinary <details> and work with no
    scripting; the script only makes the grid drive them.
    """

    def test_grid_cells_are_buttons_not_divs(self):
        # Clickable means keyboard-reachable and announced as a control.
        html = render_report_html(_populated_document())
        assert '<button class="cell is-found"' in html
        assert '<button class="cell is-pass"' in html
        assert '<button class="cell is-gap"' in html
        assert '<div class="cell' not in html

    def test_each_cell_is_wired_to_its_pane_by_id(self):
        html = render_report_html(_populated_document())
        for rule_id in ("weak_dh_group_negotiated", "ah_in_use", "anti_replay_not_observable"):
            assert f'data-explain="{rule_id}"' in html
            assert f'aria-controls="expl-{rule_id}"' in html
            assert f'id="expl-{rule_id}"' in html

    def test_explanation_text_is_in_the_markup_without_scripting(self):
        html = render_report_html(_populated_document())
        markup = _markup_only(html)
        assert "Diffie-Hellman is how the two ends agree on a shared secret." in markup

    def test_a_finding_pane_carries_its_recommendation(self):
        html = render_report_html(_populated_document())
        assert "What to do:" in html
        assert "Negotiate DH group 14 or higher." in html

    def test_a_gap_pane_explains_why_the_gap_happened(self):
        # The question a reader clicking a grey cell is actually asking.
        html = render_report_html(_populated_document())
        assert "Why this capture could not answer it:" in html
        assert "No passive observer can ever determine this" in html

    def test_a_pass_pane_offers_no_recommendation(self):
        # Nothing is wrong, so there is nothing to do.
        html = render_report_html(_four_identical_tunnels_document())
        pane_start = html.index('id="expl-null_encryption"')
        pane_end = html.index("</details>", pane_start)
        assert "What to do:" not in html[pane_start:pane_end]

    def test_references_are_shown_in_the_pane(self):
        html = render_report_html(_populated_document())
        assert "RFC 0000" in html

    def test_every_grid_cell_has_a_matching_pane(self):
        # Scoped to the markup: the inline script contains the literal
        # string `[data-explain="` when it builds a selector, which a
        # whole-file scan would pick up as a bogus cell id.
        markup = _markup_only(render_report_html(_populated_document()))
        cells = set(re.findall(r'data-explain="([^"]+)"', markup))
        panes = set(re.findall(r'id="expl-([^"]+)"', markup))
        assert cells, "expected at least one check cell"
        assert cells == panes, "a cell without a pane opens nothing"


class TestProvenanceExplanations:
    def test_all_five_tiers_are_explained(self):
        # Compared through markupsafe's escape, exactly as the template
        # escapes it — the INFERRED_IMPLEMENTATION_DEFAULT text contains an
        # apostrophe, which renders as an entity and would otherwise make
        # this assertion fail on correctly-escaped output.
        from markupsafe import escape

        from ipsec_analyzer.output.report import TIER_EXPLANATIONS

        html = render_report_html(_empty_document())
        for tier, text in TIER_EXPLANATIONS.items():
            assert tier in html
            assert str(escape(text)) in html, f"{tier}: explanation missing from the report"

    def test_tier_explanations_render_even_with_no_claims(self):
        # The provenance lattice is the product; it must be explained on a
        # capture that produced nothing at all.
        html = render_report_html(_empty_document())
        assert "What do these provenance tiers mean?" in html

    def test_tier_blocks_are_not_toggleable_check_panes(self):
        # They reuse the pane's body styling but must not carry `.explain`:
        # the script closes every other `.explain[open]` when a check is
        # clicked, and static prose has no business in that sweep.
        markup = _markup_only(render_report_html(_empty_document()))
        explain_count = markup.count('class="explain"')
        pane_ids = len(re.findall(r'id="expl-', markup))
        assert explain_count == pane_ids, "only check panes may carry the .explain class"

"""tests/test_cli.py — Phase 6 acceptance criteria, end-to-end against
real public captures (see captures/FETCH.md).

MVP_BUILD_PROMPT.md Phase 6 names "the Palo Alto and Fortinet captures"
specifically; per captures/FETCH.md's own honest note (carried over from
Phase 4), the two weberblog.net captures are what the spec means by that
— real vendor firewall-to-firewall traffic, but vendor identity was never
independently confirmed from the capture data itself. Used here as that.
"""

from pathlib import Path

import pytest

from ipsec_analyzer.cli import analyze_capture, main

CAPTURES = Path(__file__).resolve().parent.parent / "captures"


class TestAnalyzeCaptureSchema:
    """Every document analyze_capture() produces matches ARCHITECTURE.md
    §5's findings.json shape, regardless of what the capture contains.
    """

    @pytest.mark.parametrize(
        "filename",
        [
            "ikev2-decrypt-aes128ccm12.pcap",
            "weberblog_ikev1.pcap",
            "weberblog_ikev2.pcap",
            "http.pcap",
        ],
    )
    def test_document_has_every_top_level_key(self, filename):
        doc = analyze_capture(str(CAPTURES / filename))
        assert set(doc) == {
            "schema_version", "capture", "coverage", "claims", "candidate_sets",
            "findings", "passes", "gaps", "verdicts", "rules",
        }
        assert doc["schema_version"] == "1.0"

    @pytest.mark.parametrize(
        "filename",
        ["ikev2-decrypt-aes128ccm12.pcap", "weberblog_ikev1.pcap", "weberblog_ikev2.pcap"],
    )
    def test_every_finding_carries_frame_evidence(self, filename):
        # Acceptance: "frame references on every finding."
        doc = analyze_capture(str(CAPTURES / filename))
        for finding in doc["findings"]:
            assert finding["evidence"], f"finding {finding['rule_id']} has no frame evidence"

    def test_coverage_headline_numbers_are_internally_consistent(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        c = doc["coverage"]
        assert c["checks_assessable"] + c["checks_gap"] == c["checks_total"]
        assert c["checks_total"] == 15

    @pytest.mark.parametrize(
        "filename",
        ["ikev2-decrypt-aes128ccm12.pcap", "weberblog_ikev1.pcap", "weberblog_ikev2.pcap", "http.pcap"],
    )
    def test_found_plus_passed_plus_gap_equals_total(self, filename):
        # Item 2: "N rules total, X findings, Y passed, Z gaps, with
        # X + Y + Z == N" — the coverage headline's own arithmetic,
        # checked against every real capture available, not just one.
        doc = analyze_capture(str(CAPTURES / filename))
        c = doc["coverage"]
        assert c["checks_found"] + c["checks_passed"] + c["checks_gap"] == c["checks_total"]


class TestTsharkVersionRecorded:
    """Item 2 of the Phase 6c packaging pass: the dissector version that
    actually produced these observations belongs in the record — this
    project's own Bug 1 (Phase 4) was tshark's -T json output shape being
    version-sensitive, so "which version ran" is not a nice-to-have here.
    """

    def test_coverage_contains_a_real_tshark_version_string(self):
        doc = analyze_capture(str(CAPTURES / "http.pcap"))
        version = doc["coverage"]["tshark_version"]
        assert version
        assert version[0].isdigit()

    def test_version_matches_the_dockerfile_pinned_version(self):
        # Confirms the running binary is actually the Dockerfile's pin,
        # not silently drifted — same check ike_parse.py's own test makes
        # against get_tshark_version() directly; this confirms it also
        # actually reaches the emitted document.
        doc = analyze_capture(str(CAPTURES / "http.pcap"))
        assert doc["coverage"]["tshark_version"].startswith("4.4.18")


class TestNegativeObservationsAreClaims:
    """Item 1 of the Phase 6b review, verified end-to-end: a check that
    ran and came back clean must count as assessed, not as a gap. Before
    this fix, weberblog_ikev2.pcap reported checks_assessable=7/
    checks_gap=8, with ike.version/ike.aggressive_mode/ah.detected/
    esp.null_encryption_confirmed all missing from the ledger entirely —
    despite every one of those checks having actually run.
    """

    def test_weberblog_ikev2_reports_the_exact_coverage_split(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        c = doc["coverage"]
        assert c["checks_assessable"] == 11
        assert c["checks_gap"] == 4
        gap_rule_ids = {g["rule_id"] for g in doc["gaps"]}
        # The four rules genuinely still unresolvable on this capture
        # (real findings, not code defects — see reports/phase-4.md and
        # phase-5.md for why): granularity/ICV never recovered from this
        # traffic's size distribution, plus the two structural PFS/
        # anti-replay gaps.
        assert gap_rule_ids == {
            "sixty_four_bit_block_cipher_in_esp",
            "truncated_96_bit_icv",
            "pfs_not_observable",
            "anti_replay_not_observable",
        }

    def test_none_of_the_four_fixed_fields_appear_as_gaps(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        by_field = {c["field"]: c for c in doc["claims"]}
        for field in ("ike.version", "ike.aggressive_mode", "ah.detected"):
            assert field in by_field, f"{field} must always be a claim once IKE/demux ran"
            assert by_field[field]["tier"] == "OBSERVED"
        # esp.null_encryption_confirmed appears once per ESP tunnel (4 on
        # this capture) — all False (real ciphertext, not NULL-ENC).
        null_claims = [c for c in doc["claims"] if c["field"] == "esp.null_encryption_confirmed"]
        assert null_claims, "expected at least one esp.null_encryption_confirmed claim"
        assert all(c["value"] is False and c["tier"] == "INFERRED_SIDE_CHANNEL" for c in null_claims)


class TestIkeHandshakeOnlyCapture:
    """Acceptance: end-to-end on ikev2-decrypt-aes128ccm12.pcap. Honest
    finding (already logged in captures/FETCH.md/reports/phase-4.md):
    this capture is IKE_SA_INIT + IKE_AUTH only, with zero ESP
    data-plane packets — so "an ESP candidate set consistent with the
    filename's algorithm" cannot literally be produced from this specific
    file's own traffic. What Phase 6 *can* and does honestly assert: IKE
    SA parameters are extracted, notify posture is assessed, coverage is
    reported, and the report doesn't fabricate an ESP section it has no
    evidence for (see reports/phase-6.md's Deviations for the full
    account).
    """

    def test_ike_sa_parameters_extracted_and_match_the_filename(self):
        doc = analyze_capture(str(CAPTURES / "ikev2-decrypt-aes128ccm12.pcap"))
        by_field = {c["field"]: c for c in doc["claims"]}
        # 15 = ENCR_AES_CCM_8 (IANA Transform Type 1 registry); confirmed
        # against this exact file in tests/integration/test_end_to_end.py.
        assert by_field["ike_sa.encryption"]["value"]["transform_id"] == 15
        assert by_field["ike_sa.encryption"]["tier"] == "OBSERVED"
        assert "ike_sa.dh_group" in by_field

    def test_no_esp_traffic_produces_an_honest_empty_esp_section(self):
        doc = analyze_capture(str(CAPTURES / "ikev2-decrypt-aes128ccm12.pcap"))
        assert doc["candidate_sets"] == []
        assert doc["verdicts"] == []
        assert doc["coverage"]["esp_tunnels_total"] == 0

    def test_report_renders_without_crashing(self, tmp_path):
        from ipsec_analyzer.output.report import render_report_html

        doc = analyze_capture(str(CAPTURES / "ikev2-decrypt-aes128ccm12.pcap"))
        html = render_report_html(doc)
        assert "No ESP data-plane traffic was observed" in html


class TestWeberblogCaptures:
    """Acceptance: 'Same on the Palo Alto and Fortinet captures' — see
    module docstring for why these are the two files that stands in for
    that criterion.
    """

    def test_ikev2_capture_produces_esp_candidate_sets_and_a_verdict(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        assert doc["candidate_sets"], "expected at least one ESP candidate set"
        assert doc["coverage"]["esp_tunnels_total"] > 0
        predicates = {v["predicate"] for v in doc["verdicts"]}
        assert "confidentiality_acceptable" in predicates
        assert "integrity_acceptable" in predicates

    def test_ikev1_capture_is_detected_and_esp_side_still_runs(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev1.pcap"))
        by_field = {c["field"]: c for c in doc["claims"]}
        assert by_field["ike.version"]["value"] == 1
        # IKEv1's SA structure isn't what extract_ike_sa_init_claims targets
        # (IKEv2-shaped) — correctly absent, not a fabricated guess.
        assert "ike_sa.encryption" not in by_field
        assert doc["candidate_sets"], "ESP side must run independently of IKE version"

    def test_both_captures_report_frame_references_on_every_finding(self):
        for filename in ("weberblog_ikev1.pcap", "weberblog_ikev2.pcap"):
            doc = analyze_capture(str(CAPTURES / filename))
            for finding in doc["findings"]:
                assert finding["evidence"]


class TestTransformNameResolution:
    """Item 3: IANA transform IDs resolved to names in cli.py's
    typed-to-dict conversion. Ground truth verified by hand against
    weberblog_ikev2.pcap specifically, per the review's own instruction:
    12/256 is AES-CBC 256-bit, integrity 14 is HMAC_SHA2_512_256, PRF 7
    is HMAC_SHA2_512, DH group 20 is the 384-bit random ECP group.
    """

    def test_weberblog_ikev2_transform_names_match_ground_truth(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        by_field = {c["field"]: c for c in doc["claims"]}

        encryption = by_field["ike_sa.encryption"]["value"]
        assert encryption["transform_id"] == 12
        assert encryption["key_length"] == 256
        assert encryption["name"] == "ENCR_AES_CBC"

        integrity = by_field["ike_sa.integrity"]["value"]
        assert integrity["transform_id"] == 14
        assert integrity["name"] == "AUTH_HMAC_SHA2_512_256"

        prf = by_field["ike_sa.prf"]["value"]
        assert prf["transform_id"] == 7
        assert prf["name"] == "PRF_HMAC_SHA2_512"

        dh_group = by_field["ike_sa.dh_group"]["value"]
        assert dh_group["transform_id"] == 20
        assert dh_group["name"] == "384-bit random ECP"

    def test_unknown_transform_id_resolves_explicitly_not_a_crash(self):
        from ipsec_analyzer.cli import _resolve_transform_name

        resolved = _resolve_transform_name("ike_sa.integrity", 9999)
        assert resolved == {"transform_id": 9999, "name": "UNKNOWN(9999)"}

    def test_fields_outside_the_transform_tables_are_untouched(self):
        from ipsec_analyzer.cli import _resolve_transform_name

        assert _resolve_transform_name("esp.granularity", 16) == 16
        assert _resolve_transform_name("ike_sa.dh_group", None) is None


class TestVerdictContractFields:
    """Item 4a: basis_tier/confidence must be present on both Verdict and
    AmbiguousVerdict once serialized — checked against a real capture's
    actual ambiguous verdict, not a hand-built one, since the bug was
    specifically that cli.py's serialization dropped both fields for the
    ambiguous branch only.
    """

    def test_ambiguous_verdict_from_a_real_capture_carries_both_fields(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        ambiguous = [v for v in doc["verdicts"] if v["ambiguous"]]
        assert ambiguous, "expected at least one ambiguous verdict on this capture"
        for verdict in ambiguous:
            assert "basis_tier" in verdict
            assert "confidence" in verdict
            assert verdict["confidence"] == 1.0

    def test_unanimous_verdict_still_carries_both_fields(self):
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        unanimous = [v for v in doc["verdicts"] if not v["ambiguous"]]
        for verdict in unanimous:
            assert "basis_tier" in verdict
            assert "confidence" in verdict


class TestNotObservableClaimsSerializeConfidenceAsNull:
    """Item 4b: invariant 3 says NOT_OBSERVABLE carries no value — the
    serialized JSON form must not carry a confidence number either.
    Checked against the dataclass (existing invariant-3 coverage lives in
    tests/core/test_claims.py) *and* the serialized form here, since the
    defect was specifically in cli.py's dict conversion, not the
    dataclass — Claim.confidence is still whatever float the producer set
    (conventionally 0.0), only the JSON output is null.
    """

    def test_not_observable_claim_serializes_confidence_as_null(self):
        # weberblog_ikev2.pcap's esp.granularity claims are NOT_OBSERVABLE
        # (real finding: only 2 distinct wire lengths on this capture).
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        granularity_claims = [c for c in doc["claims"] if c["field"] == "esp.granularity"]
        assert granularity_claims, "expected at least one esp.granularity claim"
        for claim in granularity_claims:
            assert claim["tier"] == "NOT_OBSERVABLE"
            assert claim["value"] is None
            assert claim["confidence"] is None

    def test_observed_and_side_channel_claims_still_carry_a_real_confidence(self):
        # Regression guard: the null-confidence rule must not leak onto
        # tiers that do carry a real value.
        doc = analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        for claim in doc["claims"]:
            if claim["tier"] != "NOT_OBSERVABLE":
                assert claim["confidence"] is not None


class TestNonIpsecCapture:
    def test_http_capture_produces_a_clean_empty_document_not_a_crash(self):
        # Phase 6b review fix #1: demux() always runs, even here, so
        # ah.detected=False is a real, correct observation — "197 packets
        # examined, none were AH" — not a fabricated IKE/ESP finding. The
        # one claim present must be exactly that, nothing IKE/ESP-shaped.
        doc = analyze_capture(str(CAPTURES / "http.pcap"))
        assert doc["claims"] == [
            {
                "field": "ah.detected",
                "value": False,
                "tier": "OBSERVED",
                "confidence": 1.0,
                "method": "demux.extract_ah_detected_claim",
                "evidence": [],
                "caveats": [],
            }
        ]
        assert doc["candidate_sets"] == []
        assert doc["findings"] == []
        assert doc["coverage"]["checks_gap"] == doc["coverage"]["checks_total"] - 1
        assert doc["coverage"]["checks_passed"] == 1
        assert doc["coverage"]["checks_found"] == 0


class TestCliMain:
    def test_main_writes_report_and_json(self, tmp_path):
        report_path = tmp_path / "report.html"
        json_path = tmp_path / "findings.json"
        rc = main(
            [
                str(CAPTURES / "weberblog_ikev2.pcap"),
                "-o", str(report_path),
                "--json", str(json_path),
            ]
        )
        assert rc == 0
        assert report_path.exists()
        assert json_path.exists()
        assert "<html" in report_path.read_text().lower()

        import json as jsonlib

        document = jsonlib.loads(json_path.read_text())
        assert document["schema_version"] == "1.0"

    def test_json_is_written_by_default_even_without_the_flag(self, tmp_path):
        # Phase 6c: findings.json is no longer opt-in — with no --json,
        # it's still written, next to the capture, using the default
        # naming, independent of whatever -o was given.
        import shutil

        capture_copy = tmp_path / "http.pcap"
        shutil.copy(CAPTURES / "http.pcap", capture_copy)
        report_path = tmp_path / "custom_report.html"
        rc = main([str(capture_copy), "-o", str(report_path)])
        assert rc == 0
        assert report_path.exists()
        assert (tmp_path / "http.findings.json").exists()

    def test_default_output_paths_are_named_after_and_next_to_the_capture(self, tmp_path):
        # Item 3's exact acceptance example, generalized: with no output
        # flags at all, both files land beside the capture file itself
        # (not the current directory), named after its basename.
        import shutil

        capture_copy = tmp_path / "weberblog_ikev2.pcap"
        shutil.copy(CAPTURES / "weberblog_ikev2.pcap", capture_copy)
        rc = main([str(capture_copy)])
        assert rc == 0
        assert (tmp_path / "weberblog_ikev2.report.html").exists()
        assert (tmp_path / "weberblog_ikev2.findings.json").exists()

    def test_default_output_paths_survive_a_multi_dot_or_pcapng_extension(self, tmp_path):
        import shutil

        capture_copy = tmp_path / "ipsec_multi_algo_natt.pcapng"
        shutil.copy(CAPTURES / "ipsec_multi_algo_natt.pcapng", capture_copy)
        rc = main([str(capture_copy)])
        assert rc == 0
        assert (tmp_path / "ipsec_multi_algo_natt.report.html").exists()
        assert (tmp_path / "ipsec_multi_algo_natt.findings.json").exists()

    def test_both_output_paths_are_printed_on_stdout(self, tmp_path, capsys):
        import shutil

        capture_copy = tmp_path / "http.pcap"
        shutil.copy(CAPTURES / "http.pcap", capture_copy)
        rc = main([str(capture_copy)])
        assert rc == 0
        out = capsys.readouterr().out
        assert str(tmp_path / "http.report.html") in out
        assert str(tmp_path / "http.findings.json") in out

    def test_explicit_output_still_overrides_the_default(self, tmp_path):
        import shutil

        capture_copy = tmp_path / "http.pcap"
        shutil.copy(CAPTURES / "http.pcap", capture_copy)
        custom_report = tmp_path / "somewhere_else.html"
        custom_json = tmp_path / "somewhere_else.json"
        rc = main([str(capture_copy), "-o", str(custom_report), "--json", str(custom_json)])
        assert rc == 0
        assert custom_report.exists()
        assert custom_json.exists()
        assert not (tmp_path / "http.report.html").exists()
        assert not (tmp_path / "http.findings.json").exists()


class TestTerminalProgress:
    """The run's terminal output. The marker vocabulary carries the same
    distinction the rest of the tool is built on, so it is tested, not
    left to look right by eye.
    """

    def _reporter(self, **kwargs):
        import io

        from ipsec_analyzer.cli import TerminalProgress

        stream = io.StringIO()
        return TerminalProgress(stream=stream, **kwargs), stream

    def test_analyze_capture_is_silent_by_default(self, capsys):
        # Every test in this suite calls analyze_capture as a library;
        # none of them should be printing a progress display.
        analyze_capture(str(CAPTURES / "weberblog_ikev2.pcap"))
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_no_ansi_when_the_stream_is_not_a_tty(self):
        reporter, stream = self._reporter()
        reporter.header("x.pcap")
        reporter.stage("ingest")
        reporter.ok("packets read", "197")
        assert "\033[" not in stream.getvalue()

    def test_no_color_env_var_suppresses_colour(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        reporter, stream = self._reporter()
        reporter.ok("packets read", "197")
        assert "\033[" not in stream.getvalue()

    def test_colour_is_emitted_when_asked_for(self):
        reporter, stream = self._reporter(color=True)
        reporter.ok("packets read", "197")
        assert "\033[32m" in stream.getvalue()

    def test_an_abstention_never_renders_as_a_success_marker(self):
        # The property that matters: a tool built on distinguishing
        # "determined" from "could not tell" must not collapse the two
        # into one green tick the moment it prints to a terminal.
        reporter, stream = self._reporter()
        reporter.ok("resolved thing", "8-byte alignment")
        reporter.skip("unresolved thing", "not determinable")
        lines = [line for line in stream.getvalue().splitlines() if line.strip()]
        ok_line = next(line for line in lines if "resolved thing" in line and "unresolved" not in line)
        skip_line = next(line for line in lines if "unresolved thing" in line)
        assert ok_line.strip()[0] != skip_line.strip()[0], (
            "an abstention must not share a marker with a success"
        )

    def test_label_and_detail_are_always_separated(self):
        # `confidentiality_acceptable` is longer than the label column and
        # previously ran straight into its own detail text.
        reporter, stream = self._reporter()
        reporter.skip("confidentiality_acceptable", "undecided")
        assert "confidentiality_acceptable  undecided" in stream.getvalue()

    def test_an_overlong_detail_is_truncated(self):
        # The line no longer *ends* with the detail — an elapsed time is
        # right-aligned after it — so the ellipsis is mid-line now.
        reporter, stream = self._reporter(width=80)
        reporter.skip("granularity", "x" * 200)
        line = stream.getvalue().rstrip("\n")
        assert "…" in line
        assert "x" * 200 not in line
        assert len(line) <= 80

    def test_markers_fall_back_to_ascii_when_unencodable(self):
        import io

        from ipsec_analyzer.cli import TerminalProgress

        class AsciiStream(io.StringIO):
            encoding = "ascii"

        stream = AsciiStream()
        TerminalProgress(stream=stream).ok("packets read", "197")
        value = stream.getvalue()
        assert "✓" not in value
        assert "+" in value

    def test_a_finding_is_reported_as_a_failure_marker(self):
        from ipsec_analyzer.cli import TerminalProgress

        import io

        stream = io.StringIO()
        analyze_capture(
            str(CAPTURES / "ikev2-decrypt-3des-sha1_160.pcap"),
            progress=TerminalProgress(stream=stream, color=False),
        )
        value = stream.getvalue()
        assert "Weak IKE SA cipher (DES / 3DES)" in value
        assert "HIGH" in value

    def test_identical_verdicts_collapse_in_the_terminal_too(self):
        from ipsec_analyzer.cli import TerminalProgress

        import io

        stream = io.StringIO()
        analyze_capture(
            str(CAPTURES / "weberblog_ikev2.pcap"),
            progress=TerminalProgress(stream=stream, color=False),
        )
        value = stream.getvalue()
        # Four tunnels, one shared outcome per predicate.
        assert value.count("confidentiality_acceptable") == 1
        assert "×4" in value

    def test_a_timed_row_is_right_aligned_to_the_terminal_width(self):
        reporter, stream = self._reporter(width=80)
        reporter.ok("packets read", "197")
        line = stream.getvalue().rstrip("\n")
        assert line.endswith("0.0s")
        assert len(line) == 80

    def test_alignment_measures_unpainted_width(self):
        # ANSI escapes occupy no columns on screen but do count in len(),
        # so padding against the painted string would misalign every timed
        # row precisely when colour is on.
        plain, plain_stream = self._reporter(width=80, color=False)
        painted, painted_stream = self._reporter(width=80, color=True)
        plain.ok("packets read", "197")
        painted.ok("packets read", "197")
        import re

        stripped = re.sub(r"\033\[[0-9;]*m", "", painted_stream.getvalue())
        assert stripped == plain_stream.getvalue()

    def test_output_paths_are_never_truncated(self):
        # Truncation is for caveat prose written for the report. A path the
        # operator has to open must be printed whole, however long the
        # directory happens to be.
        reporter, stream = self._reporter()
        long_path = "/" + "/".join(["a-rather-long-directory-name"] * 6) + "/x.report.html"
        reporter.ok("report", long_path, truncate=False)
        assert long_path in stream.getvalue()

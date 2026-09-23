"""test_tui_pilot.py — Headless Textual Pilot integration tests for the IPsec Analyzer TUI."""

import asyncio
from pathlib import Path

from textual.widgets import DataTable, Input, Label, LoadingIndicator, Static, TabbedContent

from ipsec_analyzer.tui.app import IPsecAnalyzerApp
from ipsec_analyzer.tui.modals.help_modal import HelpModal
from ipsec_analyzer.tui.modals.json_viewer import JsonViewerModal
from ipsec_analyzer.tui.models import FindingsDocument
from ipsec_analyzer.tui.widgets.claims_screen import ClaimsScreen
from ipsec_analyzer.tui.widgets.coverage_screen import CoverageScreen
from ipsec_analyzer.tui.widgets.findings_screen import FindingsScreen
from ipsec_analyzer.tui.widgets.overview_screen import OverviewScreen
from ipsec_analyzer.tui.widgets.tunnels_screen import TunnelsScreen

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
GOLDEN_PATH = FIXTURES_DIR / "golden_findings.json"


def test_tui_mount_and_initial_state():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            # Check main components exist
            assert app.query_one("#sidebar") is not None
            assert app.query_one("#content-container") is not None
            assert app.query_one("#main-tabs", TabbedContent) is not None

            # Verify indicator starts hidden
            indicator = app.query_one("#status-indicator", LoadingIndicator)
            assert indicator.display is False

            # Active tab starts as overview
            tabs = app.query_one("#main-tabs", TabbedContent)
            assert tabs.active == "tab-overview"

    asyncio.run(_run())


def test_tui_loads_golden_findings_and_populates_screens():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            app.load_findings_file(GOLDEN_PATH)
            await pilot.pause()

            # 1. Overview Screen
            overview = app.query_one(OverviewScreen)
            overview_text = str(overview.query_one("#overview-content", Static).render())
            assert "weberblog_ikev2.pcap" in overview_text
            assert "197" in overview_text
            assert "15 rules total" in overview_text

            # 2. Switch to Findings Screen (key '2')
            await pilot.press("2")
            tabs = app.query_one("#main-tabs", TabbedContent)
            assert tabs.active == "tab-findings"

            findings_screen = app.query_one(FindingsScreen)
            # Golden fixture has 0 findings (11 passed, 4 gaps)
            detail_panel = str(findings_screen.query_one("#finding-detail-panel", Static).render())
            assert "NO FINDINGS TRIGGERED" in detail_panel

            # 3. Switch to Tunnels Screen (key '3')
            await pilot.press("3")
            assert tabs.active == "tab-tunnels"

            tunnels_screen = app.query_one(TunnelsScreen)
            summary = str(tunnels_screen.query_one("#tunnel-summary-card", Static).render())
            assert "spi:0x3d713155+0xf918698d" in summary
            assert "42" in summary

            # 4. Switch to Claims Screen (key '4')
            await pilot.press("4")
            assert tabs.active == "tab-claims"

            claims_screen = app.query_one(ClaimsScreen)
            claims_table = claims_screen.query_one("#claims-table", DataTable)
            assert claims_table.row_count > 0

            # 5. Switch to Coverage Screen (key '5')
            await pilot.press("5")
            assert tabs.active == "tab-coverage"

            cov_screen = app.query_one(CoverageScreen)
            cov_table = cov_screen.query_one("#coverage-table", DataTable)
            assert cov_table.row_count == 18  # 14 passed checks + 4 gaps

    asyncio.run(_run())


def test_tui_renders_findings_when_present():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            doc = FindingsDocument.from_dict({
                "schema_version": "1.0",
                "capture": {"filename": "synthetic_findings.pcap", "packet_count": 50, "truncated": False},
                "coverage": {"checks_total": 15, "checks_found": 1, "checks_passed": 10, "checks_gap": 4},
                "findings": [
                    {
                        "rule_id": "weak_dh_group_negotiated",
                        "severity": "HIGH",
                        "category": "key_exchange",
                        "title": "Weak Diffie-Hellman group negotiated",
                        "tier": "OBSERVED",
                        "evidence": [3],
                        "scope": [3],
                        "references": ["RFC 3526"],
                        "recommendation": "Negotiate DH group 14 or higher.",
                    }
                ],
                "passes": [],
                "gaps": [],
                "claims": [],
                "candidate_sets": [],
                "verdicts": [],
            })
            app.load_document(doc)
            await pilot.pause()

            await pilot.press("2")
            findings_screen = app.query_one(FindingsScreen)
            table = findings_screen.query_one("#findings-table", DataTable)
            assert table.row_count == 1

            detail = str(findings_screen.query_one("#finding-detail-panel", Static).render())
            assert "Weak Diffie-Hellman group negotiated" in detail
            assert "RFC 3526" in detail
            assert "Negotiate DH group 14 or higher" in detail

    asyncio.run(_run())


def test_tui_json_viewer_modal():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            app.load_findings_file(GOLDEN_PATH)
            await pilot.pause()

            # Press 'j' to view JSON
            await pilot.press("j")
            assert isinstance(app.screen, JsonViewerModal)

            # Press 'escape' to dismiss
            await pilot.press("escape")
            assert not isinstance(app.screen, JsonViewerModal)

    asyncio.run(_run())


def test_tui_help_modal():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            # Press '?' to view help
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpModal)

            # Press 'escape' to dismiss
            await pilot.press("escape")
            assert not isinstance(app.screen, HelpModal)

    asyncio.run(_run())


def test_tui_tab_switching_via_number_keys():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            tabs = app.query_one("#main-tabs", TabbedContent)

            await pilot.press("1")
            assert tabs.active == "tab-overview"

            await pilot.press("2")
            assert tabs.active == "tab-findings"

            await pilot.press("3")
            assert tabs.active == "tab-tunnels"

            await pilot.press("4")
            assert tabs.active == "tab-claims"

            await pilot.press("5")
            assert tabs.active == "tab-coverage"

    asyncio.run(_run())


def test_tui_analysis_failure_shows_error_modal(tmp_path, monkeypatch):
    import sys
    from ipsec_analyzer.tui.modals.error_modal import ErrorModal

    pcap = tmp_path / "broken.pcap"
    pcap.write_bytes(b"dummy")

    # Mock analyzer command that fails with code 127
    cmd = f'{sys.executable} -c "import sys; sys.stderr.write(\'docker: command not found\\n\'); sys.exit(127)"'
    monkeypatch.setenv("IPSEC_ANALYZE_CMD", cmd)

    async def _run():
        app = IPsecAnalyzerApp(initial_capture=pcap)
        async with app.run_test() as pilot:
            # Trigger analysis
            app.action_analyze_current()
            # Wait for background thread worker
            await pilot.pause(0.5)

            # ErrorModal should be pushed to screen stack
            assert isinstance(app.screen, ErrorModal)
            await pilot.press("escape")
            assert not isinstance(app.screen, ErrorModal)

    asyncio.run(_run())


def test_tui_analysis_success_worker(tmp_path, monkeypatch):
    import json
    import sys

    pcap = tmp_path / "good.pcap"
    pcap.write_bytes(b"dummy")

    findings = tmp_path / "good.findings.json"
    doc_data = {
        "schema_version": "1.0",
        "capture": {"filename": "good.pcap", "packet_count": 100, "duration_s": 5.0, "truncated": False},
        "coverage": {"checks_total": 15, "checks_found": 0, "checks_passed": 11, "checks_gap": 4},
        "claims": [],
        "candidate_sets": [],
        "findings": [],
        "passes": [],
        "gaps": [],
        "verdicts": [],
    }
    findings.write_text(json.dumps(doc_data))

    # Mock analyzer command that succeeds
    cmd = f'{sys.executable} -c "print(\'Analysis finished\')"'
    monkeypatch.setenv("IPSEC_ANALYZE_CMD", cmd)

    async def _run():
        app = IPsecAnalyzerApp(initial_capture=pcap)
        async with app.run_test() as pilot:
            app.action_analyze_current()
            await pilot.pause(0.5)

            overview = app.query_one(OverviewScreen)
            overview_text = str(overview.query_one("#overview-content", Static).render())
            assert "good.pcap" in overview_text
            assert "100" in overview_text

    asyncio.run(_run())


def test_tui_tab_switching_via_letter_keys():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            tabs = app.query_one("#main-tabs", TabbedContent)

            # Test letter shortcuts: f, t, c, v, o
            await pilot.press("f")
            assert tabs.active == "tab-findings"

            await pilot.press("t")
            assert tabs.active == "tab-tunnels"

            await pilot.press("c")
            assert tabs.active == "tab-claims"

            await pilot.press("v")
            assert tabs.active == "tab-coverage"

            await pilot.press("o")
            assert tabs.active == "tab-overview"

    asyncio.run(_run())


def test_tui_help_modal_key_h():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            # Press 'h' to open help
            await pilot.press("h")
            assert isinstance(app.screen, HelpModal)

            # Verify table has content
            modal_table = app.screen.query_one(DataTable)
            assert modal_table.row_count >= 10

            await pilot.press("escape")
            assert not isinstance(app.screen, HelpModal)

    asyncio.run(_run())


def test_tui_error_modal_structure():
    from ipsec_analyzer.tui.modals.error_modal import ErrorModal
    from textual.widgets import Label, Static, TextArea

    modal = ErrorModal(
        title="Command Failed",
        message="Subprocess crashed",
        details="docker: cannot connect to daemon socket\nexit code 1",
        capture_path="/tmp/test.pcap",
        returncode=1,
    )

    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            await app.push_screen(modal)
            assert isinstance(app.screen, ErrorModal)

            meta = str(modal.query_one("#modal-meta-label", Label).render())
            assert "Exit Code: 1" in meta
            assert "/tmp/test.pcap" in meta

            hints = str(modal.query_one("#modal-hints-box", Static).render())
            assert "Docker daemon is running" in hints
            assert "IPSEC_ANALYZE_CMD" in hints

            details = modal.query_one(TextArea).text
            assert "cannot connect to daemon socket" in details

            await pilot.press("escape")
            assert not isinstance(app.screen, ErrorModal)

    asyncio.run(_run())


def test_tui_filtering_findings():
    from textual.widgets import Input

    doc = FindingsDocument.from_dict({
        "schema_version": "1.0",
        "capture": {"filename": "filter_test.pcap", "packet_count": 50, "truncated": False},
        "coverage": {"checks_total": 15, "checks_found": 3, "checks_passed": 8, "checks_gap": 4},
        "findings": [
            {
                "rule_id": "weak_dh_group_negotiated",
                "severity": "HIGH",
                "category": "key_exchange",
                "title": "Weak Diffie-Hellman group negotiated",
                "tier": "OBSERVED",
                "evidence": [1],
                "scope": [1],
                "references": [],
                "recommendation": "Use DH 14+",
            },
            {
                "rule_id": "deprecated_ikev1",
                "severity": "HIGH",
                "category": "protocol_version",
                "title": "Deprecated IKEv1 protocol detected",
                "tier": "OBSERVED",
                "evidence": [2],
                "scope": [2],
                "references": [],
                "recommendation": "Migrate to IKEv2",
            },
            {
                "rule_id": "short_psk_entropy",
                "severity": "MEDIUM",
                "category": "authentication",
                "title": "Short pre-shared key entropy suspected",
                "tier": "INFERRED_SIDE_CHANNEL",
                "evidence": [3],
                "scope": [3],
                "references": [],
                "recommendation": "Use 32+ char PSKs",
            },
        ],
        "passes": [],
        "gaps": [],
        "claims": [],
        "candidate_sets": [],
        "verdicts": [],
    })

    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            app.load_document(doc)
            await pilot.press("2")  # findings tab

            findings_screen = app.query_one(FindingsScreen)
            table = findings_screen.query_one("#findings-table", DataTable)
            assert table.row_count == 3

            # Filter by "ikev1"
            filter_inp = findings_screen.query_one("#findings-filter", Input)
            filter_inp.value = "ikev1"
            await pilot.pause()
            assert table.row_count == 1

            # Clear filter
            filter_inp.value = ""
            await pilot.pause()
            assert table.row_count == 3

            # Focus filter via slash action
            app.action_focus_filter()
            await pilot.pause()
            assert filter_inp.has_focus

    asyncio.run(_run())


def test_tui_filtering_claims():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            app.load_findings_file(GOLDEN_PATH)
            await pilot.press("4")  # claims tab

            claims_screen = app.query_one(ClaimsScreen)
            table = claims_screen.query_one("#claims-table", DataTable)
            initial_count = table.row_count
            assert initial_count > 5

            filter_inp = claims_screen.query_one("#claims-filter", Input)
            filter_inp.value = "encryption"
            await pilot.pause()
            filtered_count = table.row_count
            assert 0 < filtered_count < initial_count

            filter_inp.value = ""
            await pilot.pause()
            assert table.row_count == initial_count


    asyncio.run(_run())


def test_tui_filtering_coverage():
    from textual.widgets import Input

    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            app.load_findings_file(GOLDEN_PATH)
            await pilot.press("5")  # coverage tab

            cov_screen = app.query_one(CoverageScreen)
            table = cov_screen.query_one("#coverage-table", DataTable)
            assert table.row_count == 18

            # Filter by "gap"
            filter_inp = cov_screen.query_one("#coverage-filter", Input)
            filter_inp.value = "gap"
            await pilot.pause()
            assert table.row_count == 4

            # Clear filter
            filter_inp.value = ""
            await pilot.pause()
            assert table.row_count == 18

    asyncio.run(_run())


def test_tui_tunnel_navigation_bracket_keys():
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test() as pilot:
            app.load_findings_file(GOLDEN_PATH)
            await pilot.press("3")  # tunnels tab

            tunnels_screen = app.query_one(TunnelsScreen)
            label = tunnels_screen.query_one("#tunnel-selector-label", Label)
            assert "Tunnel 1 of 4" in str(label.render())

            # Press ']' to advance to Tunnel 2
            await pilot.press("right_bracket")
            assert "Tunnel 2 of 4" in str(label.render())

            # Press ']' to advance to Tunnel 3
            await pilot.press("right_bracket")
            assert "Tunnel 3 of 4" in str(label.render())

            # Press '[' to go back to Tunnel 2
            await pilot.press("left_bracket")
            assert "Tunnel 2 of 4" in str(label.render())

    asyncio.run(_run())


def test_tui_realistic_terminal_size_120x36():
    """Verify application mounts, renders all tabs, and handles interactions at 120x36 without crash."""
    async def _run():
        app = IPsecAnalyzerApp()
        async with app.run_test(size=(120, 36)) as pilot:
            app.load_findings_file(GOLDEN_PATH)
            await pilot.pause()

            tabs = app.query_one("#main-tabs", TabbedContent)

            # Cycle through all 5 tabs and verify rendering
            for tab_key, tab_id in [("1", "tab-overview"), ("2", "tab-findings"), ("3", "tab-tunnels"), ("4", "tab-claims"), ("5", "tab-coverage")]:
                await pilot.press(tab_key)
                assert tabs.active == tab_id
                await pilot.pause()

            # Open help modal at 120x36
            await pilot.press("question_mark")
            assert isinstance(app.screen, HelpModal)
            await pilot.press("escape")
            assert not isinstance(app.screen, HelpModal)

            # Open JSON modal at 120x36
            await pilot.press("j")
            assert isinstance(app.screen, JsonViewerModal)
            await pilot.press("escape")
            assert not isinstance(app.screen, JsonViewerModal)

    asyncio.run(_run())


def test_tui_open_html_report_notification(tmp_path):
    pcap = tmp_path / "test.pcap"
    pcap.write_bytes(b"dummy")

    async def _run():
        app = IPsecAnalyzerApp(initial_capture=pcap)
        async with app.run_test() as pilot:
            # HTML report does not exist yet -> warning notification
            app.action_open_html_report()
            await pilot.pause()

            # Create dummy html report
            html = tmp_path / "test.report.html"
            html.write_text("<html>Report</html>")

            # Mock webbrowser.open
            opened = []
            import webbrowser
            monkeypatch_open = lambda url: opened.append(url)
            original_open = webbrowser.open
            webbrowser.open = monkeypatch_open
            try:
                app.action_open_html_report()
                assert len(opened) == 1
                assert opened[0] == html.as_uri()
            finally:
                webbrowser.open = original_open

    asyncio.run(_run())



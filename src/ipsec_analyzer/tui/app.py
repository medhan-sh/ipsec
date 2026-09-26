"""app.py — Main Textual application and composition root for the IPsec Analyzer TUI.

The TUI is an independent presentation consumer around the analyzer.
It loads findings.json documents and renders them across 5 specialized views.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Label, LoadingIndicator, TabbedContent, TabPane

from ipsec_analyzer.tui.modals.error_modal import ErrorModal
from ipsec_analyzer.tui.modals.help_modal import HelpModal
from ipsec_analyzer.tui.modals.json_viewer import JsonViewerModal
from ipsec_analyzer.tui.models import FindingsDocument
from ipsec_analyzer.tui.runner import get_default_sibling_path, run_analysis
from ipsec_analyzer.tui.widgets.capture_browser import CaptureBrowserPanel
from ipsec_analyzer.tui.widgets.claims_screen import ClaimsScreen
from ipsec_analyzer.tui.widgets.coverage_screen import CoverageScreen
from ipsec_analyzer.tui.widgets.findings_screen import FindingsScreen
from ipsec_analyzer.tui.widgets.overview_screen import OverviewScreen
from ipsec_analyzer.tui.widgets.tunnels_screen import TunnelsScreen


class IPsecAnalyzerApp(App[None]):
    """Textual terminal user interface for the Umbra IPsec Security Platform."""

    TITLE = "UMBRA // SECURITY CONSOLE"
    SUB_TITLE = "Passive IPsec (IKEv2/ESP) Assessment Platform"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("1", "switch_tab('tab-overview')", "Overview"),
        Binding("o", "switch_tab('tab-overview')", "Overview", show=False),
        Binding("2", "switch_tab('tab-findings')", "Findings"),
        Binding("f", "switch_tab('tab-findings')", "Findings", show=False),
        Binding("3", "switch_tab('tab-tunnels')", "Tunnels"),
        Binding("t", "switch_tab('tab-tunnels')", "Tunnels", show=False),
        Binding("4", "switch_tab('tab-claims')", "Claims"),
        Binding("c", "switch_tab('tab-claims')", "Claims", show=False),
        Binding("5", "switch_tab('tab-coverage')", "Coverage"),
        Binding("v", "switch_tab('tab-coverage')", "Coverage", show=False),
        Binding("f1", "switch_tab('tab-overview')", "Overview", show=False),
        Binding("f2", "switch_tab('tab-findings')", "Findings", show=False),
        Binding("f3", "switch_tab('tab-tunnels')", "Tunnels", show=False),
        Binding("f4", "switch_tab('tab-claims')", "Claims", show=False),
        Binding("f5", "switch_tab('tab-coverage')", "Coverage", show=False),
        Binding("a", "analyze_current", "Analyze"),
        Binding("r", "refresh_captures", "Refresh"),
        Binding("b", "open_html_report", "HTML Report"),
        Binding("j", "view_json", "JSON"),
        Binding("question_mark", "show_help", "Help"),
        Binding("h", "show_help", "Help", show=False),
        Binding("slash", "focus_filter", "Filter", show=False),
        Binding("left_bracket", "prev_tunnel", "Prev Tunnel", show=False),
        Binding("right_bracket", "next_tunnel", "Next Tunnel", show=False),
    ]


    def __init__(self, initial_capture: str | Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._initial_capture = Path(initial_capture).resolve() if initial_capture else None
        self._current_doc: FindingsDocument | None = None
        self._current_capture_path: Path | None = self._initial_capture
        self._is_analyzing: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            yield CaptureBrowserPanel(id="sidebar")
            with Vertical(id="content-container"):
                with Horizontal(id="status-bar"):
                    yield LoadingIndicator(id="status-indicator")
                    yield Label("Ready. Select a capture file to begin.", id="status-label")
                with TabbedContent(initial="tab-overview", id="main-tabs"):
                    with TabPane("Overview", id="tab-overview"):
                        yield OverviewScreen()
                    with TabPane("Findings", id="tab-findings"):
                        yield FindingsScreen()
                    with TabPane("Tunnels", id="tab-tunnels"):
                        yield TunnelsScreen()
                    with TabPane("Claims / Evidence", id="tab-claims"):
                        yield ClaimsScreen()
                    with TabPane("Coverage", id="tab-coverage"):
                        yield CoverageScreen()
        yield Footer()

    def on_mount(self) -> None:
        indicator = self.query_one("#status-indicator", LoadingIndicator)
        indicator.display = False

        if self._initial_capture and self._initial_capture.is_file():
            json_path = get_default_sibling_path(self._initial_capture, ".findings.json")
            if json_path.is_file():
                self.load_findings_file(json_path)
            else:
                self.action_analyze_current()

    def on_capture_browser_panel_capture_selected(
        self, event: CaptureBrowserPanel.CaptureSelected
    ) -> None:
        self._current_capture_path = event.path
        status_label = self.query_one("#status-label", Label)

        if event.has_existing_findings:
            json_path = get_default_sibling_path(event.path, ".findings.json")
            self.load_findings_file(json_path)
            status_label.update(f"Loaded existing findings for [bold cyan]{event.path.name}[/].")
        else:
            status_label.update(
                f"Selected [bold cyan]{event.path.name}[/]. Press [bold]Analyze [a][/bold] to run assessment."
            )

    def on_capture_browser_panel_analyze_requested(
        self, event: CaptureBrowserPanel.AnalyzeRequested
    ) -> None:
        self._current_capture_path = event.path
        self.action_analyze_current()

    def load_findings_file(self, path: Path) -> None:
        try:
            doc = FindingsDocument.from_file(path)
            self._current_doc = doc
            self._update_all_screens(doc)
        except Exception as exc:
            self.notify(f"Failed to load findings JSON: {exc}", severity="error")

    def load_document(self, doc: FindingsDocument) -> None:
        """Loads an already-parsed FindingsDocument directly (used by tests and runners)."""
        self._current_doc = doc
        self._update_all_screens(doc)

    def _update_all_screens(self, doc: FindingsDocument | None) -> None:
        self.query_one(OverviewScreen).update_data(doc)
        self.query_one(FindingsScreen).update_data(doc)
        self.query_one(TunnelsScreen).update_data(doc)
        self.query_one(ClaimsScreen).update_data(doc)
        self.query_one(CoverageScreen).update_data(doc)

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = tab_id

    def action_refresh_captures(self) -> None:
        sidebar = self.query_one(CaptureBrowserPanel)
        sidebar.refresh_tree()
        self.notify("Captures directory refreshed.")

    def action_prev_tunnel(self) -> None:
        self.query_one(TunnelsScreen).select_prev_tunnel()

    def action_next_tunnel(self) -> None:
        self.query_one(TunnelsScreen).select_next_tunnel()

    def action_focus_filter(self) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        if tabs.active == "tab-findings":
            self.query_one(FindingsScreen).action_focus_filter()
        elif tabs.active == "tab-claims":
            self.query_one(ClaimsScreen).action_focus_filter()
        elif tabs.active == "tab-coverage":
            self.query_one(CoverageScreen).action_focus_filter()

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    def action_open_html_report(self) -> None:
        if not self._current_capture_path:
            self.notify("No capture selected.", severity="warning")
            return
        html_path = get_default_sibling_path(self._current_capture_path, ".report.html")
        if html_path.is_file():
            webbrowser.open(html_path.as_uri())
            self.notify(f"Opened {html_path.name} in browser.")
        else:
            self.notify(f"HTML report not found at {html_path.name}. Run analysis first.", severity="warning")

    def action_view_json(self) -> None:
        if self._current_doc:
            self.push_screen(
                JsonViewerModal(
                    self._current_doc.raw_dict,
                    title=f"{self._current_doc.capture.filename}.findings.json",
                )
            )
        elif self._current_capture_path:
            json_path = get_default_sibling_path(self._current_capture_path, ".findings.json")
            if json_path.is_file():
                self.push_screen(JsonViewerModal(json_path.read_text(), title=json_path.name))
            else:
                self.notify("No findings.json available yet for this capture.", severity="warning")
        else:
            self.notify("No capture selected or findings loaded.", severity="warning")

    def action_analyze_current(self) -> None:
        if self._is_analyzing:
            self.notify("Analysis already in progress.", severity="information")
            return

        target_path = self._current_capture_path
        if not target_path or not target_path.is_file():
            # Try to get from sidebar
            sidebar = self.query_one(CaptureBrowserPanel)
            target_path = sidebar.selected_capture

        if not target_path or not target_path.is_file():
            self.notify("Select a valid .pcap or .pcapng file first.", severity="warning")
            return

        self._start_analysis_worker(target_path)

    @work(thread=True, exclusive=True)
    def _start_analysis_worker(self, capture_path: Path) -> None:
        self._is_analyzing = True
        self.call_from_thread(self._on_analysis_started, capture_path)

        result = run_analysis(capture_path)

        self.call_from_thread(self._on_analysis_finished, result)
        self._is_analyzing = False

    def _on_analysis_started(self, capture_path: Path) -> None:
        indicator = self.query_one("#status-indicator", LoadingIndicator)
        status_label = self.query_one("#status-label", Label)
        indicator.display = True
        status_label.update(
            f"[bold cyan]Analyzing {capture_path.name}[/] with ./umbra (waiting for TShark and assessment engine)..."
        )
        self.query_one(CaptureBrowserPanel).query_one("#btn-analyze").disabled = True

    def _on_analysis_finished(self, result) -> None:
        indicator = self.query_one("#status-indicator", LoadingIndicator)
        status_label = self.query_one("#status-label", Label)
        indicator.display = False
        self.query_one(CaptureBrowserPanel).query_one("#btn-analyze").disabled = False

        if result.success and result.document:
            self._current_doc = result.document
            self._update_all_screens(result.document)
            status_label.update(
                f"[bold green]✔ Complete[/] in {result.duration_s}s. "
                f"Findings: [bold]{result.findings_path.name}[/]"
            )
            self.notify(f"Analysis completed successfully ({result.duration_s}s).")
            self.action_switch_tab("tab-overview")
        else:
            status_label.update(
                f"[bold red]✖ Analysis Failed[/] (exit {result.returncode}). Press [bold]?[/bold] for help."
            )
            self.push_screen(
                ErrorModal(
                    title=f"Analysis Failed ({result.capture_path.name})",
                    message=f"Analyzer exited with status code {result.returncode}.",
                    details=result.stderr or result.stdout or result.error_message or "Unknown error",
                    capture_path=result.capture_path,
                    returncode=result.returncode,
                )
            )



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="umbra-tui",
        description="Umbra: Textual Security Console for Passive IPsec Assessment",
    )
    parser.add_argument("capture", nargs="?", default=None, help="Optional path to a .pcap/.pcapng capture file")
    args = parser.parse_args(argv)

    app = IPsecAnalyzerApp(initial_capture=args.capture)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

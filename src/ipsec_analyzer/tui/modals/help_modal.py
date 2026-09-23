"""help_modal.py — Modal displaying keyboard shortcuts reference."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label


class HelpModal(ModalScreen[None]):
    """Displays keyboard shortcuts and navigation reference."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("IPSEC ANALYZER // KEYBOARD REFERENCE", classes="modal-title")
            table = DataTable(classes="modal-body")
            table.cursor_type = "row"
            yield table
            with Horizontal(classes="modal-buttons"):
                yield Button("Close (Esc)", variant="primary", id="btn-close")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Key", "Action", "Description")
        shortcuts = [
            ("1 / o / F1", "Overview Screen", "Switch to capture overview, metadata, and verdict summary"),
            ("2 / f / F2", "Findings Screen", "Switch to security findings table and detail panel"),
            ("3 / t / F3", "Tunnels Screen", "Switch to ESP tunnels, candidate sets, and elimination view"),
            ("4 / c / F4", "Claims Screen", "Switch to wire claims and provenance evidence table"),
            ("5 / v / F5", "Coverage Screen", "Switch to rule coverage breakdown (found, passed, gaps)"),
            ("a", "Analyze Capture", "Run analyzer subprocess against currently selected capture"),
            ("r", "Refresh Captures", "Re-scan the captures directory in the sidebar"),
            ("b", "Open HTML Report", "Open generated .report.html in system default browser"),
            ("j", "View JSON", "Inspect pretty-printed findings.json in modal viewer"),
            ("[ / ]", "Prev/Next Tunnel", "Cycle through candidate sets in Tunnels view"),
            ("/", "Filter / Search", "Focus filter search input in Findings, Claims, or Coverage tab"),
            ("Tab / Shift+Tab", "Focus Cycle", "Cycle focus between sidebar, tabs, inputs, and tables"),
            ("Up / Down", "Navigate", "Navigate file tree or move DataTable row cursor"),
            ("? / h", "Help", "Open this keyboard shortcuts reference"),
            ("q / Ctrl+C", "Quit", "Exit the TUI console application"),
        ]
        for key, action, desc in shortcuts:
            table.add_row(key, action, desc)


    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()

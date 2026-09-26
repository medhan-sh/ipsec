"""error_modal.py — Modal for displaying analysis subprocess errors."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea


class ErrorModal(ModalScreen[None]):
    """Displays error output from a failed analyzer subprocess execution."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    DEFAULT_HINTS = [
        "Verify the Docker daemon is running (`systemctl status docker` or `docker info`).",
        "Verify read permissions on the capture file and write permissions in its directory.",
        "Ensure the file is a valid, uncorrupted PCAP/PCAPNG network trace.",
        "To run directly without Docker, set IPSEC_ANALYZE_CMD=\"python -m ipsec_analyzer.cli\" (or UMBRA_CMD).",
        "Test running the analyzer CLI directly: `./umbra <capture>`.",
    ]

    def __init__(
        self,
        title: str,
        message: str,
        details: str = "",
        *,
        capture_path: str | Path | None = None,
        returncode: int | None = None,
        recovery_hints: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._title_text = title
        self._message_text = message
        self._details_text = details
        self._capture_path = str(capture_path) if capture_path else None
        self._returncode = returncode
        self._recovery_hints = recovery_hints or self.DEFAULT_HINTS

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"⚠ {self._title_text}", classes="modal-title")

            meta_parts = [self._message_text]
            if self._returncode is not None:
                meta_parts.append(f"Exit Code: [bold red]{self._returncode}[/]")
            if self._capture_path:
                meta_parts.append(f"Capture: [bold cyan]{self._capture_path}[/]")
            yield Label("  |  ".join(meta_parts), id="modal-meta-label")

            hints_lines = ["[bold #F3B64B]Recovery Hints:[/]"]
            for hint in self._recovery_hints:
                hints_lines.append(f"  • {hint}")
            yield Static("\n".join(hints_lines), id="modal-hints-box")

            yield Label("[bold]Subprocess Output (stdout / stderr):[/]")
            text_area = TextArea(
                text=self._details_text or "(No additional output)",
                read_only=True,
                classes="modal-body",
            )
            yield text_area
            with Horizontal(classes="modal-buttons"):
                yield Button("Close (Esc)", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()


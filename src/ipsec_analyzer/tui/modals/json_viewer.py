"""json_viewer.py — Modal for displaying raw findings.json."""

from __future__ import annotations

import json
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea


class JsonViewerModal(ModalScreen[None]):
    """Displays pretty-printed findings.json document."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, data: dict[str, Any] | str, title: str = "findings.json") -> None:
        super().__init__()
        self._title_text = title
        if isinstance(data, dict):
            self._json_str = json.dumps(data, indent=2)
        else:
            self._json_str = str(data)

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"RAW JSON // {self._title_text}", classes="modal-title")
            text_area = TextArea(
                text=self._json_str,
                language="json",
                read_only=True,
                classes="modal-body",
            )
            yield text_area
            with Horizontal(classes="modal-buttons"):
                yield Button("Close (Esc)", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()

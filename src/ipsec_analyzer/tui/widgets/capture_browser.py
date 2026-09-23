"""capture_browser.py — Filesystem browser filtered for .pcap / .pcapng captures."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Iterable

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DirectoryTree, Label, Static

from ipsec_analyzer.tui.runner import get_default_sibling_path


class CaptureDirectoryTree(DirectoryTree):
    """DirectoryTree filtered to directories and .pcap / .pcapng files."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for p in paths:
            # Hide hidden directories and files (starting with .)
            if p.name.startswith(".") and p.name not in (".", ".."):
                continue
            if p.is_dir():
                yield p
            elif p.suffix.lower() in (".pcap", ".pcapng"):
                yield p


class CapturePreviewWidget(Static):
    """Displays information and sibling status of the currently selected capture."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "capture-preview")
        super().__init__(**kwargs)
        self._selected_path: Path | None = None

    def update_selected(self, path: Path | None) -> None:
        self._selected_path = path
        self.update(self._render_content())

    def _render_content(self) -> str:
        if not self._selected_path or not self._selected_path.is_file():
            return (
                "[bold cyan]No capture selected[/]\n\n"
                "[muted]Select a .pcap or .pcapng file\nfrom the tree above.[/]"
            )

        p = self._selected_path
        try:
            stat = p.stat()
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            size_str = "unknown"
            mtime = "unknown"

        json_path = get_default_sibling_path(p, ".findings.json")
        html_path = get_default_sibling_path(p, ".report.html")

        has_json = json_path.is_file()
        has_html = html_path.is_file()

        if has_json and has_html:
            status = "[bold green]● ANALYZED[/] (findings & html ready)"
        elif has_json:
            status = "[bold green]● ANALYZED[/] (findings.json ready)"
        elif has_html:
            status = "[bold yellow]◐ REPORT ONLY[/]"
        else:
            status = "[bold #8B9BB0]○ NOT ANALYZED[/]"

        try:
            rel_path = str(p.relative_to(Path.cwd()))
        except ValueError:
            rel_path = str(p)

        return (
            f"[bold cyan]{p.name}[/]\n"
            f"[muted]Path:[/]   {rel_path}\n"
            f"[muted]Size:[/]   {size_str}  [muted]Modified:[/] {mtime}\n"
            f"[muted]Status:[/] {status}"
        )


class CaptureBrowserPanel(Vertical):
    """Left sidebar panel with DirectoryTree and preview."""

    class CaptureSelected(Message):
        """Emitted when a capture file is highlighted or selected."""

        def __init__(self, path: Path, has_existing_findings: bool) -> None:
            super().__init__()
            self.path = path
            self.has_existing_findings = has_existing_findings

    class AnalyzeRequested(Message):
        """Emitted when the Analyze button is clicked."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, root_path: str | Path | None = None, **kwargs) -> None:
        kwargs.setdefault("id", "sidebar")
        super().__init__(**kwargs)
        # Rooted at the current working directory
        self._root_path = Path(root_path).resolve() if root_path is not None else Path.cwd()
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Label("CAPTURES", classes="sidebar-title")
        yield CaptureDirectoryTree(self._root_path, id="capture-tree")
        yield CapturePreviewWidget()
        with Horizontal(id="sidebar-buttons"):
            yield Button("Analyze [a]", variant="primary", id="btn-analyze")
            yield Button("Refresh [r]", id="btn-refresh")

    @property
    def selected_capture(self) -> Path | None:
        return self._selected_path

    def on_directory_tree_node_highlighted(self, event: DirectoryTree.NodeHighlighted) -> None:
        path = event.node.data.path if event.node.data else None
        self._handle_node_selection(path)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self._handle_node_selection(event.path)

    def _handle_node_selection(self, path: Path | None) -> None:
        preview = self.query_one(CapturePreviewWidget)
        if path and path.is_file() and path.suffix.lower() in (".pcap", ".pcapng"):
            self._selected_path = path
            preview.update_selected(path)
            json_path = get_default_sibling_path(path, ".findings.json")
            self.post_message(self.CaptureSelected(path, json_path.is_file()))
        else:
            self._selected_path = None
            preview.update_selected(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-analyze":
            if self._selected_path:
                self.post_message(self.AnalyzeRequested(self._selected_path))
        elif event.button.id == "btn-refresh":
            self.refresh_tree()

    def refresh_tree(self) -> None:
        tree = self.query_one(CaptureDirectoryTree)
        tree.reload()

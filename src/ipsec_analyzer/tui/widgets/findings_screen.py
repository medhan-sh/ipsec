"""findings_screen.py — Findings screen with selectable DataTable and detail panel."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Static

from ipsec_analyzer.tui.models import FindingItem, FindingsDocument


def _format_severity(sev: str) -> str:
    s = sev.upper()
    if s == "HIGH":
        return "[bold #FF5C6C]HIGH[/]"
    if s == "MEDIUM":
        return "[bold #F3B64B]MEDIUM[/]"
    if s == "LOW":
        return "[bold #6AA8FF]LOW[/]"
    return "[#8B9BB0]INFO[/]"


def _format_tier(tier: str) -> str:
    t = tier.upper()
    if t == "OBSERVED":
        return "[bold #45E38A]OBSERVED[/]"
    if t == "INFERRED_SIDE_CHANNEL":
        return "[bold #F3B64B]SIDE_CHANNEL[/]"
    if t == "NOT_OBSERVABLE":
        return "[#8B9BB0]NOT_OBSERVABLE[/]"
    if t == "ML_PREDICTION":
        return "[bold #FF7B72]ML_PREDICTION[/]"
    if t == "INFERRED_IMPLEMENTATION_DEFAULT":
        return "[bold #E3B341]IMPL_DEFAULT[/]"
    return tier


class FindingsScreen(Vertical):
    """Findings screen featuring a selectable DataTable and finding detail panel."""

    BINDINGS = [
        Binding("slash", "focus_filter", "Filter", show=False),
        Binding("escape", "clear_filter", "Clear Filter", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "findings-screen")
        super().__init__(**kwargs)
        self._doc: FindingsDocument | None = None
        self._all_findings: list[FindingItem] = []
        self._findings_map: dict[str, FindingItem] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="table-detail-split"):
            yield Input(
                placeholder="Filter findings (search title, severity, category, rule ID)... [/ to focus, Esc to clear]",
                id="findings-filter",
            )
            table = DataTable(classes="table-half", id="findings-table")
            table.cursor_type = "row"
            yield table
            yield Static(id="finding-detail-panel", classes="detail-half")

    def on_mount(self) -> None:
        table = self.query_one("#findings-table", DataTable)
        table.add_columns("Severity", "Finding", "Category", "Tier", "Evidence")
        self.update_data(None)

    def update_data(self, doc: FindingsDocument | None) -> None:
        self._doc = doc
        self._all_findings = list(doc.findings) if doc else []
        filter_input = self.query_one("#findings-filter", Input)
        self._apply_filter(filter_input.value)

    def _apply_filter(self, query: str) -> None:
        self._findings_map.clear()
        table = self.query_one("#findings-table", DataTable)
        detail = self.query_one("#finding-detail-panel", Static)
        table.clear()

        if self._doc is None:
            detail.update("[muted]No capture loaded.[/]")
            return

        if not self._all_findings:
            detail.update(
                "[bold green]✔ NO FINDINGS TRIGGERED[/]\n\n"
                "[muted]Every assessable rule evaluated clean on this capture.\n"
                f"({self._doc.coverage.checks_passed} checks passed, {self._doc.coverage.checks_gap} gaps).[/]"
            )
            return

        q = query.strip().lower()
        for i, f in enumerate(self._all_findings):
            if q:
                match = (
                    q in f.title.lower()
                    or q in f.rule_id.lower()
                    or q in f.severity.lower()
                    or q in f.category.lower()
                    or q in f.tier.lower()
                    or q in f.recommendation.lower()
                )
                if not match:
                    continue

            row_key = f"finding-{i}"
            self._findings_map[row_key] = f
            frames_str = ", ".join(str(x) for x in f.evidence) if f.evidence else "—"
            table.add_row(
                _format_severity(f.severity),
                f.title,
                f.category,
                _format_tier(f.tier),
                frames_str,
                key=row_key,
            )

        if self._findings_map:
            first_key = next(iter(self._findings_map))
            self._show_finding_detail(self._findings_map[first_key])
        else:
            detail.update(f"[muted]No findings match filter '{query}'. Press Escape to clear filter.[/]")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "findings-filter":
            self._apply_filter(event.value)

    def action_focus_filter(self) -> None:
        self.query_one("#findings-filter", Input).focus()

    def action_clear_filter(self) -> None:
        inp = self.query_one("#findings-filter", Input)
        if inp.has_focus:
            if inp.value:
                inp.value = ""
            else:
                self.query_one("#findings-table", DataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._findings_map:
            self._show_finding_detail(self._findings_map[event.row_key.value])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._findings_map:
            self._show_finding_detail(self._findings_map[event.row_key.value])

    def _show_finding_detail(self, f: FindingItem) -> None:
        detail = self.query_one("#finding-detail-panel", Static)
        refs = ", ".join(f.references) if f.references else "None"
        frames = ", ".join(str(x) for x in f.evidence) if f.evidence else "None"
        scope = ", ".join(str(x) for x in f.scope) if f.scope else "None"

        text = (
            f"[bold cyan]{f.title}[/]\n"
            f"[muted]Rule ID:[/]     {f.rule_id}\n"
            f"[muted]Severity:[/]    {_format_severity(f.severity)}  "
            f"[muted]Category:[/] {f.category}  "
            f"[muted]Tier:[/] {_format_tier(f.tier)}\n"
            f"[muted]Evidence:[/]    Frames {frames}  [muted]Scope:[/] {scope}\n"
            f"[muted]References:[/]  {refs}\n\n"
            f"[bold #29D3FF]Recommendation:[/]\n"
            f"{f.recommendation}"
        )
        detail.update(text)


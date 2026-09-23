"""coverage_screen.py — Rule coverage screen displaying found, passed, and gaps."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Static

from ipsec_analyzer.tui.models import FindingItem, FindingsDocument, GapItem, PassItem

GAP_KIND_LABELS = {
    "structurally_unobservable": "never observable from any passive capture (receiver-side policy)",
    "not_implemented": "not parsed by this MVP (out of scope)",
    "not_observed_in_capture": "not observed in this capture (traffic size-uniform or missing)",
}


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


class CoverageScreen(Vertical):
    """Coverage screen displaying the full breakdown of policy rules: found, passed, and gaps."""

    BINDINGS = [
        Binding("slash", "focus_filter", "Filter", show=False),
        Binding("escape", "clear_filter", "Clear Filter", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "coverage-screen")
        super().__init__(**kwargs)
        self._doc: FindingsDocument | None = None
        self._all_items: list[tuple[str, Any]] = []
        self._items_map: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Static(id="coverage-summary-card", classes="card")
        with Vertical(classes="table-detail-split"):
            yield Input(
                placeholder="Filter coverage rules (search rule ID, title, status, gap kind)... [/ to focus, Esc to clear]",
                id="coverage-filter",
            )
            table = DataTable(classes="table-half", id="coverage-table")
            table.cursor_type = "row"
            yield table
            yield Static(id="coverage-detail-panel", classes="detail-half")

    def on_mount(self) -> None:
        table = self.query_one("#coverage-table", DataTable)
        table.add_columns("Status", "Rule ID", "Title", "Required Tier", "Actual Tier", "Gap Kind / Detail")
        self.update_data(None)

    def update_data(self, doc: FindingsDocument | None) -> None:
        self._doc = doc
        self._all_items.clear()
        summary = self.query_one("#coverage-summary-card", Static)

        if doc is None:
            summary.update("[bold cyan]POLICY RULE COVERAGE[/]\n[muted]No capture loaded.[/]")
            self._apply_filter("")
            return

        cov = doc.coverage
        summary.update(
            f"[bold cyan]POLICY RULE COVERAGE BREAKDOWN[/]\n"
            f"[bold]{cov.checks_total} rules total[/] — "
            f"[bold #FF5C6C]{cov.checks_found} found[/], "
            f"[bold #45E38A]{cov.checks_passed} passed[/], "
            f"[bold #F3B64B]{cov.checks_gap} gaps[/]"
        )

        for f in doc.findings:
            self._all_items.append(("FOUND", f))
        for p in doc.passes:
            self._all_items.append(("PASS", p))
        for g in doc.gaps:
            self._all_items.append(("GAP", g))

        filter_input = self.query_one("#coverage-filter", Input)
        self._apply_filter(filter_input.value)

    def _apply_filter(self, query: str) -> None:
        self._items_map.clear()
        table = self.query_one("#coverage-table", DataTable)
        detail = self.query_one("#coverage-detail-panel", Static)
        table.clear()

        if self._doc is None:
            detail.update("[muted]No capture loaded.[/]")
            return

        q = query.strip().lower()
        idx = 0
        for status, obj in self._all_items:
            if status == "FOUND":
                f: FindingItem = obj
                if q and not (q in f.rule_id.lower() or q in f.title.lower() or q in "found" or q in f.severity.lower() or q in f.category.lower()):
                    continue
                key = f"cov-item-{idx}"
                self._items_map[key] = (status, f)
                table.add_row(
                    "[bold #FF5C6C]FOUND[/]",
                    f.rule_id,
                    f.title,
                    _format_tier(f.tier),
                    _format_tier(f.tier),
                    f"Fired ({f.severity})",
                    key=key,
                )
                idx += 1
            elif status == "PASS":
                p: PassItem = obj
                if q and not (q in p.rule_id.lower() or q in p.title.lower() or q in "pass" or q in "passed" or q in p.tier.lower()):
                    continue
                key = f"cov-item-{idx}"
                self._items_map[key] = (status, p)
                table.add_row(
                    "[bold #45E38A]PASSED[/]",
                    p.rule_id,
                    p.title,
                    _format_tier(p.tier),
                    _format_tier(p.tier),
                    "Clean (condition false)",
                    key=key,
                )
                idx += 1
            elif status == "GAP":
                g: GapItem = obj
                if q and not (q in g.rule_id.lower() or q in g.title.lower() or q in "gap" or q in g.gap_kind.lower() or q in g.reason.lower()):
                    continue
                key = f"cov-item-{idx}"
                self._items_map[key] = (status, g)
                table.add_row(
                    "[bold #F3B64B]GAP[/]",
                    g.rule_id,
                    g.title,
                    _format_tier(g.required_tier),
                    _format_tier(g.actual_tier),
                    g.gap_kind,
                    key=key,
                )
                idx += 1

        if self._items_map:
            first_key = next(iter(self._items_map))
            self._show_detail(self._items_map[first_key])
        else:
            detail.update(f"[muted]No coverage items match filter '{query}'. Press Escape to clear filter.[/]")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "coverage-filter":
            self._apply_filter(event.value)

    def action_focus_filter(self) -> None:
        self.query_one("#coverage-filter", Input).focus()

    def action_clear_filter(self) -> None:
        inp = self.query_one("#coverage-filter", Input)
        if inp.has_focus:
            if inp.value:
                inp.value = ""
            else:
                self.query_one("#coverage-table", DataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._items_map:
            self._show_detail(self._items_map[event.row_key.value])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._items_map:
            self._show_detail(self._items_map[event.row_key.value])

    def _show_detail(self, item: tuple[str, Any]) -> None:
        status, obj = item
        detail = self.query_one("#coverage-detail-panel", Static)

        if status == "GAP":
            g: GapItem = obj
            kind_desc = GAP_KIND_LABELS.get(g.gap_kind, g.gap_kind)
            text = (
                f"[bold #F3B64B]COVERAGE GAP // {g.title}[/]\n"
                f"[muted]Rule ID:[/]        {g.rule_id}\n"
                f"[muted]Required Tier:[/]  {_format_tier(g.required_tier)}\n"
                f"[muted]Actual Tier:[/]    {_format_tier(g.actual_tier)}\n"
                f"[muted]Gap Kind:[/]       [bold cyan]{g.gap_kind}[/] — {kind_desc}\n\n"
                f"[bold #29D3FF]Explanation / Reason:[/]\n"
                f"{g.reason}"
            )
        elif status == "PASS":
            p: PassItem = obj
            frames = ", ".join(str(x) for x in p.evidence) if p.evidence else "None"
            text = (
                f"[bold #45E38A]PASSED CHECK // {p.title}[/]\n"
                f"[muted]Rule ID:[/]        {p.rule_id}\n"
                f"[muted]Assessment Tier:[/] {_format_tier(p.tier)}\n"
                f"[muted]Frame Evidence:[/]  {frames}\n\n"
                f"[bold #29D3FF]Outcome:[/]\n"
                f"This rule was assessable from observed wire claims, and the security risk condition evaluated false. Traffic is clean for this check."
            )
        else:
            f: FindingItem = obj
            text = (
                f"[bold #FF5C6C]FOUND SECURITY ISSUE // {f.title}[/]\n"
                f"[muted]Rule ID:[/]        {f.rule_id}\n"
                f"[muted]Severity:[/]       {f.severity}\n"
                f"[muted]Category:[/]       {f.category}\n\n"
                f"[bold #29D3FF]Recommendation:[/]\n"
                f"{f.recommendation}\n\n"
                f"[muted]Switch to the [bold]Findings [2][/bold] tab for complete details and RFC citations.[/]"
            )

        detail.update(text)


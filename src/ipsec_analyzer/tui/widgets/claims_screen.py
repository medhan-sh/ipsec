"""claims_screen.py — Claims and evidence screen with provenance tiers and caveats."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Static

from ipsec_analyzer.tui.models import ClaimItem, FindingsDocument


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


PROVENANCE_DESCRIPTIONS = {
    "OBSERVED": "Read directly off the wire by dissector (exact protocol field, confidence 1.0).",
    "INFERRED_SIDE_CHANNEL": "Derived deterministically from packet sizes/framing arithmetic.",
    "NOT_OBSERVABLE": "Absent from wire or unobservable; carries no value or confidence.",
    "ML_PREDICTION": "Statistical classifier output (reserved).",
    "INFERRED_IMPLEMENTATION_DEFAULT": "Assumed from implementation defaults (reserved).",
}


class ClaimsScreen(Vertical):
    """Claims screen featuring a DataTable of wire observations/inferences and a detail panel."""

    BINDINGS = [
        Binding("slash", "focus_filter", "Filter", show=False),
        Binding("escape", "clear_filter", "Clear Filter", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "claims-screen")
        super().__init__(**kwargs)
        self._doc: FindingsDocument | None = None
        self._all_claims: list[ClaimItem] = []
        self._claims_map: dict[str, ClaimItem] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="table-detail-split"):
            yield Input(
                placeholder="Filter claims (search field, value, tier, method)... [/ to focus, Esc to clear]",
                id="claims-filter",
            )
            table = DataTable(classes="table-half", id="claims-table")
            table.cursor_type = "row"
            yield table
            yield Static(id="claim-detail-panel", classes="detail-half")

    def on_mount(self) -> None:
        table = self.query_one("#claims-table", DataTable)
        table.add_columns("Field", "Value", "Tier", "Confidence", "Method", "Evidence")
        self.update_data(None)

    def update_data(self, doc: FindingsDocument | None) -> None:
        self._doc = doc
        self._all_claims = list(doc.claims) if doc else []
        filter_input = self.query_one("#claims-filter", Input)
        self._apply_filter(filter_input.value)

    def _apply_filter(self, query: str) -> None:
        self._claims_map.clear()
        table = self.query_one("#claims-table", DataTable)
        detail = self.query_one("#claim-detail-panel", Static)
        table.clear()

        if self._doc is None:
            detail.update("[muted]No capture loaded.[/]")
            return

        if not self._all_claims:
            detail.update("[muted]No claims produced for this capture.[/]")
            return

        q = query.strip().lower()
        for i, c in enumerate(self._all_claims):
            if q:
                val_str = c.display_value().lower()
                cav_str = " ".join(c.caveats).lower()
                match = (
                    q in c.field.lower()
                    or q in val_str
                    or q in c.tier.lower()
                    or q in c.method.lower()
                    or q in cav_str
                )
                if not match:
                    continue

            row_key = f"claim-{i}"
            self._claims_map[row_key] = c
            conf_str = f"{c.confidence:.2f}" if c.confidence is not None else "—"
            frames_str = ", ".join(str(x) for x in c.evidence) if c.evidence else "—"
            table.add_row(
                c.field,
                c.display_value(),
                _format_tier(c.tier),
                conf_str,
                c.method,
                frames_str,
                key=row_key,
            )

        if self._claims_map:
            first_key = next(iter(self._claims_map))
            self._show_claim_detail(self._claims_map[first_key])
        else:
            detail.update(f"[muted]No claims match filter '{query}'. Press Escape to clear filter.[/]")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "claims-filter":
            self._apply_filter(event.value)

    def action_focus_filter(self) -> None:
        self.query_one("#claims-filter", Input).focus()

    def action_clear_filter(self) -> None:
        inp = self.query_one("#claims-filter", Input)
        if inp.has_focus:
            if inp.value:
                inp.value = ""
            else:
                self.query_one("#claims-table", DataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._claims_map:
            self._show_finding_detail(self._claims_map[event.row_key.value])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._claims_map:
            self._show_claim_detail(self._claims_map[event.row_key.value])

    def _show_finding_detail(self, c: ClaimItem) -> None:
        self._show_claim_detail(c)

    def _show_claim_detail(self, c: ClaimItem) -> None:
        detail = self.query_one("#claim-detail-panel", Static)
        conf_str = f"{c.confidence:.2f}" if c.confidence is not None else "None (NOT_OBSERVABLE carries no value)"
        frames = ", ".join(str(x) for x in c.evidence) if c.evidence else "None"
        caveats = "\n".join(f"  • {cav}" for cav in c.caveats) if c.caveats else "  None"
        prov_desc = PROVENANCE_DESCRIPTIONS.get(c.tier, c.tier)

        text = (
            f"[bold cyan]CLAIM // {c.field}[/]\n"
            f"[muted]Value:[/]          [bold]{c.display_value()}[/]\n"
            f"[muted]Tier:[/]           {_format_tier(c.tier)}\n"
            f"[muted]Provenance:[/]     {prov_desc}\n"
            f"[muted]Confidence:[/]     {conf_str}\n"
            f"[muted]Method:[/]         {c.method}\n"
            f"[muted]Frame Evidence:[/] {frames}\n\n"
            f"[bold #29D3FF]Caveats / Notes:[/]\n"
            f"{caveats}"
        )
        detail.update(text)


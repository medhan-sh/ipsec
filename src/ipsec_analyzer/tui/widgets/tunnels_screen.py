"""tunnels_screen.py — ESP tunnels screen showing candidate suites, indistinguishable groups, and elimination reasons."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Collapsible, DataTable, Label, Static

from ipsec_analyzer.tui.models import CandidateSetItem, FindingsDocument


def _render_ratio_bar(surviving: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "[muted]—[/]"
    ratio = max(0.0, min(1.0, surviving / total))
    filled = int(round(ratio * width))
    empty = width - filled
    bar = f"[#45E38A]{'█' * filled}[/][#273447]{'░' * empty}[/]"
    return f"{bar}  [bold]{surviving}/{total}[/] ({ratio * 100:.1f}%)"


class TunnelsScreen(VerticalScroll):
    """Tunnels screen displaying ESP candidate sets, surviving suites, indistinguishable groups, and eliminated reasons."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "tunnels-screen")
        super().__init__(**kwargs)
        self._doc: FindingsDocument | None = None
        self._current_tunnel_idx: int = 0

    def compose(self) -> ComposeResult:
        with Horizontal(id="tunnel-nav", classes="card"):
            yield Button("◀ Prev Tunnel [", id="btn-prev-tunnel")
            yield Label("", id="tunnel-selector-label")
            yield Button("Next Tunnel ] ▶", id="btn-next-tunnel")
        yield Static(id="tunnel-summary-card", classes="card")
        yield Static(id="tunnel-surviving-card", classes="card")
        yield Static(id="tunnel-indist-card", classes="card")
        with Collapsible(title="Eliminated Candidate Suites", id="eliminated-collapsible", classes="card", collapsed=False):
            table = DataTable(id="eliminated-table")
            table.cursor_type = "row"
            yield table

    def on_mount(self) -> None:
        table = self.query_one("#eliminated-table", DataTable)
        table.add_columns("Eliminated Suite", "Elimination Reason")
        self.update_data(None)

    def update_data(self, doc: FindingsDocument | None) -> None:
        self._doc = doc
        self._current_tunnel_idx = 0
        self._render_current_tunnel()

    def _render_current_tunnel(self) -> None:
        nav = self.query_one("#tunnel-nav", Horizontal)
        sel_label = self.query_one("#tunnel-selector-label", Label)
        summary_card = self.query_one("#tunnel-summary-card", Static)
        surviving_card = self.query_one("#tunnel-surviving-card", Static)
        indist_card = self.query_one("#tunnel-indist-card", Static)
        collapsible = self.query_one("#eliminated-collapsible", Collapsible)
        table = self.query_one("#eliminated-table", DataTable)
        table.clear()

        if not self._doc or not self._doc.candidate_sets:
            nav.display = False
            summary_card.update(
                "[bold cyan]NO ESP TUNNELS OBSERVED[/]\n\n"
                "[muted]No ESP data-plane traffic was observed in this capture — nothing to narrow.\n"
                "(This capture may be an IKE-handshake-only vector; see the coverage section.)[/]"
            )
            surviving_card.display = False
            indist_card.display = False
            collapsible.display = False
            return

        candidate_sets = self._doc.candidate_sets
        total_tunnels = len(candidate_sets)

        nav.display = total_tunnels > 1
        surviving_card.display = True
        indist_card.display = True
        collapsible.display = True
        collapsible.title = f"Eliminated Candidate Suites ({len(candidate_sets[self._current_tunnel_idx].eliminated)})"

        if self._current_tunnel_idx >= total_tunnels:
            self._current_tunnel_idx = 0

        cs = candidate_sets[self._current_tunnel_idx]
        sel_label.update(f"Tunnel {self._current_tunnel_idx + 1} of {total_tunnels}: [bold cyan]{cs.sa_id}[/]")

        # Summary with visual ratio bar
        ratio_bar = _render_ratio_bar(len(cs.surviving), cs.universe_size)
        summary_card.update(
            f"[bold cyan]ESP TUNNEL // {cs.sa_id}[/]\n"
            f"[muted]Candidate Universe:[/]  {cs.universe_size} RFC-defined suites\n"
            f"[muted]Surviving Suites:[/]    {ratio_bar}\n"
            f"[muted]Eliminated Suites:[/]   [bold red]{len(cs.eliminated)}[/] eliminated by wire framing"
        )

        # Surviving Suites
        surv_lines = ["[bold cyan]SURVIVING CIPHER SUITES[/]"]
        if cs.surviving:
            for s in cs.surviving:
                surv_lines.append(f"  • [green]{s}[/]")
        else:
            surv_lines.append("  [red](none survive — all candidate suites eliminated)[/]")
        surviving_card.update("\n".join(surv_lines))

        # Indistinguishable groups
        indist_lines = [
            "[bold cyan]INDISTINGUISHABLE GROUPS[/]",
            "[muted]Suites sharing identical wire framing (alignment granularity & ICV length) that cannot be told apart passively:[/]\n"
        ]
        if cs.indistinguishable:
            for i, group in enumerate(cs.indistinguishable, start=1):
                indist_lines.append(f"  [bold #F3B64B]Group {i}:[/] {', '.join(group)}")
        else:
            indist_lines.append("  [muted]No indistinguishable suites group identified.[/]")
        indist_card.update("\n".join(indist_lines))

        # Eliminated table
        for suite, reason in cs.eliminated:
            table.add_row(suite, reason)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._doc or not self._doc.candidate_sets:
            return
        total = len(self._doc.candidate_sets)
        if event.button.id == "btn-prev-tunnel":
            self._current_tunnel_idx = (self._current_tunnel_idx - 1) % total
            self._render_current_tunnel()
        elif event.button.id == "btn-next-tunnel":
            self._current_tunnel_idx = (self._current_tunnel_idx + 1) % total
            self._render_current_tunnel()

    def select_prev_tunnel(self) -> None:
        if self._doc and self._doc.candidate_sets:
            self._current_tunnel_idx = (self._current_tunnel_idx - 1) % len(self._doc.candidate_sets)
            self._render_current_tunnel()

    def select_next_tunnel(self) -> None:
        if self._doc and self._doc.candidate_sets:
            self._current_tunnel_idx = (self._current_tunnel_idx + 1) % len(self._doc.candidate_sets)
            self._render_current_tunnel()

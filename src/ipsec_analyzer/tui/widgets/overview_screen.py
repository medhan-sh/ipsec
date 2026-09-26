"""overview_screen.py — Overview screen for capture metadata, signals, and verdicts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Label, Static

from ipsec_analyzer.tui.models import FindingsDocument


class OverviewScreen(VerticalScroll):
    """Overview screen displaying capture metadata, coverage headline, signals, IKE SA, and verdicts."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "overview-screen")
        super().__init__(**kwargs)
        self._doc: FindingsDocument | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="overview-content")

    def on_mount(self) -> None:
        self.update_data(None)

    def update_data(self, doc: FindingsDocument | None) -> None:
        self._doc = doc
        content = self.query_one("#overview-content", Static)
        if doc is None:
            content.update(
                "[bold cyan]NO CAPTURE LOADED[/]\n\n"
                "[muted]Select a capture file from the sidebar and press [bold]Analyze [a][/bold]\n"
                "or select a previously analyzed capture to inspect findings.[/]"
            )
            return

        lines: list[str] = []

        # 1. Truncation Banner (if truncated)
        if doc.capture.truncated:
            lines.append(
                "[bold #F3B64B on #401F09] ⚠ TRUNCATED CAPTURE [/]\n"
                "[#F3B64B]This capture appears truncated or incompletely captured.\n"
                "Coverage gaps may reflect missing wire data rather than absent features.[/]\n"
            )

        # 2. Coverage Metrics Headline
        cov = doc.coverage
        lines.append(
            f"[bold cyan]RULE COVERAGE[/]  "
            f"[bold]{cov.checks_total} rules total[/] — "
            f"[bold #FF5C6C]{cov.checks_found} found[/], "
            f"[bold #45E38A]{cov.checks_passed} passed[/], "
            f"[bold #F3B64B]{cov.checks_gap} gaps[/]\n"
        )

        # 3. Capture Metadata Card
        cap = doc.capture
        lines.append(
            "[bold cyan]CAPTURE METADATA[/]\n"
            f"[muted]Filename:[/]      [bold]{cap.filename}[/]\n"
            f"[muted]SHA-256:[/]       {cap.sha256[:16]}…\n"
            f"[muted]Packets:[/]       [bold]{cap.packet_count:,}[/]\n"
            f"[muted]Duration:[/]      {cap.duration_s:.3f} s\n"
            f"[muted]ESP Tunnels:[/]   [bold]{cov.esp_tunnels_total}[/]\n"
            f"[muted]Dissector:[/]     tshark {cov.tshark_version}\n"
        )

        # 4. Dissection Signals
        lines.append(
            "[bold cyan]DISSECTION SIGNALS[/]\n"
            f"[muted]tshark exited cleanly:[/]          {'[green]Yes[/]' if cov.tshark_exit_clean else '[red]No[/]'}\n"
            f"[muted]Packets skipped at ingest:[/]      {cov.packets_skipped}\n"
            f"[muted]IKE_SA_INIT request observed:[/]   {'[green]Yes[/]' if cov.ike_sa_init_request_observed else '[yellow]No[/]'}\n"
            f"[muted]IKE_SA_INIT response observed:[/]  {'[green]Yes[/]' if cov.ike_sa_init_response_observed else '[yellow]No[/]'}\n"
            f"[muted]ESP tunnels missing direction:[/]  {'[yellow]' + str(cov.esp_tunnels_missing_a_direction) + '[/]' if cov.esp_tunnels_missing_a_direction > 0 else '[green]0[/]'}\n"
        )

        # 5. IKE SA Parameters
        ike_claims = doc.get_ike_sa_claims()
        lines.append("[bold cyan]IKE SECURITY ASSOCIATION (IKE_SA_INIT)[/]")
        if ike_claims:
            enc = ike_claims.get("ike_sa.encryption")
            integ = ike_claims.get("ike_sa.integrity")
            prf = ike_claims.get("ike_sa.prf")
            dh = ike_claims.get("ike_sa.dh_group")
            version = ike_claims.get("ike.version")
            posture = ike_claims.get("ike_sa_init.downgrade_protection_state")

            lines.append(f"[muted]IKE Version:[/]    {version.display_value() if version else 'IKEv2 (observed)'}")
            lines.append(f"[muted]Encryption:[/]     {enc.display_value() if enc else '—'}")
            lines.append(f"[muted]Integrity:[/]      {integ.display_value() if integ else '—'}")
            lines.append(f"[muted]PRF:[/]            {prf.display_value() if prf else '—'}")
            lines.append(f"[muted]DH Group:[/]       {dh.display_value() if dh else '—'}")
            if posture:
                lines.append(f"[muted]Downgrade Prot:[/] {posture.display_value()}")
        else:
            lines.append("[muted]No IKE_SA_INIT handshake observed in this capture.[/]")
        lines.append("")

        # 6. Lifted Risk Verdicts
        lines.append("[bold cyan]LIFTED RISK VERDICTS[/]")
        if doc.verdicts:
            for v in doc.verdicts:
                pred_label = v.predicate.replace("_", " ").title()
                if v.ambiguous:
                    lines.append(
                        f"[bold #F3B64B]◈ {pred_label} ({v.sa_id}) — AMBIGUOUS[/]  "
                        f"[#8B9BB0](basis tier: {v.basis_tier}, conf: {v.confidence})[/]\n"
                        f"  [muted]Basis:[/] {v.basis}\n"
                        f"  [green]Agree TRUE:[/]  {', '.join(v.surviving_true) if v.surviving_true else '(none)'}\n"
                        f"  [red]Agree FALSE:[/] {', '.join(v.surviving_false) if v.surviving_false else '(none)'}\n"
                    )
                else:
                    outcome_str = "[bold green]ACCEPTABLE (TRUE)[/]" if v.outcome else "[bold red]UNACCEPTABLE (FALSE)[/]"
                    lines.append(
                        f"[bold green]✔[/] [bold]{pred_label}[/] ({v.sa_id}) — {outcome_str}  "
                        f"[#8B9BB0](basis tier: {v.basis_tier}, conf: {v.confidence})[/]\n"
                        f"  [muted]Basis:[/] {v.basis}\n"
                    )
        else:
            lines.append("[muted]No ESP candidate set survived narrowing — no risk verdict lifted.[/]\n")

        content.update("\n".join(lines))

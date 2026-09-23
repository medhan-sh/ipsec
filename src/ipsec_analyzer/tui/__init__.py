"""Textual-based Terminal User Interface for IPsec Analyzer."""

from __future__ import annotations

__all__ = ["main"]


def main() -> int:
    from ipsec_analyzer.tui.app import main as tui_main
    return tui_main()

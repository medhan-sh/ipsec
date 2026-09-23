"""Entry point for python -m ipsec_analyzer.tui."""

from __future__ import annotations

import sys
from ipsec_analyzer.tui.app import main

if __name__ == "__main__":
    sys.exit(main())

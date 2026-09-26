"""test_tui_invariants.py — Enforces architectural layering invariants for the TUI."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TUI_ROOT = REPO_ROOT / "src" / "ipsec_analyzer" / "tui"

# TUI is a presentation consumer that loads findings.json and runs ./ipsec-analyze.
# It must NOT import the analyzer's core, protocol, inference, or assessment layers.
DISALLOWED_TUI_IMPORTS = {
    "ipsec_analyzer.core",
    "ipsec_analyzer.protocol",
    "ipsec_analyzer.inference",
    "ipsec_analyzer.assessment",
}


def _get_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
    return found


def test_tui_does_not_import_analyzer_pipeline_layers():
    violations = []
    for py_file in TUI_ROOT.rglob("*.py"):
        imports = _get_imports(py_file)
        for imp in imports:
            for disallowed in DISALLOWED_TUI_IMPORTS:
                if imp == disallowed or imp.startswith(f"{disallowed}."):
                    violations.append(
                        f"{py_file.relative_to(REPO_ROOT)} imports '{imp}', which violates "
                        f"the presentation-consumer invariant (disallowed: {disallowed})"
                    )
    assert not violations, "\n".join(violations)

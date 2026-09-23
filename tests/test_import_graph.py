"""Enforces ARCHITECTURE.md §1's dependency rule: imports point downward
only. Walks each existing project package's AST (not a text grep, so it
isn't fooled by imports inside strings/comments) and checks every
project-local import against what that layer is allowed to depend on.

Only packages that actually exist on disk are checked — later phases will
add protocol/, inference/, assessment/, output/ one at a time, and this
test extends to them automatically without needing to be rewritten.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "ipsec_analyzer"

# core: the spine, imports nothing from the project.
# synth: "test oracles, not shipped logic" (ARCHITECTURE.md §4) — a sibling
# of the pipeline, may depend only on core.
# protocol/inference/assessment/output: per ARCHITECTURE.md §1's diagram and
# dependency-rule paragraph.
ALLOWED_PROJECT_IMPORTS: dict[str, set[str]] = {
    "core": set(),
    "synth": {"core"},
    "protocol": {"core"},
    "inference": {"core", "protocol"},
    "assessment": {"core"},
    "output": set(),
}

PROJECT_PACKAGES = set(ALLOWED_PROJECT_IMPORTS)


def _sublayer(dotted: str) -> str | None:
    """`ipsec_analyzer.core.constants` -> `"core"`; anything else -> None."""
    parts = dotted.split(".")
    if len(parts) >= 2 and parts[0] == "ipsec_analyzer" and parts[1] in PROJECT_PACKAGES:
        return parts[1]
    return None


def _project_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                layer = _sublayer(alias.name)
                if layer:
                    found.add(layer)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import within the same package
            if node.module:
                layer = _sublayer(node.module)
                if layer:
                    found.add(layer)
    return found


def test_dependency_rule_is_respected():
    violations = []
    for package, allowed in ALLOWED_PROJECT_IMPORTS.items():
        package_dir = SRC_ROOT / package
        if not package_dir.is_dir():
            continue  # not built yet — nothing to check
        for py_file in package_dir.rglob("*.py"):
            imported = _project_imports(py_file) - {package}
            disallowed = imported - allowed
            if disallowed:
                violations.append(
                    f"{py_file.relative_to(REPO_ROOT)} imports {sorted(disallowed)}, "
                    f"not permitted for '{package}' (allowed: {sorted(allowed) or 'nothing'})"
                )
    assert not violations, "\n".join(violations)

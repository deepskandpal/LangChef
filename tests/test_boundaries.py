"""DECISIONS.md #5 — the pack boundary, enforced rather than intended.

``core`` must not import ``judge``, ``connect`` or ``packs``. That is what makes
every number in the product testable with no API key and no network, and it is
what keeps the open-core split possible later.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "langchef"
FORBIDDEN_FOR_CORE = ("langchef.judge", "langchef.connect", "langchef.packs")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_core_imports_nothing_from_the_outer_layers():
    offenders = {}
    for path in sorted((SRC / "core").rglob("*.py")):
        bad = {m for m in _imported_modules(path) if m.startswith(FORBIDDEN_FOR_CORE)}
        if bad:
            offenders[path.name] = sorted(bad)
    assert offenders == {}, f"core/ broke the boundary: {offenders}"


def test_core_imports_no_third_party_packages():
    """Core is stdlib-only until M1 brings numpy and scipy in deliberately."""
    allowed_prefixes = ("langchef",)
    stdlib = set(__import__("sys").stdlib_module_names)
    offenders = {}
    for path in sorted((SRC / "core").rglob("*.py")):
        bad = sorted(
            m
            for m in _imported_modules(path)
            if m.split(".")[0] not in stdlib and not m.startswith(allowed_prefixes)
        )
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, f"core/ grew a third-party dependency: {offenders}"


def test_every_package_has_a_docstring():
    for path in sorted(SRC.rglob("__init__.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"{path.relative_to(SRC)} has no docstring"

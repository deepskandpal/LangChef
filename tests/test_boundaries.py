"""DECISIONS.md #5 — the pack boundary, enforced rather than intended.

``core`` must not import ``judge``, ``connect`` or ``packs``. That is what makes
every number in the product testable with no API key and no network, and it is
what keeps the open-core split possible later.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "langchef"
TESTS = Path(__file__).resolve().parent
FORBIDDEN_FOR_CORE = ("langchef.judge", "langchef.connect", "langchef.packs")
# Exercising the litellm path means injecting a transport at litellm's own
# boundary, which means one test file imports the SDK. One, named here, so the
# containment DECISIONS.md #6 buys is a fact about the suite too and not only
# about src/.
SDK_IN_TESTS = "test_litellm_path.py"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _modules_reached(path: Path) -> set[str]:
    """Imports, plus the modules a test reaches through ``pytest.importorskip``.

    An optional dependency is acquired by a call, not an import statement, so a
    check that only walks ``ast.Import`` would read a file that uses the SDK as
    though it never touched one.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = _imported_modules(path)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "importorskip"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.add(node.args[0].value)
    return names


def test_core_imports_nothing_from_the_outer_layers():
    offenders = {}
    for path in sorted((SRC / "core").rglob("*.py")):
        bad = {m for m in _imported_modules(path) if m.startswith(FORBIDDEN_FOR_CORE)}
        if bad:
            offenders[path.name] = sorted(bad)
    assert offenders == {}, f"core/ broke the boundary: {offenders}"


def test_core_imports_only_the_numerical_stack():
    """Core may use numpy and scipy, and nothing else. DECISIONS.md #7.

    M1 brought these two in deliberately; the allowlist is the record of that
    decision. It is deliberately short. The moment ``core`` can import anything,
    the promise that every number in the product is testable with no API key and
    no network stops being enforceable — so widening this list is a decision
    someone makes on purpose, in a commit, with a reason.

    scikit-learn is pointedly absent: it is a *test* dependency, the independent
    implementation the known-answer tests check against. If the product and its
    check came from the same library, the check would prove nothing.
    """
    allowed_third_party = {"numpy", "scipy"}
    allowed_prefixes = ("langchef",)
    stdlib = set(__import__("sys").stdlib_module_names)
    offenders = {}
    for path in sorted((SRC / "core").rglob("*.py")):
        bad = sorted(
            m
            for m in _imported_modules(path)
            if m.split(".")[0] not in stdlib
            and m.split(".")[0] not in allowed_third_party
            and not m.startswith(allowed_prefixes)
        )
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, f"core/ grew a dependency outside the allowlist: {offenders}"


def test_core_still_touches_no_io_or_network():
    """The other half of the promise: core computes, it does not fetch."""
    forbidden = {"requests", "httpx", "urllib", "socket", "http", "subprocess", "litellm"}
    offenders = {}
    for path in sorted((SRC / "core").rglob("*.py")):
        bad = sorted({m.split(".")[0] for m in _imported_modules(path)} & forbidden)
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, f"core/ reached outside the process: {offenders}"


def test_only_the_shim_imports_a_provider_sdk():
    """DECISIONS.md #6 — one file to rewrite if litellm goes bad."""
    offenders = {}
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "providers.py":
            continue
        if "litellm" in _imported_modules(path):
            offenders[str(path.relative_to(SRC))] = ["litellm"]
    assert offenders == {}, f"a provider SDK leaked out of the shim: {offenders}"


def test_only_one_test_file_imports_a_provider_sdk():
    """The same containment, one layer out.

    ``src/`` is enforced above. The suite needs its own rule because the way the
    litellm path is exercised — a fake transport handed to litellm itself — puts
    an ``import litellm`` in a test, and a rule that stops at ``src/`` would let
    that spread through the suite unremarked. If a second file needs the SDK,
    that is a decision to make on purpose, here.
    """
    offenders = sorted(
        path.name
        for path in sorted(TESTS.rglob("*.py"))
        if path.name != SDK_IN_TESTS and "litellm" in _modules_reached(path)
    )
    assert offenders == [], f"a provider SDK spread through the suite: {offenders}"
    # And the one file that is allowed to must actually still be doing it, or
    # this rule is guarding a path that quietly stopped being exercised.
    assert "litellm" in _modules_reached(TESTS / SDK_IN_TESTS)


def test_every_package_has_a_docstring():
    for path in sorted(SRC.rglob("__init__.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"{path.relative_to(SRC)} has no docstring"

"""DECISIONS.md #5 — the pack boundary, enforced rather than intended.

``core`` must not import ``judge``, ``connect`` or ``packs``. That is what makes
every number in the product testable with no API key and no network, and it is
what keeps the open-core split possible later.

Imports are half of it. The other half is names: ``core`` must not know what a
task class is called either (DECISIONS.md #12). A statistics engine that says
``if task_class == "classification"`` has no import to catch, and it is the same
leak — the pack can no longer be sold separately, and the fifth class is a patch
to the core rather than a directory. The names are read off the packs in this
checkout, so a pack added tomorrow is covered without touching this file.
"""

import ast
import re
from pathlib import Path

import pytest

from langchef.packs.manifest import parse as parse_manifest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "langchef"
PACKS = ROOT / "packs"
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


def _declared_task_classes() -> set[str]:
    """Every task class the packs in this checkout declare.

    Read from ``packs/`` rather than through ``discover()`` on purpose: the
    search path also honours ``$LANGCHEF_PACK_PATH``, and a boundary rule that
    changed with an environment variable would be a different rule on every
    machine. What this repository ships is what this repository is held to.
    """
    return {
        name
        for child in sorted(PACKS.iterdir())
        if child.is_dir() and (child / "pack.toml").is_file()
        for name in parse_manifest(child).task_classes
    }


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _mentions(text: str, task_class: str) -> bool:
    """Does one identifier or string literal carry a task class name?

    Word-wise, so that ``classification_rate`` and ``"qna"`` both count and
    ``classifiers`` does not.
    """
    haystack, needle = _words(text), _words(task_class)
    return any(haystack[i : i + len(needle)] == needle for i in range(len(haystack)))


def _executable_text(path: Path) -> list[tuple[int, str]]:
    """Identifiers and string literals, with their line numbers. Not prose.

    Docstrings are excluded, and comments never reach the AST at all. That is
    deliberate rather than lax: prose that mentions retrieval while explaining a
    statistic cannot make the core depend on a pack, and forbidding the English
    word would push authors into writing worse comments to satisfy a linter. A
    string literal or an identifier is different — it is the raw material of a
    branch, a lookup table or a dispatch, which is exactly the leak.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstrings.add(id(first.value))

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and id(node) not in docstrings:
                found.append((node.lineno, node.value))
        elif isinstance(node, ast.Name):
            found.append((node.lineno, node.id))
        elif isinstance(node, ast.Attribute):
            found.append((node.lineno, node.attr))
        elif isinstance(node, ast.arg):
            found.append((node.lineno, node.arg))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.append((node.lineno, node.name))
        elif isinstance(node, ast.keyword) and node.arg:
            found.append((node.lineno, node.arg))
    return found


def _task_class_leaks() -> dict[str, list[str]]:
    """Where ``core/`` names something a pack defined."""
    classes = _declared_task_classes()
    assert classes, f"no pack in {PACKS} declares a task class — this check would pass vacuously"
    offenders: dict[str, list[str]] = {}
    for path in sorted((SRC / "core").rglob("*.py")):
        hits = sorted(
            {
                f"{name!r} at line {line}"
                for line, text in _executable_text(path)
                for name in classes
                if _mentions(text, name)
            }
        )
        if hits:
            offenders[path.name] = hits
    return offenders


def test_core_names_no_task_class():
    """DECISIONS.md #12 — the core computes over outcomes, not over class names.

    Three of the four task classes have a hard target and never touch the
    calibration modules at all; the one continuous path in ``compare`` is
    general, not per-class. So nothing in ``core/`` needs the name of a class,
    and a name that appeared there would be a branch nobody had to justify.
    """
    leaks = _task_class_leaks()
    assert leaks == {}, (
        f"core/ named a task class a pack defines: {leaks}. "
        "It belongs in the pack manifest (packs/*/pack.toml), not here."
    )


LEAK_CANARY = SRC / "core" / "_task_class_leak_canary.py"

# A leak that would sail through review: a plausible helper, a plausible branch,
# no import to catch, and a perfectly correct answer for classification.
PLANTED_LEAK = '''"""Planted by tests/test_boundaries.py and deleted before the test returns."""


def outcome(row: dict) -> bool:
    """Reduce one example to pass/fail."""
    if row["task_class"] == "classification":
        return row["predicted"] == row["ideal"]
    return bool(row["verdict"])
'''

# The same knowledge, in prose. This must not fail: a comment cannot dispatch.
PLANTED_PROSE = '''"""Planted by tests/test_boundaries.py and deleted before the test returns.

Explains, in a docstring, that a classification dataset is already binary.
"""

# The qna path and the generation path both go through the judge.
LEVEL = 0.95
'''


def test_a_deliberate_task_class_leak_into_core_fails_that_check():
    """The point of the ticket: the rule above is checked, not merely stated.

    A boundary nobody has watched fail is a boundary nobody knows is wired up.
    So plant one — the branch a tired author would actually write — assert that
    the real check rejects it, and take it out again.
    """
    assert not LEAK_CANARY.exists(), f"an earlier run left {LEAK_CANARY} behind; delete it"
    LEAK_CANARY.write_text(PLANTED_LEAK, encoding="utf-8")
    try:
        assert _task_class_leaks(), "a planted task-class branch in core/ went unnoticed"
        with pytest.raises(AssertionError, match="classification"):
            test_core_names_no_task_class()
    finally:
        LEAK_CANARY.unlink()

    # And the check is clean again the moment the leak is gone.
    assert _task_class_leaks() == {}


def test_prose_about_a_task_class_is_not_a_leak():
    """The rule is about dispatch, not vocabulary.

    ``core/compare.py`` already explains a worked example in terms of a
    retrieval system, and it should keep being allowed to. If this test ever
    fails, the check has started policing English instead of code.
    """
    assert not LEAK_CANARY.exists(), f"an earlier run left {LEAK_CANARY} behind; delete it"
    LEAK_CANARY.write_text(PLANTED_PROSE, encoding="utf-8")
    try:
        assert _task_class_leaks() == {}
    finally:
        LEAK_CANARY.unlink()


def test_every_package_has_a_docstring():
    for path in sorted(SRC.rglob("__init__.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"{path.relative_to(SRC)} has no docstring"

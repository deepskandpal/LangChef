"""Shared plumbing for the commands.

``cli/`` holds no logic (see the layout in the README), but every command needs
the same four things — the workspace, its configuration, the pinned rubric, and
a provider — and needs to fail the same way when one is missing. That is what
this is: resolution and refusal, no arithmetic.
"""

from pathlib import Path

from langchef.core.emit import fail, say
from langchef.core.exits import Exit
from langchef.core.gates import rubric_gate, unmet
from langchef.judge import providers
from langchef.judge.example import Example
from langchef.judge.rubric import Rubric, RubricError
from langchef.judge.rubric import load as load_rubric_file
from langchef.workspace import config as config_mod
from langchef.workspace.formats import FormatError, read_jsonl
from langchef.workspace.paths import Workspace, WorkspaceError, find


def workspace() -> Workspace:
    """The nearest workspace, or a refusal that says how to make one."""
    try:
        return find()
    except WorkspaceError as exc:
        fail(Exit.ERROR, str(exc))


def settings() -> config_mod.Settings:
    try:
        return config_mod.load(workspace())
    except (FormatError, OSError) as exc:
        fail(Exit.ERROR, f"could not read the workspace configuration: {exc}")


def rubric(resolved: config_mod.Settings) -> Rubric:
    try:
        return load_rubric_file(resolved.rubric_path)
    except RubricError as exc:
        fail(Exit.ERROR, str(exc))


def require_approved_rubric(resolved: config_mod.Settings, pinned: Rubric) -> None:
    """Gate one. An unapproved or edited rubric stops the run at exit 2."""
    gate = rubric_gate(resolved.approved_rubric, pinned.ref, name=pinned.name)
    if unmet([gate]):
        fail(
            Exit.REFUSED,
            gate.remedy,
            gate=gate.to_dict(),
        )


def provider(resolved: config_mod.Settings) -> providers.Provider:
    try:
        return providers.resolve(resolved.judge.provider, cassettes=resolved.cassette_path)
    except providers.ProviderError as exc:
        fail(Exit.ERROR, str(exc))


def suite_path(resolved: config_mod.Settings, suite: str, arm: str | None = None) -> Path:
    """Where a suite's examples live.

    Each arm of an experiment answers the same questions differently, so the
    answers are per-arm files under one suite name: ``support.baseline.jsonl``,
    ``support.top-k-1.jsonl``. A suite with only one arm needs no suffix.
    """
    if arm:
        per_arm = resolved.workspace.goldens / f"{suite}.{arm}.jsonl"
        if per_arm.is_file():
            return per_arm
    return resolved.workspace.goldens / f"{suite}.jsonl"


def examples(resolved: config_mod.Settings, suite: str, arm: str | None = None) -> list[Example]:
    """Load one golden suite, or refuse with the path that was expected."""
    path = suite_path(resolved, suite, arm)
    try:
        rows = read_jsonl(path)
    except FormatError as exc:
        fail(Exit.ERROR, f"could not read goldens: {exc}")
    if not rows:
        fail(Exit.ERROR, f"{path} has no examples")
    try:
        return [Example.from_dict(row) for row in rows]
    except KeyError as exc:
        fail(Exit.ERROR, f"{path}: every example needs an example_id ({exc})")


def suites(resolved: config_mod.Settings) -> list[str]:
    directory = resolved.workspace.goldens
    if not directory.is_dir():
        return []
    return sorted({path.stem.split(".")[0] for path in directory.glob("*.jsonl")})


def only_suite(resolved: config_mod.Settings, suite: str | None) -> str:
    """The named suite, or the only one there is."""
    if suite:
        return suite
    found = suites(resolved)
    if len(found) == 1:
        return found[0]
    if not found:
        fail(Exit.ERROR, f"no golden suites in {resolved.workspace.goldens}")
    fail(Exit.ERROR, f"which suite? one of: {', '.join(found)} (pass --suite)")


def report_stats(label: str, stats: dict) -> None:
    say(f"{label}: " + "  ".join(f"{key}={value}" for key, value in stats.items()))

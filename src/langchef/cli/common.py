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


def require_judge(resolved: config_mod.Settings, verb: str) -> None:
    """Refuse the calibration commands on a task class that has no judge.

    Three of the four task classes have a hard target, so nothing judges them and
    there is nothing to calibrate: kappa between a hard label and itself is a
    number, and somebody will quote it. A number with no meaning is worse than a
    refusal, because a refusal is read once and a number is repeated
    (DECISIONS.md #12).

    Whether a class needs a judge is **pack knowledge**, declared per class in a
    ``pack.toml`` and carried here on the resolved ``DatasetSpec``. No list of
    class names lives in this function or anywhere under ``core/``; adding a
    fifth class is a new directory, not a patch to this refusal.

    The trace-collection path has no ``[dataset]`` table at all. It is judged by
    construction, so an absent spec passes.
    """
    spec = resolved.dataset
    if spec is None or spec.requires_judge:
        return
    fail(
        Exit.REFUSED,
        f"{spec.task_class} has a hard target, so there is no judge to {verb}. "
        "What this class does support: the paired comparison between two arms, "
        "the detection limit that says what the labels could have resolved, and "
        "the pre-registration and readout discipline around both.",
        task_class=spec.task_class,
        outcome_shape=spec.outcome_shape,
        requires_judge=False,
        available=["compare", "experiment design", "experiment approve", "experiment readout"],
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

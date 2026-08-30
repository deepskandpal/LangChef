"""The pack manifest schema.

A pack declares three things: the application class it serves, a rubric library,
and the **task classes** it knows how to evaluate. A task class is the shape of
one example — the fields a row carries, what a single example's outcome is, the
metrics reported for it, and whether scoring it needs a judge at all.

Task classes live here rather than in ``core/`` on purpose (DECISIONS.md #5,
settled for the four classes by #12). ``core/`` computes statistics over
outcomes and never learns the name of a task class. If it did, the core could
not be open-sourced separately from the packs, and adding a fifth class would be
a patch to the statistics engine rather than a new directory.
``tests/test_boundaries.py`` enforces that rather than trusting it.

``outcome_shape`` is the one field the deterministic core acts on, and it is the
whole of what a task class hands to the statistics. ``core/design.py`` sizes a
``binary`` outcome from the discordant rate and a ``continuous`` one from the
standard deviation of the paired differences, and says in as many words that the
caller resolves the class to a shape because the module may not know a class
exists (#68). This is that caller's half of the arrangement: the class is named
here, the shape is declared here, and ``core/`` only ever sees the shape.

``requires_judge`` is declared per class and never defaulted. Only a free-text
target needs a judge, and only a judge needs calibration; the three classes with
a hard target need neither. A class that quietly inherited "no judge" from a
default would be indistinguishable from a class whose author never thought about
it, which is precisely the distinction the field exists to record.
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ManifestError(ValueError):
    """A pack.toml is missing, malformed, or inconsistent with its directory."""


CLASS_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
# "<file>.py:<callable>", relative to the pack directory.
REPORTING = re.compile(r"^(?P<file>[A-Za-z0-9_][A-Za-z0-9_./-]*\.py):(?P<attr>[A-Za-z_]\w*)$")

# Every class is compared example by example against its pair in the other arm,
# so every schema has to carry the key that makes the pairing possible.
PAIRING_KEY = "example_id"

# The shapes ``core/`` can compare and size. Mirrored from ``core.design.OUTCOMES``
# rather than imported: the manifest is the pack layer's schema and a pack must be
# parseable without pulling in the numerical stack. ``tests/test_packs.py`` fails
# if the two lists ever disagree, which is the only way this could go wrong.
OUTCOME_SHAPES = ("binary", "continuous")


@dataclass(frozen=True)
class TaskClass:
    """One task class a pack serves.

    ``outcome`` is prose on purpose: it is what one example contributes to the
    comparison, written so that a reviewer can check the metric set against it
    without reading any code. ``outcome_shape`` is the machine-readable half of
    the same sentence, and the only part of a task class that reaches ``core/``.
    """

    name: str
    outcome: str
    outcome_shape: str
    requires_judge: bool
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    #: ``"<file>.py:<callable>"`` inside the pack, for metrics the core does not
    #: produce. Resolved by ``langchef.packs.loader.reporting``; absent when the
    #: class needs nothing beyond what the deterministic core already computes.
    reporting: str | None = None


@dataclass(frozen=True)
class Manifest:
    """A parsed and validated ``pack.toml``."""

    name: str
    version: str
    application_class: str
    description: str
    requires_langchef: str
    path: Path
    judges: tuple[str, ...] = ()
    playbooks: tuple[str, ...] = ()
    rubrics: tuple[str, ...] = ()
    task_classes: dict[str, TaskClass] = field(default_factory=dict)

    @property
    def ref(self) -> str:
        """The form written into ``pack.lock``."""
        return f"{self.name}@{self.version}"

    @property
    def rubric_library(self) -> Path:
        """Where this pack's rubrics live, empty or not."""
        return self.path / "rubrics"

    @property
    def needs_a_judge(self) -> bool:
        """True if any class this pack serves scores free text."""
        return any(tc.requires_judge for tc in self.task_classes.values())


REQUIRED = ("name", "version", "application_class", "description")


def _strings(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ManifestError(f"{where} must be a list of strings")
    return tuple(value)


def _task_class(name: str, raw: object, where: str, path: Path) -> TaskClass:
    """Validate one ``[task_classes.<name>]`` table."""
    here = f"{where}: [task_classes.{name}]"
    if not CLASS_NAME.match(name):
        raise ManifestError(f"{here} is not a usable class name (lowercase, digits, - and _)")
    if not isinstance(raw, dict):
        raise ManifestError(f"{here} must be a table")

    outcome = raw.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        raise ManifestError(f"{here} needs an outcome: what one example contributes")

    shape = raw.get("outcome_shape")
    if shape not in OUTCOME_SHAPES:
        raise ManifestError(
            f"{here} needs outcome_shape = one of {', '.join(OUTCOME_SHAPES)}, got {shape!r}. "
            "It is what the core sizes and compares this class with, and it will not guess: "
            "recall@k is not a pass rate, and sizing one as the other is confidently wrong"
        )

    requires_judge = raw.get("requires_judge")
    if not isinstance(requires_judge, bool):
        raise ManifestError(
            f"{here} must state requires_judge = true or false. "
            "Only a free-text target needs a judge, and only a judge needs calibration; "
            "leaving it unsaid hides which of the two this class is"
        )

    schema = raw.get("schema")
    if not isinstance(schema, dict):
        raise ManifestError(f"{here} needs a [task_classes.{name}.schema] table")
    required_fields = _strings(schema.get("required", []), f"{here}.schema.required")
    optional_fields = _strings(schema.get("optional", []), f"{here}.schema.optional")
    if not required_fields:
        raise ManifestError(f"{here}.schema.required is empty: a class with no fields has no rows")
    if PAIRING_KEY not in required_fields:
        raise ManifestError(
            f"{here}.schema.required must include {PAIRING_KEY!r} — "
            "every comparison is paired example by example"
        )
    overlap = sorted(set(required_fields) & set(optional_fields))
    if overlap:
        raise ManifestError(
            f"{here}.schema lists {', '.join(overlap)} as both required and optional"
        )

    metrics = _strings(raw.get("metrics", []), f"{here}.metrics")
    if not metrics:
        raise ManifestError(
            f"{here}.metrics is empty: a class nobody reports on cannot be read out"
        )

    reporting = raw.get("reporting")
    if reporting is not None:
        if not isinstance(reporting, str) or not REPORTING.match(reporting):
            raise ManifestError(
                f'{here}.reporting must look like "metrics.py:report", got {reporting!r}'
            )
        module = path / REPORTING.match(reporting)["file"]
        if not module.is_file():
            raise ManifestError(f"{here}.reporting points at {module}, which does not exist")

    return TaskClass(
        name=name,
        outcome=outcome.strip(),
        outcome_shape=shape,
        requires_judge=requires_judge,
        required_fields=required_fields,
        optional_fields=optional_fields,
        metrics=metrics,
        reporting=reporting,
    )


def parse(path: Path) -> Manifest:
    """Read and validate ``<path>/pack.toml``."""
    toml_path = path / "pack.toml"
    if not toml_path.is_file():
        raise ManifestError(f"no pack.toml in {path}")

    try:
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{toml_path}: {exc}") from exc

    pack = raw.get("pack")
    if not isinstance(pack, dict):
        raise ManifestError(f"{toml_path}: missing [pack] table")

    missing = [key for key in REQUIRED if not pack.get(key)]
    if missing:
        raise ManifestError(f"{toml_path}: [pack] missing {', '.join(missing)}")

    if pack["name"] != path.name:
        raise ManifestError(f"{toml_path}: pack name {pack['name']!r} != directory {path.name!r}")

    declared = raw.get("task_classes") or {}
    if not isinstance(declared, dict) or not declared:
        raise ManifestError(
            f"{toml_path}: no [task_classes.<name>] table. A pack that names no task class "
            "cannot be applied to a dataset, and the class belongs here rather than in core/"
        )
    task_classes = {
        name: _task_class(name, table, str(toml_path), path) for name, table in declared.items()
    }

    contents = raw.get("contents") or {}
    rubrics = _strings(contents.get("rubrics") or [], f"{toml_path}: [contents].rubrics")
    for rubric in rubrics:
        if not (path / "rubrics" / rubric).is_file():
            raise ManifestError(
                f"{toml_path}: rubric {rubric!r} is listed but not in {path}/rubrics"
            )

    return Manifest(
        name=pack["name"],
        version=str(pack["version"]),
        application_class=pack["application_class"],
        description=pack["description"],
        requires_langchef=str(pack.get("requires_langchef", ">=0.1.0")),
        path=path,
        judges=_strings(contents.get("judges") or [], f"{toml_path}: [contents].judges"),
        playbooks=_strings(contents.get("playbooks") or [], f"{toml_path}: [contents].playbooks"),
        rubrics=rubrics,
        task_classes=task_classes,
    )

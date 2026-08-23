"""Pre-registrations: the experiment design, on disk, before any traffic.

Gate two says the design is committed to git *before* the run and that changing
it afterwards invalidates the test. That only means something if the file is
reviewable by a person and tamper-evident to a machine, so a pre-registration is
TOML — the same format as the workspace config, for the same reason (DECISIONS
#4: text is the record) — and it carries a content digest.

Approval works exactly like the rubric's: a person records the digest they read.
Editing any part of the design changes the digest and the approval lapses on its
own. There is no revoke command because there is nothing to revoke — the
approval simply stops matching.
"""

import hashlib
import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from langchef.workspace.paths import Workspace

SAFE = re.compile(r"[^a-z0-9]+")


class ExperimentError(ValueError):
    """A pre-registration that is missing, malformed, or self-inconsistent."""


def slug(text: str) -> str:
    return SAFE.sub("-", text.lower()).strip("-") or "experiment"


def _toml_value(value) -> str:
    """Serialise one value. Deliberately narrow — this writes designs, not TOML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return "nan" if value != value else repr(value)
    if value is None:
        raise ExperimentError("a pre-registration cannot contain a null; omit the key instead")
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        inner = ",\n  ".join(_toml_value(v) for v in value)
        return f"[\n  {inner},\n]"
    text = str(value)
    if "\n" in text:
        escaped = text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return f'"""\n{escaped}"""'
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_toml(design: dict) -> str:
    """Render a design as reviewable TOML. Key order is fixed so diffs are small."""
    scalars = {k: v for k, v in design.items() if not isinstance(v, dict) and v is not None}
    tables = {k: v for k, v in design.items() if isinstance(v, dict)}

    lines = [
        "# LangChef pre-registration.",
        "#",
        "# Written before the run and reviewed like code. Editing anything below",
        "# changes the digest and revokes the approval, which is the point: an",
        "# experiment whose design moved after the traffic is not an experiment.",
        "",
        "[experiment]",
    ]
    for key in sorted(scalars):
        lines.append(f"{key} = {_toml_value(scalars[key])}")
    for name in sorted(tables):
        lines += ["", f"[{name}]"]
        for key in sorted(tables[name]):
            value = tables[name][key]
            if value is None:
                continue
            lines.append(f"{key} = {_toml_value(value)}")
    return "\n".join(lines) + "\n"


def digest(text: str) -> str:
    """Content hash of a pre-registration, ignoring the approval block appended later."""
    body = text.split("\n[approval]")[0]
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Experiment:
    """One pre-registration as it stands on disk."""

    experiment_id: str
    path: Path
    design: dict
    approval: dict
    text: str

    @property
    def digest(self) -> str:
        return digest(self.text)

    @property
    def approved_digest(self) -> str | None:
        return self.approval.get("digest")

    @property
    def approved(self) -> bool:
        return bool(self.approved_digest) and self.approved_digest == self.digest

    @property
    def ref(self) -> str:
        return f"{self.experiment_id}@{self.digest}"


def path_for(workspace: Workspace, experiment_id: str) -> Path:
    return workspace.root / "experiments" / f"{experiment_id}.toml"


def write(workspace: Workspace, experiment_id: str, design: dict) -> Experiment:
    """Write a proposed design. Refuses to clobber an existing pre-registration."""
    path = path_for(workspace, experiment_id)
    if path.exists():
        raise ExperimentError(
            f"{path} already exists — pass a different --id, or delete it deliberately. "
            "Overwriting a pre-registration silently is how one stops meaning anything."
        )
    payload = {
        **design,
        "experiment_id": experiment_id,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_toml(payload), encoding="utf-8")
    return load(workspace, experiment_id)


def load(workspace: Workspace, experiment_id: str) -> Experiment:
    path = path_for(workspace, experiment_id)
    if not path.is_file():
        raise ExperimentError(f"no pre-registration at {path}")
    text = path.read_text(encoding="utf-8")
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ExperimentError(f"{path}: {exc}") from exc
    design = dict(raw.get("experiment") or {})
    for name, table in raw.items():
        if name not in ("experiment", "approval"):
            design[name] = table
    return Experiment(
        experiment_id=experiment_id,
        path=path,
        design=design,
        approval=dict(raw.get("approval") or {}),
        text=text,
    )


def approve(workspace: Workspace, experiment_id: str, by: str = "human") -> Experiment:
    """Record a person's approval of the design exactly as it stands."""
    experiment = load(workspace, experiment_id)
    body = experiment.text.split("\n[approval]")[0].rstrip("\n")
    block = "\n".join(
        [
            body,
            "",
            "[approval]",
            f'digest = "{digest(experiment.text)}"',
            f'at = "{datetime.now(UTC).isoformat(timespec="seconds")}"',
            f'by = "{by}"',
            "",
        ]
    )
    experiment.path.write_text(block, encoding="utf-8")
    return load(workspace, experiment_id)


def every(workspace: Workspace) -> list[Experiment]:
    directory = workspace.root / "experiments"
    if not directory.is_dir():
        return []
    return [load(workspace, path.stem) for path in sorted(directory.glob("*.toml"))]

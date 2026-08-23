"""Run directories — one measurement, one folder, everything that produced it.

"No number without a run artifact" is a contract rule, so every figure a memo
quotes has to trace to a file under ``runs/<id>/``. That is only enforceable if
creating a run is the easy path, which is what this module is for.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchef.workspace.formats import read_json, write_json
from langchef.workspace.paths import Workspace

SAFE = re.compile(r"[^a-z0-9]+")
RUN_JSON = "run.json"


def slug(text: str) -> str:
    return SAFE.sub("-", text.lower()).strip("-") or "run"


def new_run_id(suite: str, arm: str | None = None, when: datetime | None = None) -> str:
    """A sortable, readable run id: ``suite-arm-20260823T120000Z``."""
    stamp = (when or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    parts = [slug(suite)] + ([slug(arm)] if arm else []) + [stamp]
    return "-".join(parts)


@dataclass
class Run:
    """One run directory and its manifest."""

    workspace: Workspace
    run_id: str
    suite: str
    kind: str = "judge"
    arm: str | None = None
    pin: dict | None = None
    stats: dict = field(default_factory=dict)
    created: str = ""

    @property
    def path(self) -> Path:
        return self.workspace.run_dir(self.run_id)

    def file(self, name: str) -> Path:
        return self.path / name

    def save(self) -> Path:
        self.created = self.created or datetime.now(UTC).isoformat(timespec="seconds")
        write_json(
            self.file(RUN_JSON),
            {
                "run_id": self.run_id,
                "suite": self.suite,
                "kind": self.kind,
                "arm": self.arm,
                "created": self.created,
                "pin": self.pin,
                "stats": self.stats,
            },
        )
        return self.path

    def artifact(self, name: str, payload: Any) -> Path:
        """Write one JSON artifact into the run directory and return its path."""
        path = self.file(name)
        write_json(path, payload)
        return path


def load(workspace: Workspace, run_id: str) -> Run:
    """Read a run manifest back."""
    raw = read_json(workspace.run_dir(run_id) / RUN_JSON)
    return Run(
        workspace=workspace,
        run_id=raw["run_id"],
        suite=raw["suite"],
        kind=raw.get("kind", "judge"),
        arm=raw.get("arm"),
        pin=raw.get("pin"),
        stats=raw.get("stats", {}),
        created=raw.get("created", ""),
    )


def latest(workspace: Workspace, suite: str | None = None, arm: str | None = None) -> Run | None:
    """The most recent run, optionally filtered. Ids sort chronologically."""
    if not workspace.runs.is_dir():
        return None
    for path in sorted(workspace.runs.iterdir(), reverse=True):
        if not (path / RUN_JSON).is_file():
            continue
        run = load(workspace, path.name)
        if suite and run.suite != suite:
            continue
        if arm and run.arm != arm:
            continue
        return run
    return None


def every(workspace: Workspace) -> list[Run]:
    """Every run in the workspace, newest first."""
    if not workspace.runs.is_dir():
        return []
    return [
        load(workspace, path.name)
        for path in sorted(workspace.runs.iterdir(), reverse=True)
        if (path / RUN_JSON).is_file()
    ]

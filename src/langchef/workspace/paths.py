"""Where everything lives.

The whole trust story is that a person can review a workspace in a pull request
(DECISIONS.md #4), so the layout is flat, named in English, and every file in it
is text a reviewer can read. The one binary is ``scores.parquet``, which is bulk
per-example output nobody reads by eye.

    evals/
      config.toml            what to judge, with which rubric, under which pin
      goldens/<suite>.jsonl  the examples
      rubrics/<name>.md      the judging criteria — reviewable, hashable
      labels/<judge>.jsonl   what a person said, the ground truth for calibration
      runs/<run-id>/         one measurement: pin, stats, scores, reports
      baselines/<suite>.json the run a comparison is made against
      memos/<run-id>.md      the decision memo
      ledger/ledger.jsonl    the persistent record across every run
      packs/                 workspace-local expertise packs
      .cache/                judgement cache — keyed, disposable, not in git
"""

from dataclasses import dataclass
from pathlib import Path

WORKSPACE_DIR = "evals"
CONFIG_NAME = "config.toml"


class WorkspaceError(RuntimeError):
    """No workspace here, or the one here is unusable."""


@dataclass(frozen=True)
class Workspace:
    """An ``evals/`` directory and everything under it."""

    root: Path

    @property
    def config(self) -> Path:
        return self.root / CONFIG_NAME

    @property
    def goldens(self) -> Path:
        return self.root / "goldens"

    @property
    def rubrics(self) -> Path:
        return self.root / "rubrics"

    @property
    def labels(self) -> Path:
        return self.root / "labels"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def baselines(self) -> Path:
        return self.root / "baselines"

    @property
    def memos(self) -> Path:
        return self.root / "memos"

    @property
    def ledger(self) -> Path:
        return self.root / "ledger" / "ledger.jsonl"

    @property
    def packs(self) -> Path:
        return self.root / "packs"

    @property
    def cache(self) -> Path:
        return self.root / ".cache" / "judgements.jsonl"

    def run_dir(self, run_id: str) -> Path:
        return self.runs / run_id

    def directories(self) -> list[Path]:
        """Every directory ``init`` creates, in the order it reports them."""
        return [
            self.goldens,
            self.rubrics,
            self.labels,
            self.runs,
            self.baselines,
            self.memos,
            self.ledger.parent,
            self.packs,
        ]

    def exists(self) -> bool:
        return self.config.is_file()


def find(start: Path | None = None) -> Workspace:
    """The nearest workspace at or above ``start``.

    Walking up means the CLI works from anywhere in a repository, the way git
    does, rather than only from the directory that happens to hold ``evals/``.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        workspace = Workspace(candidate / WORKSPACE_DIR)
        if workspace.exists():
            return workspace
    raise WorkspaceError(
        f"no {WORKSPACE_DIR}/{CONFIG_NAME} at or above {here} — run `langchef init` first"
    )

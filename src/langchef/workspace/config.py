"""``evals/config.toml``, resolved.

One place that knows what the file means, so the CLI commands stay thin and the
defaults do not drift between them. Unknown keys are ignored rather than
rejected: a workspace written by a newer LangChef should still be readable by an
older one, and a hard failure on an unknown key makes every upgrade a breaking
change.
"""

from dataclasses import dataclass
from pathlib import Path

from langchef.workspace.dataset import DatasetSpec, spec_from_config
from langchef.workspace.formats import read_toml
from langchef.workspace.paths import Workspace


@dataclass(frozen=True)
class JudgeSettings:
    """How this workspace scores an example."""

    provider: str = "containment"
    cheap_model: str = "containment/v2"
    strong_model: str | None = None
    escalate_below: float = 0.6
    rubric: str = "answer-quality"
    cassettes: str | None = None
    # Costing a design needs a price. There is no sane default across
    # providers, so an absent price is reported as absent rather than guessed.
    price_per_call_usd: float | None = None


@dataclass(frozen=True)
class Settings:
    """The whole configuration, with the workspace it came from."""

    workspace: Workspace
    name: str
    application_class: str
    pack: str | None
    judge: JudgeSettings
    approved_rubric: str | None
    level: float
    # The [dataset] declaration, when the workspace points at a file somebody
    # already owns. None for the trace-collection path, which is unaffected.
    dataset: DatasetSpec | None = None

    @property
    def rubric_path(self) -> Path:
        return self.workspace.rubrics / f"{self.judge.rubric}.md"

    @property
    def cassette_path(self) -> Path | None:
        if not self.judge.cassettes:
            return None
        return self.workspace.root / self.judge.cassettes


def load(workspace: Workspace) -> Settings:
    """Read and resolve the workspace configuration."""
    raw = read_toml(workspace.config)
    ws = raw.get("workspace") or {}
    judge = raw.get("judge") or {}
    approvals = raw.get("approvals") or {}
    compare = raw.get("compare") or {}
    dataset = spec_from_config(raw, workspace.root)

    return Settings(
        workspace=workspace,
        name=str(ws.get("name", workspace.root.parent.name)),
        application_class=str(ws.get("application_class", "genai-rag")),
        pack=ws.get("pack"),
        judge=JudgeSettings(
            provider=str(judge.get("provider", "containment")),
            cheap_model=str(judge.get("cheap_model", "containment/v2")),
            strong_model=judge.get("strong_model"),
            escalate_below=float(judge.get("escalate_below", 0.6)),
            rubric=str(judge.get("rubric", "answer-quality")),
            cassettes=judge.get("cassettes"),
            price_per_call_usd=(
                float(judge["price_per_call_usd"])
                if judge.get("price_per_call_usd") is not None
                else None
            ),
        ),
        approved_rubric=approvals.get("rubric"),
        level=float(compare.get("level", 0.95)),
        dataset=dataset,
    )


def approve_rubric(workspace: Workspace, ref: str) -> None:
    """Record a human approval of a rubric, in place, without reformatting the file.

    Deliberately a line edit rather than a TOML round-trip: config.toml carries
    comments explaining every gate, and a writer that drops them would make the
    file worse each time a person approved something.
    """
    text = workspace.config.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_line = f'rubric = "{ref}"'

    in_approvals = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_approvals = stripped == "[approvals]"
            continue
        if in_approvals and (stripped.startswith("rubric =") or stripped.startswith("# rubric =")):
            lines[index] = new_line
            workspace.config.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return

    if "[approvals]" not in text:
        lines += ["", "[approvals]"]
    lines.append(new_line)
    workspace.config.write_text("\n".join(lines) + "\n", encoding="utf-8")

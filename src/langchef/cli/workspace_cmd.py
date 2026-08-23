"""``langchef init`` and ``langchef approve`` — creating a workspace and signing off a rubric."""

from pathlib import Path
from typing import Annotated

import typer

from langchef.cli import common
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.core.gates import rubric_gate
from langchef.workspace import config as config_mod
from langchef.workspace import scaffold
from langchef.workspace.paths import WORKSPACE_DIR, Workspace

approve_app = typer.Typer(help="Record a human approval. Gates are exit codes, not prompts.")


def init(
    name: Annotated[str | None, typer.Option("--name", help="Workspace name.")] = None,
    application_class: Annotated[
        str, typer.Option("--class", help="What kind of application this evaluates.")
    ] = "genai-rag",
    directory: Annotated[
        Path | None, typer.Option("--dir", help="Where to create evals/. Defaults to here.")
    ] = None,
) -> None:
    """Scaffold an eval workspace in the current directory."""
    root = (directory or Path.cwd()).resolve()
    workspace = Workspace(root / WORKSPACE_DIR)
    already = workspace.exists()

    written = scaffold.create(
        workspace,
        name=name or root.name,
        application_class=application_class,
    )
    emit(
        {
            "ok": True,
            "workspace": str(workspace.root),
            "created": written,
            "already_present": already,
        }
    )
    if already and not written:
        say(f"workspace already initialised at {workspace.root}")
    else:
        say(f"workspace at {workspace.root}")
        for path in written:
            say(f"  + {path}")
        say("")
        say("Next: add goldens to evals/goldens/<suite>.jsonl, review the rubric,")
        say("then `langchef approve rubric answer-quality` to open gate one.")
    raise typer.Exit(Exit.OK)


@approve_app.command("rubric")
def approve_rubric(
    name: Annotated[
        str | None, typer.Argument(help="Rubric name. Defaults to the configured one.")
    ] = None,
) -> None:
    """Approve the rubric as it stands. Editing it afterwards revokes this."""
    resolved = common.settings()
    if name and name != resolved.judge.rubric:
        fail(
            Exit.ERROR,
            f"this workspace is configured for rubric {resolved.judge.rubric!r}, not {name!r}",
        )
    pinned = common.rubric(resolved)
    before = resolved.approved_rubric

    config_mod.approve_rubric(resolved.workspace, pinned.ref)
    gate = rubric_gate(pinned.ref, pinned.ref, name=pinned.name)
    emit(
        {
            "ok": True,
            "rubric": pinned.ref,
            "criteria": list(pinned.criteria),
            "previous": before,
            "gate": gate.to_dict(),
        }
    )
    say(f"approved {pinned.ref}")
    for criterion in pinned.criteria:
        say(f"  - {criterion}")
    if before and before != pinned.ref:
        say(f"(was {before})")
    raise typer.Exit(Exit.OK)

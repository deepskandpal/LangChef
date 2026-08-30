"""The ``langchef`` command.

Every command writes one JSON document to stdout and its narration to stderr.
``--help`` is the single exception: it is for people.
"""

import platform
import shutil
import sys
from typing import Annotated

import typer

from langchef import __version__
from langchef.cli.calibrate_cmd import calibrate_app, label_app
from langchef.cli.design_cmd import experiment_app
from langchef.cli.experiment_cmd import baseline_app, compare
from langchef.cli.judge_cmd import judge_app
from langchef.cli.memo_cmd import ledger_app, memo_app
from langchef.cli.power_cmd import app as power_app
from langchef.cli.workspace_cmd import approve_app, init
from langchef.core import contract as contract_mod
from langchef.core.credentials import present as credentials_present
from langchef.core.emit import emit, say
from langchef.core.exits import Exit
from langchef.packs import discover, search_path
from langchef.packs.loader import ENV_VAR as PACK_PATH_VAR
from langchef.workspace.paths import WorkspaceError
from langchef.workspace.paths import find as find_workspace

app = typer.Typer(
    name="langchef",
    help="An installed eval engineer. JSON to stdout, narration to stderr.",
    no_args_is_help=True,
    add_completion=False,
)
packs_app = typer.Typer(help="Expertise packs.", no_args_is_help=True)
app.add_typer(packs_app, name="packs")

# The commands live in their own modules; this file assembles them and holds
# nothing but the two that describe the tool itself.
app.command("init")(init)
app.command("compare")(compare)
app.add_typer(judge_app, name="judge")
app.add_typer(label_app, name="label")
app.add_typer(calibrate_app, name="calibrate")
app.add_typer(baseline_app, name="baseline")
app.add_typer(memo_app, name="memo")
app.add_typer(ledger_app, name="ledger")
app.add_typer(approve_app, name="approve")
app.add_typer(experiment_app, name="experiment")
app.add_typer(power_app, name="power")

SUPPORTED_PYTHON = ((3, 12), (3, 13))


def _version_callback(value: bool) -> None:
    if value:
        emit({"name": "langchef", "version": __version__})
        say(f"langchef {__version__}")
        raise typer.Exit(Exit.OK)


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Print the version."
        ),
    ] = False,
) -> None:
    """LangChef root command."""


@app.command()
def contract() -> None:
    """Emit the agent contract: commands, exit codes, rules."""
    payload = contract_mod.as_dict()
    emit(payload)
    done = sum(1 for c in payload["commands"] if c["implemented"])
    total = len(payload["commands"])
    say(f"agent contract v{payload['version']}: {done}/{total} commands implemented")


@app.command()
def doctor() -> None:
    """Verify environment, credentials, pins and pack resolution."""
    version_info = sys.version_info[:2]
    try:
        workspace_root = str(find_workspace().root)
    except WorkspaceError:
        workspace_root = None
    packs = discover()
    credentials = credentials_present()
    credential_names = ", ".join(credentials) or "none"

    checks = [
        {
            "name": "python",
            "required": True,
            "ok": version_info in SUPPORTED_PYTHON,
            "detail": f"{platform.python_version()} (supported: 3.12, 3.13)",
        },
        {
            "name": "uv",
            "required": False,
            "ok": shutil.which("uv") is not None,
            "detail": shutil.which("uv") or "not on PATH",
        },
        {
            "name": "packs",
            "required": True,
            "ok": bool(packs),
            "detail": ", ".join(p.ref for p in packs)
            or f"none resolvable — set {PACK_PATH_VAR} or install an expertise pack",
        },
        {
            "name": "workspace",
            "required": False,
            "ok": workspace_root is not None,
            "detail": f"{workspace_root}" if workspace_root else "none found — run langchef init",
        },
        {
            "name": "credentials",
            "required": False,
            "ok": True,
            "detail": f"{len(credentials)} provider key(s) present: {credential_names}",
        },
    ]

    ok = all(check["ok"] for check in checks if check["required"])
    emit(
        {
            "ok": ok,
            "version": __version__,
            "python": platform.python_version(),
            "workspace": workspace_root,
            "pack_search_path": [str(p) for p in search_path()],
            "packs": [p.ref for p in packs],
            "credentials_present": credentials,
            "checks": checks,
        }
    )
    for check in checks:
        if check["ok"]:
            mark = "ok  "
        elif check["required"]:
            mark = "FAIL"
        else:
            mark = "note"  # informational: a soft check that has not been met yet
        say(f"{mark} {check['name']:<12} {check['detail']}")
    say("doctor: ok" if ok else "doctor: a required check failed")
    raise typer.Exit(Exit.OK if ok else Exit.ERROR)


@packs_app.command("list")
def packs_list() -> None:
    """List every pack resolvable on the search path."""
    packs = discover()
    emit(
        {
            "ok": True,
            "search_path": [str(p) for p in search_path()],
            "packs": [
                {
                    "name": p.name,
                    "version": p.version,
                    "application_class": p.application_class,
                    "description": p.description,
                    "requires_langchef": p.requires_langchef,
                    "path": str(p.path),
                }
                for p in packs
            ],
        }
    )
    say(f"{len(packs)} pack(s) on the search path")
    for p in packs:
        say(f"  {p.ref:<20} {p.application_class:<12} {p.description}")


if __name__ == "__main__":  # pragma: no cover - module entry point
    app()

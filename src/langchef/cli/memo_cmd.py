"""``langchef memo render`` and ``langchef ledger`` — the written record."""

from typing import Annotated

import typer

from langchef.cli import common
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.render.memo import render
from langchef.workspace import ledger as ledger_mod
from langchef.workspace import runs
from langchef.workspace.formats import FormatError, read_json, write_text

memo_app = typer.Typer(help="Decision memos.", no_args_is_help=True)
ledger_app = typer.Typer(help="The persistent record.", no_args_is_help=True)


def _maybe(path):
    try:
        return read_json(path) if path.is_file() else None
    except FormatError:
        return None


@memo_app.command("render")
def memo_render(
    run_id: Annotated[str | None, typer.Option("--run", help="Run to write up.")] = None,
) -> None:
    """Write the decision memo for a run.

    Calibration is looked up from the run itself, and if it has none, from the
    last calibration in the ledger — with the memo saying which. A memo that
    quietly omits the judge's agreement is the failure mode this whole product
    exists to prevent.
    """
    resolved = common.settings()
    run = runs.load(resolved.workspace, run_id) if run_id else runs.latest(resolved.workspace)
    if run is None:
        fail(Exit.ERROR, "no runs yet — start with `langchef judge run`")

    calibration = _maybe(run.file("calibration.json"))
    borrowed = None
    if calibration is None:
        last = ledger_mod.last_calibration(resolved.workspace.ledger)
        if last and last.get("run_id"):
            borrowed = last["run_id"]
            calibration = _maybe(resolved.workspace.run_dir(borrowed) / "calibration.json")

    comparison = _maybe(run.file("compare.json"))
    calibration_dir = resolved.workspace.run_dir(borrowed) if borrowed else run.path
    artifacts = {}
    if calibration:
        path = calibration_dir / "calibration.json"
        artifacts["calibration"] = str(path.relative_to(resolved.workspace.root.parent))
    if comparison:
        path = run.file("compare.json")
        artifacts["compare"] = str(path.relative_to(resolved.workspace.root.parent))

    text = render(
        run_id=run.run_id,
        suite=run.suite,
        comparison=comparison,
        calibration=calibration,
        taxonomy=(calibration or {}).get("taxonomy"),
        pin=run.pin,
        artifacts=artifacts,
    )
    if borrowed:
        text += (
            f"\n> Calibration above is from run `{borrowed}`, not this one. "
            "Re-run `langchef calibrate report` against this run to refresh it.\n"
        )

    path = resolved.workspace.memos / f"{run.run_id}.md"
    write_text(path, text)
    emit(
        {
            "ok": True,
            "run_id": run.run_id,
            "memo": str(path),
            "has_calibration": calibration is not None,
            "calibration_borrowed_from": borrowed,
            "has_comparison": comparison is not None,
            "bytes": len(text),
        }
    )
    say(f"memo -> {path}")
    if calibration is None:
        say("  warning: no calibration for this judge — the memo says so in full")
    raise typer.Exit(Exit.OK)


@ledger_app.command("query")
def ledger_query(
    kind: Annotated[
        str | None,
        typer.Option("--kind", help="calibration|run|experiment|decision|note"),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="How many entries.")] = 20,
) -> None:
    """Read the record, newest first."""
    resolved = common.settings()
    entries = ledger_mod.read(resolved.workspace.ledger, kind=kind, limit=limit)
    emit({"ok": True, "entries": entries, "count": len(entries)})
    if not entries:
        say("ledger is empty")
    for entry in entries:
        say(f"{entry['at']}  {entry['kind']:<12} {entry['summary']}")
    raise typer.Exit(Exit.OK)


@ledger_app.command("append")
def ledger_append(
    summary: Annotated[str, typer.Argument(help="What happened.")],
    kind: Annotated[str, typer.Option("--kind", help="Entry kind.")] = "note",
) -> None:
    """Add an entry. Entries are never edited; a correction is a new entry."""
    resolved = common.settings()
    try:
        entry = ledger_mod.append(resolved.workspace.ledger, kind, summary)
    except ledger_mod.LedgerError as exc:
        fail(Exit.ERROR, str(exc))
    emit({"ok": True, "entry": entry})
    say(f"{entry['at']}  {entry['kind']:<12} {entry['summary']}")
    raise typer.Exit(Exit.OK)

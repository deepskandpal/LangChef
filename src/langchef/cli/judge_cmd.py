"""``langchef judge run`` — score a golden suite against the pinned rubric."""

from typing import Annotated

import typer

from langchef.cli import common
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.judge import providers, runner
from langchef.judge.cache import Cache
from langchef.workspace import ledger, runs
from langchef.workspace.formats import write_scores

judge_app = typer.Typer(help="Run a judge over a suite.", no_args_is_help=True)


@judge_app.command("run")
def judge_run(
    suite: Annotated[str | None, typer.Option("--suite", help="Golden suite name.")] = None,
    arm: Annotated[
        str | None, typer.Option("--arm", help="Label this run, e.g. baseline or variant.")
    ] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Override the run id.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Score at most this many.")] = 0,
) -> None:
    """Score every golden and write the run directory."""
    resolved = common.settings()
    pinned = common.rubric(resolved)
    common.require_approved_rubric(resolved, pinned)

    name = common.only_suite(resolved, suite)
    batch = common.examples(resolved, name, arm)
    if limit > 0:
        batch = batch[:limit]

    backend = common.provider(resolved)
    cache = Cache(resolved.workspace.cache)
    try:
        result = runner.run(
            batch,
            pinned,
            backend,
            cheap_model=resolved.judge.cheap_model,
            cache=cache,
            strong_model=resolved.judge.strong_model,
            escalate_below=resolved.judge.escalate_below,
        )
    except providers.ProviderError as exc:
        fail(Exit.ERROR, str(exc))

    run = runs.Run(
        workspace=resolved.workspace,
        run_id=run_id or runs.new_run_id(name, arm),
        suite=name,
        kind="judge",
        arm=arm,
        pin=result.pin.to_dict(),
        stats=result.stats,
    )
    run.save()

    by_id = {example.example_id: example for example in batch}
    rows = [
        {
            **judgement.to_dict(),
            **{f"slice_{key}": value for key, value in by_id[judgement.example_id].slices.items()},
        }
        for judgement in result.judgements
    ]
    scores_path = run.file("scores.parquet")
    write_scores(scores_path, rows)

    ledger.append(
        resolved.workspace.ledger,
        "run",
        f"{name}{f' ({arm})' if arm else ''}: {result.stats['pass']}/{result.stats['n']} passed",
        run_id=run.run_id,
        pin=result.pin.to_dict(),
        stats=result.stats,
    )

    emit(
        {
            "ok": True,
            "run_id": run.run_id,
            "suite": name,
            "arm": arm,
            "pin": result.pin.to_dict(),
            "stats": result.stats,
            "artifacts": {
                "run": str(run.file("run.json")),
                "scores": str(scores_path),
            },
        }
    )
    say(f"run {run.run_id}")
    common.report_stats("judge", result.stats)
    say(f"  scores -> {scores_path}")
    raise typer.Exit(Exit.OK)

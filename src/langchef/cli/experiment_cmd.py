"""``langchef compare`` and ``langchef baseline`` — the experiment half.

A comparison is only a comparison if both arms were measured the same way, so
the first thing this does is check the pins and exit 5 if they moved. Everything
after that is paired arithmetic in ``core``.
"""

from typing import Annotated

import typer

from langchef.cli import common
from langchef.core.compare import compare as compare_arms
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.judge.runner import Pin, PinMismatch, check_pin
from langchef.workspace import ledger, runs
from langchef.workspace.formats import FormatError, read_json, read_scores, write_json

baseline_app = typer.Typer(help="The run a comparison is made against.", no_args_is_help=True)


def _load(resolved, run_id: str, what: str):
    try:
        return runs.load(resolved.workspace, run_id)
    except FormatError:
        fail(Exit.ERROR, f"no such {what} run: {run_id}")


def _verdicts(run) -> dict[str, str]:
    try:
        rows = read_scores(run.file("scores.parquet"))
    except FormatError as exc:
        fail(Exit.ERROR, str(exc))
    return {row["example_id"]: row["verdict"] for row in rows}


def _pinned_baseline(resolved, suite: str) -> str | None:
    path = resolved.workspace.baselines / f"{suite}.json"
    if not path.is_file():
        return None
    return read_json(path).get("run_id")


@baseline_app.command("set")
def baseline_set(
    run_id: Annotated[str | None, typer.Option("--run", help="Run to pin.")] = None,
) -> None:
    """Pin a run as the reference every later comparison is made against."""
    resolved = common.settings()
    run = _load(resolved, run_id, "baseline") if run_id else runs.latest(resolved.workspace)
    if run is None:
        fail(Exit.ERROR, "no runs yet — start with `langchef judge run`")

    path = resolved.workspace.baselines / f"{run.suite}.json"
    write_json(path, {"run_id": run.run_id, "suite": run.suite, "pin": run.pin, "stats": run.stats})
    emit({"ok": True, "suite": run.suite, "run_id": run.run_id, "baseline": str(path)})
    say(f"baseline for {run.suite} is now {run.run_id}")
    raise typer.Exit(Exit.OK)


@baseline_app.command("show")
def baseline_show(
    suite: Annotated[str | None, typer.Option("--suite", help="Suite name.")] = None,
) -> None:
    """Show the pinned baseline."""
    resolved = common.settings()
    name = common.only_suite(resolved, suite)
    path = resolved.workspace.baselines / f"{name}.json"
    if not path.is_file():
        fail(Exit.ERROR, f"no baseline pinned for {name} — run `langchef baseline set`")
    payload = read_json(path)
    emit({"ok": True, **payload})
    say(f"{name}: {payload['run_id']}")
    raise typer.Exit(Exit.OK)


def compare(
    baseline: Annotated[str | None, typer.Option("--baseline", help="Baseline run id.")] = None,
    variant: Annotated[str | None, typer.Option("--variant", help="Variant run id.")] = None,
    suite: Annotated[str | None, typer.Option("--suite", help="Suite name.")] = None,
) -> None:
    """Baseline against variant on the goldens they share."""
    resolved = common.settings()
    name = common.only_suite(resolved, suite)

    baseline_id = baseline or _pinned_baseline(resolved, name)
    if not baseline_id:
        fail(
            Exit.ERROR,
            f"no baseline for {name} — pass --baseline, or pin one with `langchef baseline set`",
        )
    baseline_run = _load(resolved, baseline_id, "baseline")

    if variant:
        variant_run = _load(resolved, variant, "variant")
    else:
        # for_experiment() rather than latest(): latest() is a thin wrapper over
        # it that discards the count, and the count is the whole disclosure.
        # #12 -- one resolution path, so the next version of this bug cannot be
        # written into a second one.
        candidates = runs.for_experiment(resolved.workspace, suite=name, arm="variant")
        variant_run = candidates[0] if candidates else None
        if variant_run is None or variant_run.run_id == baseline_run.run_id:
            fail(Exit.ERROR, "no variant run to compare — pass --variant")
        if len(candidates) > 1:
            # A disclosure, not a refusal. `readout` refuses here (#13) because
            # it is gate two; `compare` is the exploratory command, where
            # re-running an arm is exactly what you should be doing. Inside a
            # gate ambiguity is a refusal; outside one it is a disclosure.
            # Silence is neither -- and with a warm cache each re-run is free,
            # so an arm accumulates runs faster than anyone tracks.
            others = len(candidates) - 1
            say(
                f"langchef: compared {variant_run.run_id}, the newest of "
                f"{len(candidates)} runs for arm 'variant' in suite {name!r} "
                f"({others} other{'' if others == 1 else 's'} not compared). "
                "Pass --variant to choose.",
            )

    try:
        check_pin(Pin.from_dict(baseline_run.pin or {}), Pin.from_dict(variant_run.pin or {}))
    except PinMismatch as exc:
        fail(
            Exit.PIN_MISMATCH,
            f"{exc} — these are two measurements, not a comparison. "
            "Re-run the older arm under the current pin.",
            moved=exc.moved,
            baseline=baseline_run.run_id,
            variant=variant_run.run_id,
        )
    except KeyError:
        fail(Exit.ERROR, "one of these runs has no pin recorded; re-run it")

    left, right = _verdicts(baseline_run), _verdicts(variant_run)
    shared = sorted(set(left) & set(right))
    if not shared:
        fail(Exit.ERROR, "the two runs share no goldens")

    result = compare_arms(
        [left[key] for key in shared],
        [right[key] for key in shared],
        level=resolved.level,
    )
    payload = {
        **result.to_dict(),
        "suite": name,
        "baseline_run": baseline_run.run_id,
        "variant_run": variant_run.run_id,
        "pin": variant_run.pin,
        "dropped": len(set(left) ^ set(right)),
    }
    artifact = variant_run.artifact("compare.json", payload)

    ledger.append(
        resolved.workspace.ledger,
        "experiment",
        f"{name}: {result.verdict} ({result.difference:+.1%})",
        baseline_run=baseline_run.run_id,
        variant_run=variant_run.run_id,
        verdict=result.verdict,
        difference=result.difference,
        p_value=result.p_value,
    )

    emit({"ok": True, **payload, "artifact": str(artifact)})
    say(f"{baseline_run.run_id} -> {variant_run.run_id} on {len(shared)} shared golden(s)")
    say(f"  baseline {result.baseline_rate:.1%}   variant {result.variant_rate:.1%}")
    say(
        f"  difference {result.difference:+.1%} "
        f"[{result.interval.lo:+.1%}, {result.interval.hi:+.1%}]  p={result.p_value:.4f}"
    )
    say(f"  {result.verdict.upper()}")
    if result.inconclusive:
        say(f"  (smallest effect this run could have seen: {result.mde:.1%})")
    say(f"  -> {artifact}")
    raise typer.Exit(Exit.OK)

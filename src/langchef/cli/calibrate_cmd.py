"""``langchef label`` and ``langchef calibrate`` — the M1 loop.

Score a suite, pick what a person should look at, take their labels back, and
report how far the judge can be trusted. Nothing here talks to a model: the
judgements were produced by ``judge run`` and the labels by a person.
"""

from pathlib import Path
from typing import Annotated

import typer

from langchef.cli import common
from langchef.core import sampling
from langchef.core.agreement import agreement
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.core.taxonomy import Judgement as Paired
from langchef.core.taxonomy import summarise
from langchef.workspace import ledger, runs
from langchef.workspace.formats import FormatError, read_jsonl, read_scores, write_jsonl

label_app = typer.Typer(help="Human labels — the ground truth.", no_args_is_help=True)
calibrate_app = typer.Typer(help="How far the judge can be trusted.", no_args_is_help=True)


def _run_or_latest(resolved, run_id: str | None):
    if run_id:
        try:
            return runs.load(resolved.workspace, run_id)
        except FormatError as exc:
            fail(Exit.ERROR, f"no such run: {exc}")
    run = runs.latest(resolved.workspace, arm=None)
    if run is None:
        fail(Exit.ERROR, "no runs yet — start with `langchef judge run`")
    return run


def _scores(run) -> list[dict]:
    path = run.file("scores.parquet")
    try:
        return read_scores(path)
    except FormatError as exc:
        fail(Exit.ERROR, str(exc))


@label_app.command("plan")
def label_plan(
    run_id: Annotated[str | None, typer.Option("--run", help="Run to plan from.")] = None,
    budget: Annotated[int, typer.Option("--budget", help="How many labels to ask for.")] = 40,
    seed: Annotated[int, typer.Option("--seed", help="Tie-break seed.")] = 0,
) -> None:
    """Choose the examples worth a person's attention, balanced across verdicts."""
    resolved = common.settings()
    run = _run_or_latest(resolved, run_id)
    rows = _scores(run)

    selections = sampling.plan(rows, budget=budget, seed=seed)
    if not selections:
        fail(Exit.ERROR, f"nothing to plan from in run {run.run_id}")

    by_id = {row["example_id"]: row for row in rows}
    examples = {e.example_id: e for e in common.examples(resolved, run.suite, run.arm)}
    todo = resolved.workspace.labels / f"{resolved.judge.rubric}.todo.jsonl"
    write_jsonl(
        todo,
        [
            {
                **selection.to_dict(),
                "question": getattr(examples.get(selection.example_id), "question", ""),
                "answer": getattr(examples.get(selection.example_id), "answer", ""),
                "expected": getattr(examples.get(selection.example_id), "expected", None),
                "judge_verdict": by_id[selection.example_id]["verdict"],
                "verdict": None,
                "run_id": run.run_id,
            }
            for selection in selections
        ],
    )
    summary = sampling.summarise(selections, rows)
    emit({"ok": True, "run_id": run.run_id, "todo": str(todo), **summary})
    say(f"{summary['selected']} of {summary['available']} examples planned for labelling")
    say(f"  by stratum: {summary['by_stratum']}")
    say(f"  -> {todo}")
    say('Fill in the null "verdict" fields with "pass" or "fail", then:')
    say(f"  langchef label import {todo}")
    raise typer.Exit(Exit.OK)


@label_app.command("import")
def label_import(
    path: Annotated[Path, typer.Argument(help="JSONL of {example_id, verdict}.")],
) -> None:
    """Ingest returned human labels."""
    resolved = common.settings()
    try:
        rows = read_jsonl(path)
    except FormatError as exc:
        fail(Exit.ERROR, str(exc))

    labelled, skipped = [], 0
    for row in rows:
        verdict = row.get("verdict")
        if verdict not in ("pass", "fail"):
            skipped += 1
            continue
        labelled.append(
            {
                "example_id": str(row["example_id"]),
                "verdict": verdict,
                "note": row.get("note", ""),
            }
        )
    if not labelled:
        fail(
            Exit.ERROR,
            f"{path} has no usable labels — each row needs a verdict of 'pass' or 'fail' "
            f"({skipped} row(s) had none)",
        )

    destination = resolved.workspace.labels / f"{resolved.judge.rubric}.jsonl"
    prior = read_jsonl(destination) if destination.is_file() else []
    existing = {row["example_id"]: row for row in prior}
    existing.update({row["example_id"]: row for row in labelled})
    written = write_jsonl(destination, [existing[key] for key in sorted(existing)])

    emit(
        {
            "ok": True,
            "imported": len(labelled),
            "skipped": skipped,
            "total": written,
            "labels": str(destination),
        }
    )
    say(f"imported {len(labelled)} label(s), {skipped} unlabelled row(s) skipped")
    say(f"  {written} label(s) on file -> {destination}")
    raise typer.Exit(Exit.OK)


@calibrate_app.command("report")
def calibrate_report(
    run_id: Annotated[str | None, typer.Option("--run", help="Run to calibrate.")] = None,
) -> None:
    """Judge against human: agreement, intervals, and where they parted."""
    resolved = common.settings()
    run = _run_or_latest(resolved, run_id)
    rows = _scores(run)

    label_path = resolved.workspace.labels / f"{resolved.judge.rubric}.jsonl"
    if not label_path.is_file():
        fail(
            Exit.ERROR,
            f"no human labels at {label_path} — run `langchef label plan` first, "
            "have a person fill it in, then `langchef label import`",
        )
    labels = {row["example_id"]: row["verdict"] for row in read_jsonl(label_path)}
    by_id = {row["example_id"]: row for row in rows}

    paired_ids = sorted(set(labels) & set(by_id))
    if not paired_ids:
        fail(
            Exit.ERROR,
            f"none of the {len(labels)} labels match an example in run {run.run_id}",
        )

    human = [labels[example_id] for example_id in paired_ids]
    judge = [by_id[example_id]["verdict"] for example_id in paired_ids]
    report = agreement(human, judge, level=resolved.level)

    paired = [
        Paired(
            example_id=example_id,
            human=labels[example_id],
            judge=by_id[example_id]["verdict"],
            criterion=by_id[example_id].get("criterion"),
            slices={
                key[len("slice_") :]: value
                for key, value in by_id[example_id].items()
                if key.startswith("slice_") and value is not None
            },
        )
        for example_id in paired_ids
    ]
    taxonomy = summarise(paired, level=resolved.level)

    payload = {**report.to_dict(), "run_id": run.run_id, "pin": run.pin, "taxonomy": taxonomy}
    artifact = run.artifact("calibration.json", payload)

    ledger.append(
        resolved.workspace.ledger,
        "calibration",
        f"kappa {report.kappa:.2f} on {report.confusion.n} labels",
        run_id=run.run_id,
        kappa=report.kappa,
        tpr=report.tpr.value,
        fpr=report.fpr,
        n=report.confusion.n,
        pin=run.pin,
    )

    emit({"ok": True, **payload, "artifact": str(artifact)})
    say(f"calibration for {run.run_id} on {report.confusion.n} labelled example(s)")
    interval = report.kappa_interval
    say(f"  kappa      {report.kappa:.2f}  {interval.lo:.2f}..{interval.hi:.2f}")
    say(f"  TPR        {report.tpr.value:.1%}  ({report.tpr.k}/{report.tpr.n})")
    say(f"  FPR        {report.fpr:.1%}")
    say(f"  disagreed  {taxonomy['disagreements']} ({taxonomy['kinds']})")
    say(f"  -> {artifact}")
    raise typer.Exit(Exit.OK)

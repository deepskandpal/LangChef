"""``langchef label`` and ``langchef calibrate`` — the M1 loop, and its M6 close.

Score a suite, pick what a person should look at, take their labels back, and
report how far the judge can be trusted. ``calibrate report`` talks to no model:
the judgements were produced by ``judge run`` and the labels by a person.

``calibrate diff`` is the one command here that does score, because that is the
whole point of it — a revised rubric has no judgements until something produces
them. It re-scores only the labelled examples, only under the new rubric; the
old rubric's verdicts are read from the run that already paid for them, and the
new ones are cached, so running the same diff twice costs nothing.
"""

from pathlib import Path
from typing import Annotated

import typer

from langchef.cli import common
from langchef.core import sampling
from langchef.core.agreement import agreement
from langchef.core.delta import INCONCLUSIVE, delta
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.core.taxonomy import Judgement as Paired
from langchef.core.taxonomy import summarise
from langchef.judge import providers, runner
from langchef.judge.cache import Cache
from langchef.judge.rubric import Rubric, RubricError
from langchef.judge.rubric import load as load_rubric
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


def _labels(resolved) -> dict[str, str]:
    """What the person said, or the refusal that names the two commands to run."""
    path = resolved.workspace.labels / f"{resolved.judge.rubric}.jsonl"
    if not path.is_file():
        fail(
            Exit.ERROR,
            f"no human labels at {path} — run `langchef label plan` first, "
            "have a person fill it in, then `langchef label import`",
        )
    return {row["example_id"]: row["verdict"] for row in read_jsonl(path)}


def _slices(row: dict) -> dict[str, str]:
    """The slice metadata a score row carries, unprefixed."""
    return {
        key[len("slice_") :]: value
        for key, value in row.items()
        if key.startswith("slice_") and value is not None
    }


def _paired(
    labels: dict[str, str],
    example_ids: list[str],
    verdicts: dict[str, str],
    criteria: dict[str, str | None],
    slices: dict[str, dict[str, str]],
) -> list[Paired]:
    """One row per labelled example, as both raters saw it. Input to the taxonomy."""
    return [
        Paired(
            example_id=example_id,
            human=labels[example_id],
            judge=verdicts[example_id],
            criterion=criteria.get(example_id),
            slices=slices.get(example_id, {}),
        )
        for example_id in example_ids
    ]


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

    labels = _labels(resolved)
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

    taxonomy = summarise(
        _paired(
            labels,
            paired_ids,
            {key: by_id[key]["verdict"] for key in paired_ids},
            {key: by_id[key].get("criterion") for key in paired_ids},
            {key: _slices(by_id[key]) for key in paired_ids},
        ),
        level=resolved.level,
    )

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


def _revised_rubric(resolved, name: str | None) -> Rubric:
    """The rubric to re-score with: a name under ``evals/rubrics/``, or a path.

    Defaults to the workspace's configured rubric, because the ordinary way to
    revise one is to edit it in place — which changes its hash, revokes its
    approval, and is exactly the state this command is for.
    """
    if name is None:
        path = resolved.rubric_path
    else:
        by_name = resolved.workspace.rubrics / f"{name}.md"
        path = by_name if by_name.is_file() else Path(name)
    try:
        return load_rubric(path)
    except RubricError as exc:
        fail(Exit.ERROR, str(exc))


@calibrate_app.command("diff")
def calibrate_diff(
    run_id: Annotated[
        str | None, typer.Option("--run", help="The run holding the old rubric's verdicts.")
    ] = None,
    rubric_name: Annotated[
        str | None,
        typer.Option("--rubric", help="The revised rubric: a name under rubrics/, or a path."),
    ] = None,
) -> None:
    """Re-score a revised rubric against the same labels and report the delta.

    Deliberately **not** behind gate one. The gate says nothing may be *scored
    for real* under a rubric a person has not approved; this command exists to
    produce the evidence that approval is supposed to rest on, and requiring the
    signature first would make the signature meaningless. The payload records
    that the revised rubric is unapproved so nothing downstream can mistake a
    candidate for a signed-off instrument.
    """
    resolved = common.settings()
    run = _run_or_latest(resolved, run_id)
    by_id = {row["example_id"]: row for row in _scores(run)}
    labels = _labels(resolved)

    labelled = sorted(set(labels) & set(by_id))
    if not labelled:
        fail(Exit.ERROR, f"none of the {len(labels)} labels match an example in run {run.run_id}")

    candidate = _revised_rubric(resolved, rubric_name)
    if not run.pin:
        fail(
            Exit.ERROR,
            f"run {run.run_id} recorded no pin, so there is nothing to check the "
            "revised rubric against — re-run it, then diff",
        )
    before_pin = runner.Pin.from_dict(run.pin)
    after_pin = runner.Pin(
        rubric=candidate.ref,
        provider=resolved.judge.provider,
        cheap_model=resolved.judge.cheap_model,
        strong_model=resolved.judge.strong_model,
    )
    try:
        # The rubric is the thing being changed, so it is the one field excluded.
        runner.check_pin(before_pin, after_pin, fields=runner.MODEL_FIELDS)
    except runner.PinMismatch as exc:
        fail(
            Exit.PIN_MISMATCH,
            f"{exc} — a rubric delta computed across a model change measures the "
            "model as much as the rubric, which is to say it measures nothing. "
            "Put the models back, or re-run the old rubric under the new ones.",
            moved=exc.moved,
            run_id=run.run_id,
            before=before_pin.to_dict(),
            after=after_pin.to_dict(),
        )
    if before_pin.rubric == after_pin.rubric:
        fail(
            Exit.ERROR,
            f"{candidate.ref} is the rubric run {run.run_id} already used — there is "
            "nothing to diff. Edit the rubric, or pass --rubric to name another one.",
            run_id=run.run_id,
            rubric=candidate.ref,
        )

    examples = {e.example_id: e for e in common.examples(resolved, run.suite, run.arm)}
    batch = [examples[key] for key in labelled if key in examples]
    if not batch:
        fail(
            Exit.ERROR,
            f"none of the {len(labelled)} labelled examples in run {run.run_id} are still "
            f"in the goldens for suite {run.suite} — the delta would be measuring the "
            "example set, not the rubric",
        )

    backend = common.provider(resolved)
    try:
        scored = runner.run(
            batch,
            candidate,
            backend,
            cheap_model=resolved.judge.cheap_model,
            cache=Cache(resolved.workspace.cache),
            strong_model=resolved.judge.strong_model,
            escalate_below=resolved.judge.escalate_below,
        )
    except providers.ProviderError as exc:
        fail(Exit.ERROR, str(exc))
    after = scored.by_id()

    # The paired set: labelled, scored under the old rubric, scored under the new.
    shared = [key for key in labelled if key in after]
    human = [labels[key] for key in shared]
    before_verdicts = [by_id[key]["verdict"] for key in shared]
    after_verdicts = [after[key].verdict for key in shared]
    result = delta(human, before_verdicts, after_verdicts, level=resolved.level, example_ids=shared)

    slices = {key: _slices(by_id[key]) for key in shared}
    taxonomies = {
        "before": summarise(
            _paired(
                labels,
                shared,
                {key: by_id[key]["verdict"] for key in shared},
                {key: by_id[key].get("criterion") for key in shared},
                slices,
            ),
            level=resolved.level,
        ),
        "after": summarise(
            _paired(
                labels,
                shared,
                {key: after[key].verdict for key in shared},
                {key: after[key].criterion for key in shared},
                slices,
            ),
            level=resolved.level,
        ),
    }

    payload = {
        **result.to_dict(),
        "run_id": run.run_id,
        "suite": run.suite,
        "arm": run.arm,
        "rubric": {"before": before_pin.rubric, "after": after_pin.rubric},
        "pin": {"before": before_pin.to_dict(), "after": after_pin.to_dict()},
        "approved": {
            "before": resolved.approved_rubric == before_pin.rubric,
            "after": resolved.approved_rubric == after_pin.rubric,
        },
        "labels": {
            "on_file": len(labels),
            "compared": len(shared),
            "dropped": len(labels) - len(shared),
        },
        "cost": {
            "judge_calls": scored.stats["provider_calls"],
            "cache_hits": scored.stats["cache_hits"],
            "rescored": len(after),
        },
        "taxonomy": taxonomies,
    }
    artifact = run.artifact("delta.json", payload)

    # A note, not a calibration. The ledger's calibration entries are what a memo
    # quotes as the judge's trustworthiness, and the revised rubric is a
    # candidate nobody has approved; filing it as a calibration would let an
    # unapproved instrument's kappa become the headline of a decision memo.
    ledger.append(
        resolved.workspace.ledger,
        "note",
        f"rubric delta {before_pin.rubric} -> {after_pin.rubric}: "
        f"kappa {result.kappa.difference:+.2f} ({result.verdict})",
        what="calibration-delta",
        run_id=run.run_id,
        n=result.n,
        kappa_before=result.kappa.before,
        kappa_after=result.kappa.after,
        kappa_delta=result.kappa.difference,
        verdict=result.verdict,
        pairing="paired",
    )

    emit({"ok": True, **payload, "artifact": str(artifact)})

    kappa, tpr, tnr = result.kappa, result.tpr, result.tnr
    say(f"rubric delta on {result.n} labelled example(s) from run {run.run_id}")
    say(f"  {before_pin.rubric}  ->  {after_pin.rubric}")
    say(
        f"  kappa  {kappa.before:+.2f} -> {kappa.after:+.2f}   {kappa.difference:+.2f} "
        f"[{kappa.interval.lo:+.2f}, {kappa.interval.hi:+.2f}]   {result.verdict.upper()}"
    )
    for rate, label in ((tpr, "TPR"), (tnr, "TNR")):
        if rate.discordance is None:
            say(f"  {label}    no example carried this label; nothing to compare")
            continue
        say(
            f"  {label}    {rate.before.value:.1%} -> {rate.after.value:.1%}   "
            f"{rate.difference:+.1%} [{rate.interval.lo:+.1%}, {rate.interval.hi:+.1%}]   "
            f"p={rate.p_adjusted:.4f}  {rate.direction}"
        )
        if rate.direction == INCONCLUSIVE:
            say(f"  {'':<6} (nothing under {rate.mde:.1%} was in reach on these labels)")
    moved = result.movement
    say(
        f"  moved  {moved.misses_fixed} miss(es) fixed, {moved.misses_introduced} introduced; "
        f"{moved.false_alarms_fixed} false alarm(s) fixed, "
        f"{moved.false_alarms_introduced} introduced"
    )
    say(
        f"  paired: the same {result.n} example(s) and the same labels under both "
        "rubrics, so the intervals are differences, not two overlapping reports"
    )
    say(
        f"  {scored.stats['provider_calls']} judge call(s) for the revised rubric; "
        f"the old rubric's verdicts were already on file"
    )
    if not payload["approved"]["after"]:
        say(
            f"  {after_pin.rubric} is not approved. If you keep it: "
            "langchef approve rubric, then re-run the suite."
        )
    say(f"  -> {artifact}")
    raise typer.Exit(Exit.OK)

"""``langchef experiment`` — the waiter.

Gate two needs something to approve. This is the surface that produces it: given
a stated intent, it proposes one or two designs with every number computed, and
records the one you pick as a pre-registration. Then it approves, checks and
reads out — refusing, in each case, where refusing is the point.

The division of labour is the contract's. The agent turns "we want to move to
the cheaper model" into a kind, a margin and a budget, and explains the options
to a person. Every figure in those options comes from ``core/design.py``.
"""

from typing import Annotated

import typer

from langchef.cli import common
from langchef.core import design as design_mod
from langchef.core.compare import compare as compare_arms
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit
from langchef.core.gates import experiment_gate, unmet
from langchef.judge.cache import Cache, judgement_key
from langchef.judge.runner import Pin, PinMismatch, check_pin
from langchef.workspace import experiments as store
from langchef.workspace import ledger, runs
from langchef.workspace.formats import FormatError, read_json, read_scores

experiment_app = typer.Typer(
    help="Design, approve and read out an experiment.", no_args_is_help=True
)


def _prior_discordance(resolved):
    """The flip rate this workspace actually saw last time, if it ever ran one."""
    for run in runs.every(resolved.workspace):
        path = run.file("compare.json")
        if not path.is_file():
            continue
        try:
            payload = read_json(path)
        except FormatError:
            continue
        if payload.get("n"):
            return payload.get("discordant"), payload.get("n")
    return None, None


def _cached_count(resolved, suite: str, arm: str, rubric) -> int:
    """How much of the arm being costed is already paid for.

    Keyed on the *variant* arm, not the baseline: the two arms answer the same
    questions differently, so they share no cache entries. Costing the baseline's
    cache would report a run as free that has not been run.
    """
    path = common.suite_path(resolved, suite, arm)
    if not path.is_file():
        return 0  # the arm has not been generated yet, which is normal at design time
    from langchef.judge.example import Example
    from langchef.workspace.formats import read_jsonl

    cache = Cache(resolved.workspace.cache)
    model = resolved.judge.cheap_model
    entries = cache.entries or {}
    return sum(
        1
        for row in read_jsonl(path)
        if judgement_key(Example.from_dict(row), rubric, model, "cheap") in entries
    )


def _escalation_rate(resolved) -> float:
    latest = runs.latest(resolved.workspace)
    if latest and latest.stats.get("n"):
        return float(latest.stats.get("escalated", 0)) / float(latest.stats["n"])
    return 0.0


@experiment_app.command("design")
def experiment_design(
    intent: Annotated[str, typer.Option("--intent", help="What you are trying to find out.")],
    variant_arm: Annotated[str, typer.Option("--variant-arm", help="The arm being tested.")],
    baseline_arm: Annotated[
        str, typer.Option("--baseline-arm", help="The reference arm.")
    ] = "baseline",
    kind: Annotated[
        str, typer.Option("--kind", help="superiority | non-inferiority")
    ] = "superiority",
    margin: Annotated[
        float, typer.Option("--margin", help="Quality you will accept losing, e.g. 0.03.")
    ] = 0.0,
    target: Annotated[
        float, typer.Option("--target-effect", help="Effect you want to be able to detect.")
    ] = 0.0,
    budget_calls: Annotated[
        int,
        typer.Option("--budget-calls", help="Ceiling on judge calls. 0 = design estimate."),
    ] = 0,
    accept: Annotated[
        str, typer.Option("--accept", help="Which candidate to record: as-it-stands | powered.")
    ] = "as-it-stands",
    suite: Annotated[str | None, typer.Option("--suite", help="Suite name.")] = None,
    experiment_id: Annotated[str | None, typer.Option("--id", help="Override the id.")] = None,
) -> None:
    """Propose one or two designs and record the one you pick, unapproved."""
    resolved = common.settings()
    pinned = common.rubric(resolved)
    name = common.only_suite(resolved, suite)
    examples = common.examples(resolved, name, baseline_arm)

    prior_discordant, prior_n = _prior_discordance(resolved)
    discordance, source = design_mod.estimate_discordance(prior_discordant, prior_n)

    guardrails = [
        f"The rubric must still be {pinned.ref} at run time; a changed rubric revokes approval.",
        "Both arms must be scored under the same pin, or compare exits 5.",
        "Calibration must exist for this judge; a memo without it says so in full.",
    ]
    try:
        candidates = design_mod.propose(
            suite=name,
            intent=intent,
            n_available=len(examples),
            baseline_arm=baseline_arm,
            variant_arm=variant_arm,
            kind=(
                "non_inferiority" if kind.replace("-", "_") == "non_inferiority" else "superiority"
            ),
            target_effect=target or None,
            margin=margin or None,
            level=resolved.level,
            discordance=discordance,
            discordance_source=source,
            cached=_cached_count(resolved, name, variant_arm, pinned),
            price_per_call_usd=resolved.judge.price_per_call_usd,
            escalation_rate=_escalation_rate(resolved),
            guardrails=guardrails,
        )
    except design_mod.DesignError as exc:
        fail(Exit.ERROR, str(exc))

    chosen = next((c for c in candidates if c.name == accept), None)
    if chosen is None:
        fail(
            Exit.ERROR,
            f"no candidate named {accept!r} — this design produced: "
            f"{', '.join(c.name for c in candidates)}",
        )

    record = chosen.to_dict()
    record["rubric"] = pinned.ref
    record["budget"] = {
        "judge_calls": budget_calls or chosen.cost.judge_calls,
        "source": "explicit --budget-calls" if budget_calls else "the design's own estimate",
    }
    record.pop("cost")
    record["cost"] = chosen.cost.to_dict()

    ident = experiment_id or store.slug(f"{name}-{variant_arm}")
    try:
        written = store.write(resolved.workspace, ident, record)
    except store.ExperimentError as exc:
        fail(Exit.ERROR, str(exc))

    emit(
        {
            "ok": True,
            "experiment_id": ident,
            "recorded": chosen.name,
            "digest": written.digest,
            "path": str(written.path),
            "approved": False,
            "candidates": [c.to_dict() for c in candidates],
        }
    )
    say(f"{len(candidates)} candidate design(s) for {name}: {intent}")
    for c in candidates:
        mark = "->" if c.name == chosen.name else "  "
        money = f"  ~${c.cost.usd}" if c.cost.usd is not None else ""
        say(
            f" {mark} {c.name:<14} n={c.n:<6} detects >={c.mde:.1%}  "
            f"{c.cost.judge_calls} judge call(s){money}"
        )
        for caveat in c.caveats:
            say(f"      note: {caveat}")
    say(f"  discordance {discordance:.0%} — {source}")
    say(f"  recorded -> {written.path}")
    say(f"  This is a proposal. Nothing runs until: langchef experiment approve {ident}")
    raise typer.Exit(Exit.OK)


@experiment_app.command("approve")
def experiment_approve(
    experiment_id: Annotated[str, typer.Argument(help="The experiment to approve.")],
) -> None:
    """Approve a design exactly as it stands. Editing it afterwards revokes this."""
    resolved = common.settings()
    try:
        approved = store.approve(resolved.workspace, experiment_id)
    except store.ExperimentError as exc:
        fail(Exit.ERROR, str(exc))

    ledger.append(
        resolved.workspace.ledger,
        "decision",
        f"pre-registered {approved.ref}",
        experiment_id=experiment_id,
        digest=approved.digest,
    )
    emit({"ok": True, "experiment_id": experiment_id, "digest": approved.digest, "approved": True})
    say(f"approved {approved.ref}")
    say(f"  n={approved.design.get('n')}  detects >={float(approved.design.get('mde', 0)):.1%}")
    say(f"  stopping rule: {approved.design.get('stopping_rule', '')[:80]}")
    raise typer.Exit(Exit.OK)


@experiment_app.command("list")
def experiment_list() -> None:
    """Every pre-registration in this workspace."""
    resolved = common.settings()
    found = store.every(resolved.workspace)
    emit(
        {
            "ok": True,
            "experiments": [
                {
                    "experiment_id": e.experiment_id,
                    "digest": e.digest,
                    "approved": e.approved,
                    "kind": e.design.get("kind"),
                    "n": e.design.get("n"),
                }
                for e in found
            ],
        }
    )
    say(f"{len(found)} pre-registration(s)")
    for e in found:
        state = "approved" if e.approved else "PROPOSED"
        say(f"  {e.experiment_id:<28} {state:<10} n={e.design.get('n')}")
    raise typer.Exit(Exit.OK)


def _load(resolved, experiment_id):
    try:
        return store.load(resolved.workspace, experiment_id)
    except store.ExperimentError as exc:
        fail(Exit.ERROR, str(exc))


def _violations(resolved, experiment, variant_run) -> list[str]:
    """Every way the run departs from what was registered."""
    design = experiment.design
    problems = []
    if variant_run.arm != design.get("variant_arm"):
        problems.append(f"arm is {variant_run.arm!r}, registered as {design.get('variant_arm')!r}")
    if variant_run.suite != design.get("suite"):
        problems.append(f"suite is {variant_run.suite!r}, registered as {design.get('suite')!r}")
    scored = int(variant_run.stats.get("n", 0))
    registered = int(design.get("n", 0))
    if scored < registered:
        problems.append(
            f"{scored} of {registered} registered golden(s) scored — the stopping "
            "rule says score them all before reading out"
        )
    pin_rubric = (variant_run.pin or {}).get("rubric")
    if design.get("rubric") and pin_rubric and pin_rubric != design["rubric"]:
        problems.append(f"rubric moved: registered {design['rubric']}, run used {pin_rubric}")
    return problems


@experiment_app.command("check")
def experiment_check(
    experiment_id: Annotated[str, typer.Argument(help="The experiment to check.")],
    variant: Annotated[str | None, typer.Option("--variant", help="Variant run id.")] = None,
) -> None:
    """Does the run match what was registered? Reports, never decides."""
    resolved = common.settings()
    experiment = _load(resolved, experiment_id)
    gate = experiment_gate(experiment.approved_digest, experiment.digest, experiment_id)

    problems: list[str] = []
    variant_run = None
    if variant:
        try:
            variant_run = runs.load(resolved.workspace, variant)
        except FormatError:
            fail(Exit.ERROR, f"no such run: {variant}")
        problems = _violations(resolved, experiment, variant_run)

    emit(
        {
            "ok": gate.met and not problems,
            "experiment_id": experiment_id,
            "gate": gate.to_dict(),
            "violations": problems,
            "variant_run": variant,
        }
    )
    say(f"{experiment.ref}: {'approved' if gate.met else 'NOT APPROVED'}")
    if gate.remedy:
        say(f"  {gate.remedy}")
    for problem in problems:
        say(f"  violation: {problem}")
    if gate.met and not problems:
        say("  the run matches the pre-registration")
    raise typer.Exit(Exit.OK)


@experiment_app.command("readout")
def experiment_readout(
    experiment_id: Annotated[str, typer.Argument(help="The experiment to read out.")],
    variant: Annotated[str | None, typer.Option("--variant", help="Variant run id.")] = None,
    baseline: Annotated[str | None, typer.Option("--baseline", help="Baseline run id.")] = None,
    override: Annotated[
        str | None,
        typer.Option("--override", help="Read out anyway, on the record, with a reason."),
    ] = None,
) -> None:
    """The gated readout. Refuses an unapproved design or an unfinished run."""
    resolved = common.settings()
    experiment = _load(resolved, experiment_id)
    design = experiment.design
    gate = experiment_gate(experiment.approved_digest, experiment.digest, experiment_id)

    if unmet([gate]) and not override:
        fail(
            Exit.REFUSED,
            gate.remedy,
            gate=gate.to_dict(),
            experiment_id=experiment_id,
        )

    variant_id = variant or runs.latest(
        resolved.workspace, suite=design.get("suite"), arm=design.get("variant_arm")
    )
    variant_id = variant_id.run_id if hasattr(variant_id, "run_id") else variant_id
    if not variant_id:
        fail(Exit.ERROR, f"no run for arm {design.get('variant_arm')!r} — score it first")
    variant_run = runs.load(resolved.workspace, variant_id)

    baseline_id = baseline
    if not baseline_id:
        path = resolved.workspace.baselines / f"{design.get('suite')}.json"
        baseline_id = read_json(path).get("run_id") if path.is_file() else None
    if not baseline_id:
        fail(Exit.ERROR, "no baseline — pass --baseline or run `langchef baseline set`")
    baseline_run = runs.load(resolved.workspace, baseline_id)

    problems = _violations(resolved, experiment, variant_run)
    if problems and not override:
        fail(
            Exit.REFUSED,
            "the run does not match the pre-registration: " + "; ".join(problems),
            violations=problems,
            remedy=(
                "finish the run, or re-read out with --override '<reason>' to record the departure"
            ),
        )

    try:
        check_pin(Pin.from_dict(baseline_run.pin or {}), Pin.from_dict(variant_run.pin or {}))
    except PinMismatch as exc:
        fail(Exit.PIN_MISMATCH, f"{exc} — these are two measurements, not a comparison.")

    left = {r["example_id"]: r["verdict"] for r in read_scores(baseline_run.file("scores.parquet"))}
    right = {r["example_id"]: r["verdict"] for r in read_scores(variant_run.file("scores.parquet"))}
    shared = sorted(set(left) & set(right))
    if not shared:
        fail(Exit.ERROR, "the two runs share no goldens")

    result = compare_arms(
        [left[k] for k in shared], [right[k] for k in shared], level=resolved.level
    )

    verdict = result.verdict
    if design.get("kind") == "non_inferiority":
        margin = float(design.get("margin") or 0)
        verdict = design_mod.non_inferiority_verdict(result.interval, margin)

    payload = {
        **result.to_dict(),
        "experiment_id": experiment_id,
        "design_digest": experiment.digest,
        "kind": design.get("kind"),
        "margin": design.get("margin"),
        "readout_verdict": verdict,
        "pre_registered": gate.met,
        "exploratory": bool(override) or not gate.met,
        "override": override,
        "violations": problems,
        "baseline_run": baseline_run.run_id,
        "variant_run": variant_run.run_id,
    }
    artifact = variant_run.artifact("readout.json", payload)

    ledger.append(
        resolved.workspace.ledger,
        "experiment",
        f"{experiment_id}: {verdict}"
        + (" (exploratory)" if payload["exploratory"] else " (pre-registered)"),
        experiment_id=experiment_id,
        verdict=verdict,
        difference=result.difference,
        exploratory=payload["exploratory"],
    )

    emit({"ok": True, **payload, "artifact": str(artifact)})
    say(f"readout for {experiment.ref} on {len(shared)} shared golden(s)")
    lo, hi = result.interval.lo, result.interval.hi
    say(f"  difference {result.difference:+.1%} [{lo:+.1%}, {hi:+.1%}]")
    if design.get("kind") == "non_inferiority":
        say(f"  margin -{float(design.get('margin') or 0):.1%} -> QUALITY {verdict.upper()}")
    else:
        say(f"  {verdict.upper()}")
    if payload["exploratory"]:
        say("  EXPLORATORY — not a pre-registered result; no decision is recommended")
    if result.inconclusive:
        say(f"  smallest effect this run could have seen: {result.mde:.1%}")
    say(f"  -> {artifact}")
    raise typer.Exit(Exit.OK)

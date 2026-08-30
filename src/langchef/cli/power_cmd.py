"""``langchef power``: is this many examples enough?

The question people ask before committing to anything, and today the only way to
get an answer is to create a pre-registration, which is more ceremony than the
question deserves and so discourages asking it at all.

Asking early is the whole point. Before a run the answer changes which experiment
is worth doing; after one it only explains a disappointment.

This command owns no arithmetic. Every number comes from ``core/design.py``, the
same functions ``experiment design`` uses, so the answer here and the answer
inside a design can never drift apart.
"""

from __future__ import annotations

import typer

from langchef.core import design
from langchef.core.emit import emit, fail, say
from langchef.core.exits import Exit

app = typer.Typer(no_args_is_help=True, help="Is this many examples enough?")


def _horizon(n: int, per_week: int) -> float | None:
    """Weeks until ``n`` examples exist, when a collection rate is known.

    None rather than a guess when it is not: a horizon invented from a default
    rate is a date somebody will put in a plan.
    """
    if per_week <= 0:
        return None
    return round(n / per_week, 1)


@app.callback(invoke_without_command=True)
def power(  # noqa: PLR0913 - each argument is a distinct question the caller answers
    n: int = typer.Option(..., "--n", help="Examples available, or planned."),
    effect: float | None = typer.Option(
        None, "--effect", help="Effect you want to detect, as a proportion (0.05 = 5 points)."
    ),
    discordant: int | None = typer.Option(
        None, "--discordant", help="Verdicts that flipped in a prior run, if you have one."
    ),
    prior_n: int | None = typer.Option(None, "--prior-n", help="Examples in that prior run."),
    sd: float | None = typer.Option(
        None, "--sd", help="Standard deviation of per-example differences, for a continuous score."
    ),
    level: float = typer.Option(0.95, "--level", help="Confidence level."),
    power_target: float = typer.Option(0.8, "--power", help="Power to design for."),
    per_week: int = typer.Option(
        0, "--per-week", help="Examples collected per week, for a horizon."
    ),
) -> None:
    """Report the detection limit, the sample size a target needs, and a horizon.

    Needs no workspace. It is arithmetic, and requiring a workspace to do
    arithmetic is exactly the ceremony this command exists to remove.
    """
    if n <= 0:
        fail(Exit.ERROR, "--n must be greater than zero: there is nothing to size.")

    # A continuous outcome is sized from the spread of the differences; a binary
    # one from the rate at which verdicts flip. Choosing by which evidence the
    # caller supplied keeps the two from being silently confused, and DECISIONS
    # #12 explains why they must not be.
    continuous = sd is not None
    if continuous:
        if sd < 0:
            fail(Exit.ERROR, "--sd cannot be negative.")
        mde = design.minimum_detectable_effect_continuous(n, sd, level, power_target)
        basis = f"sd of paired differences ({sd:.4g})"
        outcome = "continuous"
    else:
        rate, basis = design.estimate_discordance(discordant, prior_n)
        mde = design.minimum_detectable_effect(n, rate, level, power_target)
        outcome = "binary"

    needed: int | None = None
    if effect is not None:
        if effect <= 0:
            fail(Exit.ERROR, "--effect must be greater than zero.")
        needed = (
            design.required_n_continuous(effect, sd, level, power_target)
            if continuous
            else design.required_n(effect, rate, level, power_target)
        )

    payload: dict = {
        "ok": True,
        "outcome": outcome,
        "n": n,
        "level": level,
        "power": power_target,
        "mde": round(mde, 6),
        "basis": basis,
        "target_effect": effect,
        "required_n": needed,
        "shortfall": max(0, needed - n) if needed is not None else None,
        "runnable_now": None if needed is None else needed <= n,
        "horizon_weeks": _horizon(max(0, needed - n), per_week) if needed is not None else None,
    }
    emit(payload)

    say(f"{n} examples detect a difference of {mde:.1%} or larger ({outcome}).")
    say(f"  basis: {basis}")
    if needed is None:
        say("  Pass --effect to ask how many you would need for a specific difference.")
        return

    if needed <= n:
        say(f"  {effect:.1%} is within reach: {needed} needed, {n} available.")
        return

    short = needed - n
    say(f"  {effect:.1%} needs {needed} examples. You have {n}, so {short} short.")
    weeks = payload["horizon_weeks"]
    if weeks is not None:
        say(f"  At {per_week} a week that is about {weeks} weeks away.")
    else:
        say("  Pass --per-week to turn that shortfall into a date.")

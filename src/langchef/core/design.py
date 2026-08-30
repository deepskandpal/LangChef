"""Designing an experiment before it runs.

Gate two in the approval model needs something to approve, and until now nothing
produced it: the pre-registration format was specified, the refusal to read out
without one was specified, and the surface that proposes a design in the first
place did not exist. This is that surface's arithmetic.

The split matters. **This module computes every number in a design** — how small
an effect the goldens on hand could resolve, how many more would be needed for a
target effect, what it will cost to score, and whether it can be run with the
goldens that exist.
The agent's job is to turn "we want to move to the cheaper model" into a kind and
a tolerance, and to explain the options to a person. It does no arithmetic, which
is why none of this imports anything from ``judge`` or the CLI.

Two shapes of experiment, and confusing them is the most expensive mistake here:

``superiority``
    "Is the variant better?" The interesting outcome is a difference away from
    zero, in either direction.
``non_inferiority``
    "We are buying cost or latency with quality — did quality hold?" There is a
    margin you are willing to lose, decided *before* the run, and the question is
    whether the interval clears it. Deciding the margin afterwards is how a null
    result becomes a green light.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.stats import norm

from langchef.core.agreement import DEFAULT_LEVEL, Interval, wilson

DEFAULT_POWER = 0.8
# Used only when nothing better is known, and always reported as an assumption.
# Two arms of the same system usually agree on most examples; a fifth of them
# flipping is pessimistic for a small change and about right for a large one.
ASSUMED_DISCORDANCE = 0.20
MAX_FEASIBLE_N = 100_000


class DesignError(ValueError):
    """A design that could not be built, or could not mean anything if it were."""


@dataclass(frozen=True)
class Cost:
    """What a design will cost to score, in the units that are actually known.

    Calls are always known. Money is not: it depends on a price for the model,
    and inventing one is worse than admitting the gap — so ``usd`` is None unless
    a price was configured, and every caller has to cope with that.
    """

    judge_calls: int
    cached_calls: int
    usd: float | None = None
    price_note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Design:
    """One candidate experiment, fully specified, ready to be approved or refused."""

    name: str
    kind: str
    hypothesis: str
    suite: str
    baseline_arm: str
    variant_arm: str
    n: int
    n_available: int
    mde: float
    target_effect: float | None
    required_n: int | None
    margin: float | None
    power: float
    level: float
    discordance_assumed: float
    discordance_source: str
    stopping_rule: str
    guardrails: tuple[str, ...]
    cost: Cost
    # Whether this design can be executed with the goldens that exist. It is not
    # a judgement about whether the design is sensible; a design needing 628
    # goldens when the suite has 90 is perfectly sound and simply not runnable
    # yet. `shortfall` is the number an agent would otherwise have to derive,
    # and it is here because stdout is the interface: putting the binding
    # constraint only in prose would invert the split the contract rests on.
    runnable_now: bool
    shortfall: int
    # Which arithmetic produced `mde`. A continuous limit and a discordant one
    # are different quantities that both print as a percentage, so a reader who
    # cannot tell them apart will compare two numbers that were never
    # comparable. See DECISIONS #12.
    outcome: str = "binary"
    caveats: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["cost"] = self.cost.to_dict()
        payload["guardrails"] = list(self.guardrails)
        payload["caveats"] = list(self.caveats)
        return payload


OUTCOMES = ("binary", "continuous")


def _z(level: float, power: float) -> tuple[float, float]:
    return float(norm.ppf(1 - (1 - level) / 2)), float(norm.ppf(power))


def minimum_detectable_effect(
    n: int, discordance: float, level: float = DEFAULT_LEVEL, power: float = DEFAULT_POWER
) -> float:
    """Smallest paired difference ``n`` goldens could resolve at this flip rate.

    The same formula ``compare`` reports after the fact, run forwards. Paired, so
    it is driven by the discordant rate rather than the pass rate — 200 goldens
    where 4 flip carry far less information than 200 where 40 do.
    """
    if n <= 0:
        return float("nan")
    z_alpha, z_beta = _z(level, power)
    return float((z_alpha + z_beta) * np.sqrt(max(discordance, 1e-9) / n))


def minimum_detectable_effect_continuous(
    n: int, sd_difference: float, level: float = DEFAULT_LEVEL, power: float = DEFAULT_POWER
) -> float:
    """Smallest paired difference ``n`` examples could resolve on a *continuous* score.

    The binary version above is driven by the discordant rate, which counts
    verdicts that flipped. Nothing flips on a continuous score: recall moving
    from 0.42 to 0.71 did not change category, and asking how often it did is
    not a question the data can answer. What carries the information instead is
    the spread of the **per-example differences**.

    That distinction is the whole reason this function exists. ``sd_difference``
    is the standard deviation of ``variant[i] - baseline[i]``, not of either arm.
    Using an arm's own spread would ignore the pairing and inflate the estimate,
    which is the same mistake in the other direction: two arms can both vary
    widely while the difference between them is nearly constant, and that
    experiment is far more sensitive than an unpaired reading of it suggests.

    See DECISIONS #12 for why only ``compare`` and this module generalise.
    """
    if n <= 0:
        return float("nan")
    if sd_difference < 0:
        raise DesignError("the standard deviation of the differences cannot be negative")
    z_alpha, z_beta = _z(level, power)
    return float((z_alpha + z_beta) * sd_difference / np.sqrt(n))


def required_n_continuous(
    effect: float,
    sd_difference: float,
    level: float = DEFAULT_LEVEL,
    power: float = DEFAULT_POWER,
) -> int:
    """Examples needed to detect ``effect`` on a continuous score. The inverse."""
    if effect <= 0:
        raise DesignError("target effect must be greater than zero")
    if sd_difference < 0:
        raise DesignError("the standard deviation of the differences cannot be negative")
    z_alpha, z_beta = _z(level, power)
    return int(np.ceil(((z_alpha + z_beta) * sd_difference / effect) ** 2))


def required_n(
    effect: float, discordance: float, level: float = DEFAULT_LEVEL, power: float = DEFAULT_POWER
) -> int:
    """Goldens needed to detect ``effect``. The inverse of the above."""
    if effect <= 0:
        raise DesignError("target effect must be greater than zero")
    z_alpha, z_beta = _z(level, power)
    n = max(discordance, 1e-9) * ((z_alpha + z_beta) / effect) ** 2
    return int(np.ceil(n))


def estimate_discordance(prior_discordant: int | None, prior_n: int | None) -> tuple[float, str]:
    """How often verdicts are expected to flip between the two arms.

    Prefers evidence over the default: if this workspace has compared two arms
    before, the rate it actually saw is a far better prior than a number chosen
    here. The upper end of its interval is used rather than the point estimate,
    because under-estimating the flip rate under-powers the design, and an
    under-powered experiment is one that was never going to answer anything.
    """
    if prior_discordant is not None and prior_n:
        return (
            wilson(prior_discordant, prior_n).hi,
            f"observed in a prior run ({prior_discordant}/{prior_n})",
        )
    return (
        ASSUMED_DISCORDANCE,
        f"assumed default ({ASSUMED_DISCORDANCE:.0%}) — no prior comparison here",
    )


def estimate_cost(
    n: int,
    cached: int = 0,
    price_per_call_usd: float | None = None,
    escalation_rate: float = 0.0,
) -> Cost:
    """Scoring cost for one arm. Escalated examples are charged twice."""
    to_score = max(0, n - cached)
    calls = int(round(to_score * (1 + max(0.0, escalation_rate))))
    if price_per_call_usd is None:
        return Cost(
            judge_calls=calls,
            cached_calls=cached,
            usd=None,
            price_note=(
                "no price configured for this model — set [judge].price_per_call_usd to cost it"
            ),
        )
    return Cost(
        judge_calls=calls,
        cached_calls=cached,
        usd=round(calls * price_per_call_usd, 4),
        price_note=f"{price_per_call_usd} USD per judge call, as configured",
    )


def non_inferiority_verdict(interval: Interval, margin: float) -> str:
    """Did quality hold within a margin decided before the run?

    Three outcomes, and the middle one is the one people skip. ``held`` means the
    whole interval clears the margin. ``failed`` means the whole interval is past
    it. ``unresolved`` means the run cannot tell — which is not permission to
    ship, it is a statement that the evidence is absent.
    """
    if margin <= 0:
        raise DesignError("a non-inferiority margin must be greater than zero")
    if interval.lo != interval.lo:  # NaN
        return "unresolved"
    if interval.lo >= -margin:
        return "held"
    if interval.hi < -margin:
        return "failed"
    return "unresolved"


def propose(
    suite: str,
    intent: str,
    n_available: int,
    baseline_arm: str,
    variant_arm: str,
    kind: str = "superiority",
    target_effect: float | None = None,
    margin: float | None = None,
    level: float = DEFAULT_LEVEL,
    power: float = DEFAULT_POWER,
    discordance: float | None = None,
    discordance_source: str = "",
    outcome: str = "binary",
    sd_difference: float | None = None,
    cached: int = 0,
    price_per_call_usd: float | None = None,
    escalation_rate: float = 0.0,
    guardrails: Sequence[str] = (),
) -> list[Design]:
    """One or two candidate designs for a stated intent.

    The first uses the goldens that exist and reports what they can resolve. The
    second exists only when a target effect was named and the goldens on hand
    cannot resolve it — and it is the more useful of the two, because "you need
    340 examples and you have 90" is an answer, where a shrug is not.
    """
    if kind not in ("superiority", "non_inferiority"):
        raise DesignError(f"unknown experiment kind {kind!r}")
    # The sizing arithmetic follows the shape of the outcome, never a flag and
    # never a task-class name: `core/` must not know that "retrieval" exists
    # (DECISIONS #5, enforced by tests/test_boundaries.py). The caller resolves
    # class to shape; this module only knows the two shapes it can size.
    if outcome not in OUTCOMES:
        raise DesignError(
            f"no sizing rule for a {outcome!r} outcome. This tool can size a "
            f"{' or a '.join(sorted(OUTCOMES))} outcome; it will not guess at a "
            "third, because a plausible sample size is worse than no answer."
        )
    if outcome == "continuous" and sd_difference is None:
        raise DesignError(
            "sizing a continuous outcome needs the standard deviation of the "
            "per-example differences. Without it there is nothing to compute, "
            "and a default here would be a number nobody chose."
        )
    if kind == "non_inferiority" and not margin:
        raise DesignError(
            "a non-inferiority design needs --margin: how much quality you are "
            "willing to lose. Deciding it after the run is not a design."
        )
    if n_available <= 0:
        raise DesignError(f"no goldens in suite {suite!r} to design over")

    if discordance is None:
        discordance, discordance_source = estimate_discordance(None, None)

    # One pair of callables, chosen once, so the two designs below cannot end up
    # sized by different arithmetic than the one recorded on them.
    if outcome == "continuous":
        assert sd_difference is not None  # guarded above
        spread = sd_difference

        def _mde(n: int) -> float:
            return minimum_detectable_effect_continuous(n, spread, level, power)

        def _needed(e: float) -> int:
            return required_n_continuous(e, spread, level, power)

        discordance_source = f"sd of paired differences ({spread:.4g})"
    else:
        flip = discordance

        def _mde(n: int) -> float:
            return minimum_detectable_effect(n, flip, level, power)

        def _needed(e: float) -> int:
            return required_n(e, flip, level, power)

    effect = target_effect if target_effect is not None else margin
    common = dict(
        kind=kind,
        hypothesis=intent,
        suite=suite,
        baseline_arm=baseline_arm,
        variant_arm=variant_arm,
        n_available=n_available,
        target_effect=target_effect,
        margin=margin,
        power=power,
        level=level,
        discordance_assumed=discordance,
        discordance_source=discordance_source,
        stopping_rule=(
            f"Score all {n_available} goldens in both arms, then read out once. "
            "No interim looks: stopping early when a result looks good is the "
            "most common way an experiment reports an effect that is not there."
        ),
        guardrails=tuple(guardrails),
        outcome=outcome,
    )

    at_hand_mde = _mde(n_available)
    caveats: list[str] = []
    if effect is not None and effect < at_hand_mde:
        caveats.append(
            f"These goldens cannot resolve {effect:.1%}. The smallest effect this "
            f"design could detect is {at_hand_mde:.1%}; a real change below that "
            "will come back inconclusive."
        )
    if kind == "non_inferiority":
        caveats.append(
            f"Quality holds only if the whole interval clears −{margin:.1%}. "
            "The point estimate is not the test."
        )

    designs = [
        Design(
            name="as-it-stands",
            n=n_available,
            mde=at_hand_mde,
            required_n=None,
            cost=estimate_cost(n_available, cached, price_per_call_usd, escalation_rate),
            runnable_now=True,  # n == n_available by construction
            shortfall=0,
            caveats=tuple(caveats),
            **common,
        )
    ]

    if effect is not None and effect < at_hand_mde:
        needed = _needed(effect)
        shortfall = max(0, needed - n_available)
        powered_caveats = [
            f"Needs {shortfall} more golden(s) than the suite has "
            f"({n_available}). Collect them before running, or accept the "
            "detection limit of the design above."
        ]
        if needed > MAX_FEASIBLE_N:
            # Arithmetically real, practically absurd. Words are more use here
            # than a boolean, because the number itself is the argument.
            powered_caveats.append(
                f"{needed:,} goldens is beyond any realistic collection effort. "
                "Treat this as evidence that the effect you named cannot be "
                "resolved by this method, not as a plan."
            )
        designs.append(
            Design(
                name="powered",
                n=needed,
                mde=_mde(needed),
                required_n=needed,
                cost=estimate_cost(needed, cached, price_per_call_usd, escalation_rate),
                runnable_now=shortfall == 0,
                shortfall=shortfall,
                caveats=tuple(powered_caveats),
                **common,
            )
        )
    return designs

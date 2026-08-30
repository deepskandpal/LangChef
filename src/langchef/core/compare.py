"""Baseline against variant, on the same goldens.

The arms of an eval experiment are not two independent samples: every golden is
scored under both, so the pairs are the unit and the comparison is McNemar's,
not a two-sample proportion test. Treating them as independent is the standard
way to get a confident answer to the wrong question — it throws away the pairing
and inflates the variance, so real regressions come back "not significant".

Only the discordant pairs carry information. If 200 goldens pass under both
arms and 3 flip, the evidence is in the 3.

The second half of the module attributes that one verdict to the rubric
criteria the judge cited, because "quality fell 4 points" and "groundedness
fell 9 points while correctness held" are the difference between a fact and an
answer to *which part of the system broke*. It is attribution, not k separate
comparisons, and the multiplicity is corrected rather than ignored — see the
block comment above ``Outcome``.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
from scipy.stats import binomtest, norm

from langchef.core.agreement import DEFAULT_LEVEL, Interval, Verdict, wilson

BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 0  # the contract calls compare deterministic; the seed is the pin


@dataclass(frozen=True)
class Discordance:
    """The 2x2 of paired verdicts. Only the off-diagonal moves the estimate."""

    both_pass: int
    fixed: int  # failed under baseline, passes under variant
    broke: int  # passed under baseline, fails under variant
    both_fail: int

    @property
    def n(self) -> int:
        return self.both_pass + self.fixed + self.broke + self.both_fail

    @property
    def discordant(self) -> int:
        return self.fixed + self.broke


@dataclass(frozen=True)
class Comparison:
    """What ``compare`` writes, and what a decision memo quotes."""

    discordance: Discordance
    baseline_rate: float
    variant_rate: float
    difference: float
    interval: Interval
    p_value: float
    regression: bool
    improvement: bool
    inconclusive: bool
    mde: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["n"] = self.discordance.n
        payload["discordant"] = self.discordance.discordant
        payload["verdict"] = self.verdict
        return payload

    @property
    def verdict(self) -> str:
        if self.regression:
            return "regression"
        if self.improvement:
            return "improvement"
        return "inconclusive"


def discordance(baseline: Sequence[Verdict], variant: Sequence[Verdict]) -> Discordance:
    """Count the paired outcomes. Element *i* is the same golden under both arms."""
    if len(baseline) != len(variant):
        raise ValueError(f"arms must be the same length: {len(baseline)} != {len(variant)}")
    if not baseline:
        raise ValueError("no goldens to compare")
    allowed = {"pass", "fail"}
    bad = sorted({*baseline, *variant} - allowed)
    if bad:
        raise ValueError(f"verdicts must be 'pass' or 'fail', got {bad}")

    b = np.array([v == "pass" for v in baseline])
    v = np.array([v == "pass" for v in variant])
    return Discordance(
        both_pass=int(np.sum(b & v)),
        fixed=int(np.sum(~b & v)),
        broke=int(np.sum(b & ~v)),
        both_fail=int(np.sum(~b & ~v)),
    )


def mcnemar_p(d: Discordance) -> float:
    """Exact McNemar: given a flip happened, was it equally likely either way?

    The exact binomial rather than the chi-square approximation, because the
    discordant counts that matter in practice are small enough that the
    approximation is wrong exactly when the decision is close.
    """
    if d.discordant == 0:
        return 1.0
    return float(binomtest(d.broke, d.discordant, 0.5).pvalue)


def paired_bootstrap_interval(
    baseline: Sequence[Verdict], variant: Sequence[Verdict], level: float
) -> Interval:
    """Percentile bootstrap over pairs, resampled together to keep the pairing.

    Public because ``core.delta`` needs the same estimator for the difference of
    two correlated rates. One implementation, so the two paired intervals this
    product reports cannot drift apart.
    """
    b = np.array([v == "pass" for v in baseline])
    v = np.array([v == "pass" for v in variant])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx = rng.integers(0, len(b), size=(BOOTSTRAP_DRAWS, len(b)))
    draws = v[idx].mean(axis=1) - b[idx].mean(axis=1)
    tail = (1 - level) / 2 * 100
    return Interval(
        float(np.percentile(draws, tail)), float(np.percentile(draws, 100 - tail)), level
    )


def minimum_detectable_effect(
    n: int, discordant: int, level: float = DEFAULT_LEVEL, power: float = 0.8
) -> float:
    """The smallest change this experiment could have detected.

    Quoted on every inconclusive result. "No significant difference" on 90
    goldens means nothing until you know what the run could have seen, and
    reporting this is the difference between an honest null and a shrug.

    Paired, like the rest of this module. Under McNemar the variance of the
    difference is governed by the *discordant* rate, not the pass rate — 90
    goldens where 4 flip carry far less information than 90 where 40 do, and an
    unpaired two-sample formula ignores that and overstates the threshold.

    The discordant rate is taken at the upper end of its confidence interval,
    which also keeps the answer meaningful when nothing flipped at all: zero
    discordant pairs is not evidence that the experiment could detect an
    arbitrarily small effect, it is evidence of an unknown rate that this many
    goldens bound from above.
    """
    if n <= 0:
        return float("nan")
    psi = wilson(discordant, n, level).hi
    z_alpha = float(norm.ppf(1 - (1 - level) / 2))
    z_beta = float(norm.ppf(power))
    return float((z_alpha + z_beta) * np.sqrt(max(psi, 1e-12) / n))


def compare(
    baseline: Sequence[Verdict],
    variant: Sequence[Verdict],
    level: float = DEFAULT_LEVEL,
) -> Comparison:
    """Full paired comparison of two arms over the same goldens."""
    d = discordance(baseline, variant)
    baseline_rate = (d.both_pass + d.broke) / d.n
    variant_rate = (d.both_pass + d.fixed) / d.n
    interval = paired_bootstrap_interval(baseline, variant, level)
    p_value = mcnemar_p(d)

    # The interval decides. The p-value is reported because people ask for it,
    # but a direction only counts when the whole interval agrees with it.
    regression = interval.hi < 0
    improvement = interval.lo > 0
    return Comparison(
        discordance=d,
        baseline_rate=baseline_rate,
        variant_rate=variant_rate,
        difference=variant_rate - baseline_rate,
        interval=interval,
        p_value=p_value,
        regression=regression,
        improvement=improvement,
        inconclusive=not (regression or improvement),
        mde=minimum_detectable_effect(d.n, d.discordant, level),
    )


# ---------------------------------------------------------------------------
# Per-criterion attribution
# ---------------------------------------------------------------------------
#
# The overall verdict says quality moved. It does not say which half of a
# retrieval system moved it, and "groundedness fell 9 points while correctness
# held" is the sentence somebody can act on. The judge already names the
# criterion it cited on every failure, so the decomposition is free.
#
# Three decisions are load-bearing here, and all three are about not turning one
# honest finding into five dishonest ones.
#
# 1. The pairing is per example *and* per criterion, never across criteria.
#    Within one criterion the machinery above applies unchanged: the same
#    example under both arms, the same exact McNemar over the discordant pairs,
#    the same percentile bootstrap over the pairs. Nothing switches to a
#    two-sample test on a smaller slice.
#
# 2. **Multiplicity is corrected, with Holm–Bonferroni.** k criteria means k
#    tests, and with five of them one crossing a threshold by chance is
#    ordinary, not a finding. The alternative — report intervals and refuse to
#    call any direction — was rejected because a reader looking at five
#    intervals performs the k comparisons anyway, in their head, uncorrected;
#    declining to compute the correction does not remove it, it just moves it
#    somewhere nobody can check. Holm rather than Bonferroni because it is
#    uniformly more powerful at the same family-wise error rate, and rather than
#    Benjamini–Hochberg because these criteria are the two or three halves of
#    one system: the question is "which one broke", so a false positive is a
#    person sent to rewrite the wrong component, and FWER is the error rate that
#    matches that cost. Holm holds under arbitrary dependence between the tests,
#    which matters — the per-criterion outcomes here are strongly negatively
#    dependent, because the judge cites exactly one criterion per failure.
#
# 3. **The language is deliberately not the overall verdict's.** A criterion is
#    reported as ``moved_worse`` / ``moved_better`` / ``inconclusive``, never as
#    a regression or an improvement. These are attributions of one comparison's
#    movement, not k standalone comparisons, and the vocabulary says so in the
#    payload rather than in a footnote somebody drops.
#
# The remaining honesty problem is censoring, and it cannot be fixed here: the
# judge names one criterion per failing example, so an example that failed
# Correctness tells us nothing about whether it would also have failed
# Groundedness. A criterion is therefore credited with a failure only when it
# was cited. That is exactly why this is attribution — the per-criterion
# differences add up to the overall difference by construction, which is the
# useful property, and is not the same claim as five independent measurements.

ATTRIBUTION_NOTE = (
    "Attribution of one paired comparison, not independent findings per criterion. "
    "p-values are Holm-corrected across the criteria tested; a direction is only "
    "named when the corrected p clears alpha and the interval lies wholly on one "
    "side of zero. The intervals themselves are not simultaneous — read them as "
    "magnitude, not as one verdict each."
)

MOVED_WORSE = "moved_worse"
MOVED_BETTER = "moved_better"
INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Outcome:
    """One example under one arm: the verdict, and the criterion cited on a fail.

    ``criterion`` is what the judge named when it failed the example. It is
    ignored on a passing outcome: the judge cites a criterion to explain a
    failure, and crediting a pass to a criterion would invent a measurement
    nobody made.
    """

    verdict: Verdict
    criterion: str | None = None


@dataclass(frozen=True)
class CriterionResult:
    """One criterion's share of the movement between the two arms.

    ``baseline_rate`` and ``variant_rate`` are the share of examples this
    criterion did *not* fail, so the sign convention matches the overall
    comparison: negative ``difference`` means this criterion accounts for more
    failures under the variant.
    """

    criterion: str
    discordance: Discordance
    baseline_failures: int
    variant_failures: int
    baseline_rate: float
    variant_rate: float
    difference: float
    interval: Interval
    p_value: float
    p_adjusted: float
    attribution: str
    mde: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["n"] = self.discordance.n
        payload["discordant"] = self.discordance.discordant
        return payload


@dataclass(frozen=True)
class Attribution:
    """The per-criterion breakdown, with the family it was corrected against.

    ``attributed`` is how much of the overall difference the cited criteria
    account for, and ``unattributed`` is the rest — non-zero only when the judge
    failed something without naming a criterion. Reporting the remainder is what
    stops a breakdown from quietly explaining less than it appears to.
    """

    criteria: tuple[CriterionResult, ...]
    level: float
    alpha: float
    mde_level: float
    uncited_failures: int
    attributed: float
    unattributed: float
    method: str = "holm"

    @property
    def family(self) -> int:
        """How many tests the correction was applied over."""
        return len(self.criteria)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "family": self.family,
            "level": self.level,
            "alpha": self.alpha,
            "mde_level": self.mde_level,
            "uncited_failures": self.uncited_failures,
            "attributed": self.attributed,
            "unattributed": self.unattributed,
            "note": ATTRIBUTION_NOTE,
            "criteria": [c.to_dict() for c in self.criteria],
        }


def holm(p_values: Sequence[float]) -> list[float]:
    """Holm-Bonferroni step-down adjusted p-values, in the input order.

    Sort ascending, multiply the *i*-th smallest by ``k - i``, then take a
    running maximum so the adjusted values never decrease. Comparing these
    against alpha is identical to walking the ladder alpha/k, alpha/(k-1), ...
    and stopping at the first failure, and it keeps the family-wise error rate
    at alpha under any dependence between the tests.

    Uniformly at least as powerful as Bonferroni — the largest p-value is
    compared against alpha itself rather than alpha/k — at the same guarantee.
    """
    k = len(p_values)
    if k == 0:
        return []
    order = sorted(range(k), key=lambda i: p_values[i])
    adjusted = [1.0] * k
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (k - rank) * p_values[index])
        adjusted[index] = float(min(1.0, running))
    return adjusted


def _attributed(outcomes: Sequence[Outcome], criterion: str) -> list[Verdict]:
    """This criterion's verdict per example: fail only where it was cited."""
    return [
        "fail" if (o.verdict == "fail" and o.criterion == criterion) else "pass" for o in outcomes
    ]


def by_criterion(
    baseline: Sequence[Outcome],
    variant: Sequence[Outcome],
    level: float = DEFAULT_LEVEL,
) -> Attribution:
    """Attribute the paired difference to the criteria the judge cited.

    Element *i* is the same golden under both arms, exactly as in ``compare``.
    The criteria tested are those cited by at least one failure in either arm; a
    criterion nobody ever failed carries no information, can never be rejected,
    and is left out of the family rather than padding the correction.

    Every criterion reports its own detection limit, computed at the *corrected*
    level (alpha/k, the strictest rung of the Holm ladder and the one a lone
    signal faces). That is the point of quoting it per criterion: the overall
    limit was computed at alpha over the whole suite's flip rate, and pasting it
    next to a per-criterion finding it cannot support is the failure mode here.
    A per-criterion limit is not automatically wider than the overall one — a
    criterion with few flips is estimated *more* precisely, not less — so it is
    computed rather than assumed.
    """
    if len(baseline) != len(variant):
        raise ValueError(f"arms must be the same length: {len(baseline)} != {len(variant)}")
    if not baseline:
        raise ValueError("no goldens to compare")
    allowed = {"pass", "fail"}
    bad = sorted({o.verdict for o in (*baseline, *variant)} - allowed)
    if bad:
        raise ValueError(f"verdicts must be 'pass' or 'fail', got {bad}")

    names = sorted(
        {o.criterion for o in (*baseline, *variant) if o.verdict == "fail" and o.criterion}
    )
    alpha = 1 - level
    family = len(names)
    # The Holm ladder's strictest rung. With no criteria there is nothing to
    # correct and the nominal level stands.
    mde_level = 1 - alpha / family if family else level

    measured = []
    for name in names:
        left, right = _attributed(baseline, name), _attributed(variant, name)
        d = discordance(left, right)
        measured.append((name, d, paired_bootstrap_interval(left, right, level), mcnemar_p(d)))

    adjusted = holm([p for *_, p in measured])
    results = []
    for (name, d, interval, p_value), p_adjusted in zip(measured, adjusted, strict=True):
        # Both halves are required. Holm controls the false-positive rate across
        # the family; the interval carries the module's standing rule that a
        # direction only counts when the whole interval agrees with it. Requiring
        # both is conservative and, more usefully, means the payload can never
        # name a direction that the interval it prints beside it contradicts.
        significant = p_adjusted < alpha
        if significant and interval.hi < 0:
            attribution = MOVED_WORSE
        elif significant and interval.lo > 0:
            attribution = MOVED_BETTER
        else:
            attribution = INCONCLUSIVE
        baseline_rate = (d.both_pass + d.broke) / d.n
        variant_rate = (d.both_pass + d.fixed) / d.n
        results.append(
            CriterionResult(
                criterion=name,
                discordance=d,
                baseline_failures=d.broke + d.both_fail,
                variant_failures=d.fixed + d.both_fail,
                baseline_rate=baseline_rate,
                variant_rate=variant_rate,
                difference=variant_rate - baseline_rate,
                interval=interval,
                p_value=p_value,
                p_adjusted=p_adjusted,
                attribution=attribution,
                mde=minimum_detectable_effect(d.n, d.discordant, mde_level),
            )
        )

    n = len(baseline)
    overall = sum(1 for o in variant if o.verdict == "pass") / n
    overall -= sum(1 for o in baseline if o.verdict == "pass") / n
    attributed = sum(r.difference for r in results)
    return Attribution(
        # Worst first: the criterion that lost the most is the one somebody
        # reads, and ties break on the name so the order is deterministic.
        criteria=tuple(sorted(results, key=lambda r: (r.difference, r.criterion))),
        level=level,
        alpha=alpha,
        mde_level=mde_level,
        uncited_failures=sum(
            1 for o in (*baseline, *variant) if o.verdict == "fail" and not o.criterion
        ),
        attributed=attributed,
        unattributed=overall - attributed,
    )

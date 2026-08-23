"""Baseline against variant, on the same goldens.

The arms of an eval experiment are not two independent samples: every golden is
scored under both, so the pairs are the unit and the comparison is McNemar's,
not a two-sample proportion test. Treating them as independent is the standard
way to get a confident answer to the wrong question — it throws away the pairing
and inflates the variance, so real regressions come back "not significant".

Only the discordant pairs carry information. If 200 goldens pass under both
arms and 3 flip, the evidence is in the 3.
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


def _bootstrap_interval(
    baseline: Sequence[Verdict], variant: Sequence[Verdict], level: float
) -> Interval:
    """Percentile bootstrap over pairs, resampled together to keep the pairing."""
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
    interval = _bootstrap_interval(baseline, variant, level)
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

"""Judge–human agreement — the measurement that gates everything downstream.

A judge is a measuring instrument, not a metric. Before any eval suite built on
it means anything, we need to know how often it agrees with a person and *how*
it fails when it does not. This module is the arithmetic for that, and nothing
else: no I/O, no LLM, no network, so every number here is testable with no API
key (``tests/test_boundaries.py``).

The positive class is **the finding** — the judge saying "this output is bad".
That convention is deliberate and load-bearing: recall (TPR) is then the share
of real problems the judge catches, and the false-positive rate is the share of
good outputs it needlessly flags. Both are quoted with intervals, because a
point estimate off 40 labels is a rumour, not a measurement.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
from scipy.stats import norm

Verdict = Literal["pass", "fail"]
DEFAULT_LEVEL = 0.95


@dataclass(frozen=True)
class Interval:
    """A two-sided confidence interval."""

    lo: float
    hi: float
    level: float = DEFAULT_LEVEL

    @property
    def width(self) -> float:
        return self.hi - self.lo


@dataclass(frozen=True)
class Proportion:
    """An estimated rate, with the counts it came from.

    Carrying ``k`` and ``n`` alongside the value is what lets a memo say
    "17 of 22" instead of "0.77", which is the difference between a reader
    trusting the number and not.
    """

    k: int
    n: int
    interval: Interval

    @property
    def value(self) -> float:
        return self.k / self.n if self.n else float("nan")


@dataclass(frozen=True)
class Confusion:
    """Paired verdicts, counted. Rows are the human, columns are the judge."""

    tp: int  # human fail, judge fail — a real problem, caught
    fp: int  # human pass, judge fail — a false alarm
    fn: int  # human fail, judge pass — a miss
    tn: int  # human pass, judge pass — agreed clean

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.fn + self.tn


@dataclass(frozen=True)
class Agreement:
    """Everything ``calibrate report`` needs to say whether a judge is usable."""

    confusion: Confusion
    accuracy: Proportion
    tpr: Proportion
    tnr: Proportion
    ppv: Proportion
    npv: Proportion
    prevalence: Proportion
    kappa: float
    kappa_interval: Interval
    mcc: float
    balanced_accuracy: float
    f1: float

    @property
    def fpr(self) -> float:
        """False-alarm rate — the complement of specificity."""
        return 1.0 - self.tnr.value

    def to_dict(self) -> dict:
        """Plain data for ``emit``."""
        payload = asdict(self)
        for key in ("accuracy", "tpr", "tnr", "ppv", "npv", "prevalence"):
            payload[key]["value"] = getattr(self, key).value
        payload["fpr"] = self.fpr
        payload["n"] = self.confusion.n
        return payload


def wilson(k: int, n: int, level: float = DEFAULT_LEVEL) -> Interval:
    """Wilson score interval for a binomial proportion.

    Not the textbook normal approximation: at the rates that matter here — a
    judge that misses 2 of 30 problems — the Wald interval runs off the end of
    [0, 1] and reports impossible confidence. Wilson stays inside the unit
    interval and keeps nominal coverage down to single-digit counts.
    """
    if n <= 0:
        return Interval(float("nan"), float("nan"), level)
    z = float(norm.ppf(1 - (1 - level) / 2))
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return Interval(float(max(0.0, centre - half)), float(min(1.0, centre + half)), level)


def _proportion(k: int, n: int, level: float) -> Proportion:
    return Proportion(k=int(k), n=int(n), interval=wilson(int(k), int(n), level))


def confusion(human: Sequence[Verdict], judge: Sequence[Verdict]) -> Confusion:
    """Count paired verdicts. Order matters: element *i* is the same example."""
    if len(human) != len(judge):
        raise ValueError(f"paired labels must be the same length: {len(human)} != {len(judge)}")
    if not human:
        raise ValueError("no labels to compare")

    allowed = {"pass", "fail"}
    bad = sorted({v for v in (*human, *judge)} - allowed)
    if bad:
        raise ValueError(f"verdicts must be 'pass' or 'fail', got {bad}")

    h = np.array([v == "fail" for v in human])
    j = np.array([v == "fail" for v in judge])
    return Confusion(
        tp=int(np.sum(h & j)),
        fp=int(np.sum(~h & j)),
        fn=int(np.sum(h & ~j)),
        tn=int(np.sum(~h & ~j)),
    )


def cohen_kappa(c: Confusion) -> float:
    """Chance-corrected agreement.

    Raw accuracy flatters any judge on a skewed suite: if 95% of outputs are
    fine, a judge that never flags anything is 95% accurate and worthless.
    Kappa removes the agreement you would get by chance alone, which is why it
    is the number the gate is written against.
    """
    n = c.n
    if n == 0:
        return float("nan")
    observed = (c.tp + c.tn) / n
    human_fail = (c.tp + c.fn) / n
    judge_fail = (c.tp + c.fp) / n
    expected = human_fail * judge_fail + (1 - human_fail) * (1 - judge_fail)
    if expected == 1.0:
        # Both raters used one category for everything; agreement is entirely
        # explained by chance and kappa is undefined rather than perfect.
        return float("nan")
    return float((observed - expected) / (1 - expected))


def kappa_interval(c: Confusion, level: float = DEFAULT_LEVEL) -> Interval:
    """Asymptotic interval for kappa (Fleiss, Cohen & Everitt 1969).

    Categories are indexed 0 = fail, 1 = pass; rows are the human, columns the
    judge. The three terms are written out rather than vectorised because the
    index gymnastics in the published form is where implementations go wrong,
    and this one is checked against a worked example in the tests.
    """
    n = c.n
    k = cohen_kappa(c)
    if n == 0 or np.isnan(k):
        return Interval(float("nan"), float("nan"), level)

    p = np.array([[c.tp, c.fn], [c.fp, c.tn]], dtype=float) / n
    row = p.sum(axis=1)  # human: [fail, pass]
    col = p.sum(axis=0)  # judge: [fail, pass]
    pe = float(np.dot(row, col))
    if pe == 1.0:
        return Interval(float("nan"), float("nan"), level)

    # A: the agreeing cells, weighted by how much each marginal already explains.
    term_a = sum(p[i, i] * (1 - (row[i] + col[i]) * (1 - k)) ** 2 for i in range(2))
    # B: the disagreeing cells. Note the crossed marginals — column of i, row of j.
    term_b = (1 - k) ** 2 * sum(
        p[i, j] * (col[i] + row[j]) ** 2 for i in range(2) for j in range(2) if i != j
    )
    term_c = (k - pe * (1 - k)) ** 2

    variance = (term_a + term_b - term_c) / (n * (1 - pe) ** 2)
    if variance <= 0:
        return Interval(k, k, level)

    z = float(norm.ppf(1 - (1 - level) / 2))
    half = z * float(np.sqrt(variance))
    return Interval(float(max(-1.0, k - half)), float(min(1.0, k + half)), level)


def matthews(c: Confusion) -> float:
    """Matthews correlation — the one summary that degrades honestly on skew."""
    numerator = c.tp * c.tn - c.fp * c.fn
    denominator = np.sqrt(
        float(c.tp + c.fp) * float(c.tp + c.fn) * float(c.tn + c.fp) * float(c.tn + c.fn)
    )
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def agreement(
    human: Sequence[Verdict],
    judge: Sequence[Verdict],
    level: float = DEFAULT_LEVEL,
) -> Agreement:
    """Full agreement report for one judge against one set of human labels."""
    c = confusion(human, judge)
    human_fail = c.tp + c.fn
    human_pass = c.tn + c.fp
    judge_fail = c.tp + c.fp
    judge_pass = c.tn + c.fn

    tpr = _proportion(c.tp, human_fail, level)
    tnr = _proportion(c.tn, human_pass, level)
    f1_denominator = 2 * c.tp + c.fp + c.fn
    return Agreement(
        confusion=c,
        accuracy=_proportion(c.tp + c.tn, c.n, level),
        tpr=tpr,
        tnr=tnr,
        ppv=_proportion(c.tp, judge_fail, level),
        npv=_proportion(c.tn, judge_pass, level),
        prevalence=_proportion(human_fail, c.n, level),
        kappa=cohen_kappa(c),
        kappa_interval=kappa_interval(c, level),
        mcc=matthews(c),
        balanced_accuracy=float(np.mean([tpr.value, tnr.value])),
        f1=float(2 * c.tp / f1_denominator) if f1_denominator else float("nan"),
    )

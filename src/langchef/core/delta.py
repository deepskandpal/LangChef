"""Two calibrations of the same judge, compared — the rubric-iteration loop.

``calibrate report`` says how far a judge can be trusted. This module says
whether a *revision to the rubric* moved that, which is the only way to act on a
disagreement taxonomy without re-running everything and comparing two reports by
eye.

The inputs are one set of human labels and two sets of judge verdicts over the
same examples: the verdicts the old rubric produced, and the verdicts the
revised rubric produced. Nothing here does I/O, talks to a model, or knows what
a rubric is — the CLI hands it three aligned sequences of ``"pass"``/``"fail"``.

The pairing, which is the whole statistical content
---------------------------------------------------

**This comparison is paired, and every interval in this module accounts for it.**

The same examples are scored under both rubrics, and the human labels do not
move at all — a rubric revision changes the instrument, not the ground truth. So
:math:`\\hat\\kappa_{before}` and :math:`\\hat\\kappa_{after}` are two
measurements on one sample rather than two samples. Their sampling covariance is
large and positive, because a rubric revision typically moves a handful of
verdicts and leaves the rest exactly where they were.

An unpaired interval — the one you get from ``sqrt(var_before + var_after)``, or
from noticing that two reported kappa intervals overlap — throws that covariance
away and inflates the width. The consequence is not a rounding error: a rubric
revision that genuinely fixed six false alarms out of forty labels comes back
"no significant change", the revision is discarded, and the loop this command
exists to close never closes. This is the same defect as the M3 minimum
detectable effect computed with an unpaired formula on paired data, which
reported 15.6% where the truth was 6.0%, and it is the exact class of bug this
project exists to catch.

Two paired estimators, chosen for the two shapes of statistic:

``Δκ``
    Percentile bootstrap that resamples **examples**, carrying the human label
    and *both* judge verdicts together on every draw. Kappa is not a mean, so
    there is no exact test to reach for; resampling the triples preserves the
    covariance by construction rather than modelling it. Deterministic: the seed
    is part of the pin, exactly as in :mod:`langchef.core.compare`.

``ΔTPR`` and ``ΔTNR``
    Differences of *correlated proportions on a fixed denominator*. Because the
    human labels are identical under both rubrics, the human-fail subset and the
    human-pass subset are literally the same examples in both calibrations, so
    the denominators are fixed by design and only the numerators move. That is
    precisely McNemar's setting: the information is in the examples where the two
    rubrics disagree *with each other*, and the concordant ones carry none. The
    interval is the same paired percentile bootstrap ``compare`` already uses for
    two arms, so the two paired intervals in the product cannot drift apart.

**The unpaired shape is deliberately not supported.** Two calibrations sharing
no labelled examples differ by rubric *and* by example set, and no interval can
separate those two causes; the number would be a rubric delta in name only.
``calibrate diff`` therefore refuses rather than computing one, and when the two
sets overlap only partially the caller restricts to the intersection and reports
how many labels it dropped.

What is not corrected here
--------------------------

The labelled set is a stratified, confidence-selected subset (see
:mod:`langchef.core.sampling`), so these are rates *on the labelled examples*,
not estimates of the whole suite. The delta inherits that limitation from the
report it compares, and inherits it in a benign direction: both calibrations are
measured on the same biased sample, so the bias is common to both and largely
cancels in the difference. It does not cancel in the levels, which is why the
levels are reported as ``before`` and ``after`` rather than as the finding.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace

import numpy as np

from langchef.core.agreement import (
    DEFAULT_LEVEL,
    Agreement,
    Interval,
    Proportion,
    Verdict,
    agreement,
    wilson,
)
from langchef.core.compare import (
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    Discordance,
    discordance,
    holm,
    mcnemar_p,
    minimum_detectable_effect,
    paired_bootstrap_interval,
)

IMPROVED = "improved"
DEGRADED = "degraded"
INCONCLUSIVE = "inconclusive"

PAIRING = "paired"

PAIRED_NOTE = (
    "Paired. Both rubrics scored the same examples against the same human labels, "
    "so every interval here resamples examples and carries both verdicts with each "
    "draw. An unpaired interval would discard the covariance between the two "
    "calibrations and overstate the width, which is how a real improvement comes "
    "back as 'no significant change'."
)

FAMILY_NOTE = (
    "TPR and TNR are the two halves of one change, measured on disjoint subsets of "
    "the same labels; their exact McNemar p-values are Holm-corrected across that "
    "family of two, and a direction is named only when the corrected p clears alpha "
    "and the interval lies wholly on one side of zero. Kappa is the headline and is "
    "not in the family: it is corrected for chance, not for multiplicity, and its "
    "direction is read off its paired interval alone."
)


@dataclass(frozen=True)
class KappaDelta:
    """The change in chance-corrected agreement, with a paired interval.

    ``before_interval`` and ``after_interval`` are the ordinary Fleiss-Cohen-
    Everitt intervals for each calibration on its own. They are reported so a
    reader can see the levels, and they are **not** what ``interval`` is built
    from: two marginal intervals overlapping is not evidence that the difference
    is zero, and combining them as if they were independent is the mistake this
    module exists to avoid.
    """

    before: float
    after: float
    difference: float
    interval: Interval
    before_interval: Interval
    after_interval: Interval
    direction: str
    draws: int
    seed: int
    degenerate_draws: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RateDelta:
    """A paired difference of two rates measured on the same fixed subset.

    ``discordance`` counts agreement with the human, not pass and fail: within
    the human-fail subset the judge agrees exactly when it says "fail", so
    ``fixed`` is a problem the revision started catching and ``broke`` is one it
    stopped catching. Only those two cells move the estimate.
    """

    name: str
    subset: str
    before: Proportion
    after: Proportion
    difference: float
    interval: Interval
    p_value: float
    p_adjusted: float
    direction: str
    discordance: Discordance | None
    mde: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["before"]["value"] = self.before.value
        payload["after"]["value"] = self.after.value
        if self.discordance is not None:
            payload["discordance"]["n"] = self.discordance.n
            payload["discordance"]["discordant"] = self.discordance.discordant
        return payload


@dataclass(frozen=True)
class Movement:
    """Which disagreement bucket the rubric change moved.

    A delta in kappa says the judge got better. This says *how*: a revision that
    fixed four false alarms and introduced no misses is a different change from
    one that fixed four misses at the cost of four false alarms, and the two
    have different consequences for whoever reads the suite's verdicts.

    A human label never moves, so an example can only travel inside its own
    class: a miss can become an agreement and back, and a false alarm can become
    an agreement and back, but a miss can never become a false alarm.
    """

    misses_fixed: int
    misses_introduced: int
    false_alarms_fixed: int
    false_alarms_introduced: int
    unchanged: int
    examples: dict[str, tuple[str, ...]]

    @property
    def moved(self) -> int:
        return (
            self.misses_fixed
            + self.misses_introduced
            + self.false_alarms_fixed
            + self.false_alarms_introduced
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["moved"] = self.moved
        payload["examples"] = {key: list(value) for key, value in self.examples.items()}
        return payload


@dataclass(frozen=True)
class CalibrationDelta:
    """What ``calibrate diff`` writes, and what a person reads to keep or discard."""

    n: int
    level: float
    before: Agreement
    after: Agreement
    kappa: KappaDelta
    tpr: RateDelta
    tnr: RateDelta
    movement: Movement
    alpha: float

    @property
    def verdict(self) -> str:
        """The headline, read off kappa — the number the trust gate is written against."""
        return self.kappa.direction

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "level": self.level,
            "alpha": self.alpha,
            "verdict": self.verdict,
            "pairing": PAIRING,
            "note": PAIRED_NOTE,
            "family_note": FAMILY_NOTE,
            "kappa": self.kappa.to_dict(),
            "tpr": self.tpr.to_dict(),
            "tnr": self.tnr.to_dict(),
            "movement": self.movement.to_dict(),
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
        }


def _check(human: Sequence[Verdict], before: Sequence[Verdict], after: Sequence[Verdict]) -> None:
    """Refuse anything that is not three aligned sequences of verdicts."""
    if not (len(human) == len(before) == len(after)):
        raise ValueError(
            "a calibration delta is paired: the human labels and both sets of judge "
            f"verdicts must be the same length, got {len(human)}, {len(before)}, {len(after)}"
        )
    if not human:
        raise ValueError("no labels to compare")
    allowed = {"pass", "fail"}
    bad = sorted({*human, *before, *after} - allowed)
    if bad:
        raise ValueError(f"verdicts must be 'pass' or 'fail', got {bad}")


def _cells(human_fail: np.ndarray, judge_fail: np.ndarray) -> tuple[np.ndarray, ...]:
    """The four confusion counts along the last axis."""
    return (
        np.sum(human_fail & judge_fail, axis=-1),
        np.sum(~human_fail & judge_fail, axis=-1),
        np.sum(human_fail & ~judge_fail, axis=-1),
        np.sum(~human_fail & ~judge_fail, axis=-1),
    )


def kappa_from_cells(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray, tn: np.ndarray) -> np.ndarray:
    """Cohen's kappa from the four counts, elementwise over arrays.

    The same formula as :func:`langchef.core.agreement.cohen_kappa`, vectorised
    so a bootstrap can evaluate ten thousand resamples without a Python loop.
    Duplicating a formula is how two implementations drift, so a known-answer
    test asserts these agree draw for draw with the scalar one — which is itself
    checked against scikit-learn.

    A resample in which either rater used a single category throughout has
    ``pe == 1``; agreement is then entirely explained by chance and kappa is
    undefined, so those draws come back NaN and are dropped rather than counted
    as zeros.
    """
    n = tp + fp + fn + tn
    with np.errstate(divide="ignore", invalid="ignore"):
        observed = (tp + tn) / n
        human_fail = (tp + fn) / n
        judge_fail = (tp + fp) / n
        expected = human_fail * judge_fail + (1 - human_fail) * (1 - judge_fail)
        value = (observed - expected) / (1 - expected)
    return np.where(expected == 1.0, np.nan, value)


def kappa_delta(
    human: Sequence[Verdict],
    before: Sequence[Verdict],
    after: Sequence[Verdict],
    level: float = DEFAULT_LEVEL,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> KappaDelta:
    """Change in kappa, with a **paired** percentile bootstrap interval.

    One index vector per draw, applied to the human labels and to both sets of
    judge verdicts at once. That is the whole of the pairing: an example is
    either in a resample under both rubrics or in it under neither, so the
    positive covariance between the two kappas is carried through the draw
    instead of being assumed away.

    Resampling examples rather than the four confusion cells is deliberate too.
    The cells are not independent — they are one multinomial — and the example is
    the unit that was sampled, so it is the unit that gets resampled.
    """
    _check(human, before, after)
    h = np.array([v == "fail" for v in human])
    b = np.array([v == "fail" for v in before])
    a = np.array([v == "fail" for v in after])

    before_report = agreement(human, before, level)
    after_report = agreement(human, after, level)
    difference = after_report.kappa - before_report.kappa

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, h.size, size=(draws, h.size))
    resampled_human = h[idx]
    drawn = kappa_from_cells(*_cells(resampled_human, a[idx])) - kappa_from_cells(
        *_cells(resampled_human, b[idx])
    )
    finite = drawn[np.isfinite(drawn)]

    if finite.size == 0:
        interval = Interval(float("nan"), float("nan"), level)
    else:
        tail = (1 - level) / 2 * 100
        interval = Interval(
            float(np.percentile(finite, tail)),
            float(np.percentile(finite, 100 - tail)),
            level,
        )

    return KappaDelta(
        before=before_report.kappa,
        after=after_report.kappa,
        difference=float(difference),
        interval=interval,
        before_interval=before_report.kappa_interval,
        after_interval=after_report.kappa_interval,
        # No p-value, so the interval alone names the direction — the standing
        # rule in this codebase is that a direction only counts when the whole
        # interval agrees with it, and that half of the rule applies here.
        direction=(IMPROVED if interval.lo > 0 else DEGRADED if interval.hi < 0 else INCONCLUSIVE),
        draws=draws,
        seed=seed,
        degenerate_draws=int(drawn.size - finite.size),
    )


def _rate_delta(
    name: str,
    human: Sequence[Verdict],
    before: Sequence[Verdict],
    after: Sequence[Verdict],
    keep: Verdict,
    level: float,
) -> RateDelta:
    """ΔTPR (``keep='fail'``) or ΔTNR (``keep='pass'``), paired over a fixed subset.

    The subset is chosen by the *human* label, which is identical under both
    rubrics, so the denominator is the same set of examples in both calibrations
    and only the numerator can move. On that subset "the judge agreed with the
    person" is exactly "the judge said ``keep``", so the agreement rate is the
    TPR or the TNR and the paired machinery in ``compare`` applies unchanged.
    """
    rows = [(b, a) for label, b, a in zip(human, before, after, strict=True) if label == keep]
    subset = "human_fail" if keep == "fail" else "human_pass"
    n = len(rows)
    if n == 0:
        # No examples of this class were labelled, so the rate does not exist
        # under either rubric. A NaN that says so beats a zero that does not.
        nan_interval = Interval(float("nan"), float("nan"), level)
        empty = Proportion(k=0, n=0, interval=nan_interval)
        return RateDelta(
            name=name,
            subset=subset,
            before=empty,
            after=empty,
            difference=float("nan"),
            interval=nan_interval,
            p_value=float("nan"),
            p_adjusted=float("nan"),
            direction=INCONCLUSIVE,
            discordance=None,
            mde=float("nan"),
        )

    agreed_before = ["pass" if b == keep else "fail" for b, _ in rows]
    agreed_after = ["pass" if a == keep else "fail" for _, a in rows]
    d = discordance(agreed_before, agreed_after)
    k_before = d.both_pass + d.broke
    k_after = d.both_pass + d.fixed
    return RateDelta(
        name=name,
        subset=subset,
        before=Proportion(k=k_before, n=n, interval=wilson(k_before, n, level)),
        after=Proportion(k=k_after, n=n, interval=wilson(k_after, n, level)),
        difference=(k_after - k_before) / n,
        interval=paired_bootstrap_interval(agreed_before, agreed_after, level),
        p_value=mcnemar_p(d),
        p_adjusted=float("nan"),  # filled in by delta() once the family is known
        direction=INCONCLUSIVE,
        discordance=d,
        mde=minimum_detectable_effect(d.n, d.discordant, level),
    )


def _direction(interval: Interval, p_adjusted: float, alpha: float) -> str:
    """Both halves required: the corrected p, and an interval that agrees with it.

    Holm controls the false-positive rate across the family; the interval carries
    the standing rule that a direction only counts when the whole interval lies
    on one side of zero. Requiring both is conservative and, more usefully, means
    the payload can never name a direction the interval printed beside it
    contradicts.
    """
    if not p_adjusted < alpha:
        return INCONCLUSIVE
    if interval.lo > 0:
        return IMPROVED
    if interval.hi < 0:
        return DEGRADED
    return INCONCLUSIVE


def movement(
    human: Sequence[Verdict],
    before: Sequence[Verdict],
    after: Sequence[Verdict],
    example_ids: Sequence[str] | None = None,
    cap: int = 20,
) -> Movement:
    """Count which disagreement bucket each example moved between, if any."""
    _check(human, before, after)
    if example_ids is not None and len(example_ids) != len(human):
        raise ValueError(
            f"example_ids must align with the labels: {len(example_ids)} != {len(human)}"
        )
    ids = list(example_ids) if example_ids is not None else [""] * len(human)

    counts = dict.fromkeys(
        ("misses_fixed", "misses_introduced", "false_alarms_fixed", "false_alarms_introduced"), 0
    )
    examples: dict[str, list[str]] = {key: [] for key in counts}
    unchanged = 0
    for label, b, a, example_id in zip(human, before, after, ids, strict=True):
        if b == a:
            unchanged += 1
            continue
        agreed_after = a == label
        if label == "fail":
            key = "misses_fixed" if agreed_after else "misses_introduced"
        else:
            key = "false_alarms_fixed" if agreed_after else "false_alarms_introduced"
        counts[key] += 1
        if example_id:
            examples[key].append(example_id)

    return Movement(
        misses_fixed=counts["misses_fixed"],
        misses_introduced=counts["misses_introduced"],
        false_alarms_fixed=counts["false_alarms_fixed"],
        false_alarms_introduced=counts["false_alarms_introduced"],
        unchanged=unchanged,
        examples={key: tuple(value[:cap]) for key, value in examples.items()},
    )


def delta(
    human: Sequence[Verdict],
    before: Sequence[Verdict],
    after: Sequence[Verdict],
    level: float = DEFAULT_LEVEL,
    example_ids: Sequence[str] | None = None,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> CalibrationDelta:
    """The full paired comparison of two calibrations of the same judge.

    Element *i* is the same example throughout: ``human[i]`` is what the person
    said, ``before[i]`` what the judge said under the old rubric, ``after[i]``
    what it said under the revised one. Accuracy is deliberately absent — it is
    the number kappa exists to replace, and reporting both invites a reader to
    quote the flattering one.
    """
    _check(human, before, after)
    alpha = 1 - level

    kappa = kappa_delta(human, before, after, level, draws=draws, seed=seed)
    tpr = _rate_delta("tpr", human, before, after, "fail", level)
    tnr = _rate_delta("tnr", human, before, after, "pass", level)

    # The family is TPR and TNR: two tests on disjoint halves of the same labels,
    # and the two ways a rubric revision can move agreement. Accuracy is not in
    # it because it is a weighted average of these two and would pad the
    # correction with a redundant test; kappa is not in it because it is the
    # headline rather than a candidate culprit, exactly as the overall verdict in
    # `compare` sits outside its per-criterion family.
    tested = [rate for rate in (tpr, tnr) if rate.discordance is not None]
    adjusted = dict(
        zip(
            [rate.name for rate in tested],
            holm([rate.p_value for rate in tested]),
            strict=True,
        )
    )
    finished = {
        rate.name: (
            replace(
                rate,
                p_adjusted=adjusted[rate.name],
                direction=_direction(rate.interval, adjusted[rate.name], alpha),
            )
            if rate.name in adjusted
            else rate
        )
        for rate in (tpr, tnr)
    }

    return CalibrationDelta(
        n=len(human),
        level=level,
        alpha=alpha,
        before=agreement(human, before, level),
        after=agreement(human, after, level),
        kappa=kappa,
        tpr=finished["tpr"],
        tnr=finished["tnr"],
        movement=movement(human, before, after, example_ids),
    )

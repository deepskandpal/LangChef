"""M6 known-answer tests — the paired delta between two calibrations.

DECISIONS.md #7: every statistic is checked against an independent
implementation or a closed form. Here that means scikit-learn for kappa and the
two recalls, scipy's exact binomial for the McNemar p-values, a closed form for
the population kappa a simulation is generated from, and — for the one thing no
library will hand us — a coverage check across many simulated draws.

The tests this file exists for are the two in **"the pairing"** section. A delta
between two calibrations measured on the same labels is paired, and the whole
question is whether the interval says so. An unpaired interval is written out
here, once, as ``unpaired_kappa_interval``, purely so the two can be compared:
it lives in the test suite and must never appear under ``src/``.
"""

import json
import math

import numpy as np
import pytest
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score, recall_score

from langchef.core.agreement import DEFAULT_LEVEL, cohen_kappa, confusion, kappa_interval
from langchef.core.compare import discordance
from langchef.core.delta import (
    DEGRADED,
    IMPROVED,
    INCONCLUSIVE,
    delta,
    kappa_delta,
    kappa_from_cells,
    movement,
)

Z = 1.959963984540054


def _sk(verdicts):
    """sklearn wants numbers; the positive class is 'fail' — a finding."""
    return [1 if v == "fail" else 0 for v in verdicts]


def labelled(rng, n, prevalence=0.35, tpr=0.75, tnr=0.85):
    """A synthetic judge with known operating characteristics."""
    human = list(np.where(rng.random(n) < prevalence, "fail", "pass"))
    judge = []
    for h in human:
        if h == "fail":
            judge.append("fail" if rng.random() < tpr else "pass")
        else:
            judge.append("pass" if rng.random() < tnr else "fail")
    return human, judge


def revised(rng, judge, churn=0.15):
    """A second rubric that moves a share of the verdicts and leaves the rest."""
    return [("pass" if v == "fail" else "fail") if rng.random() < churn else v for v in judge]


def table(human, before, after):
    """Three aligned sequences from four counts per human class, for exact cases."""
    return list(human), list(before), list(after)


def scenario(tp, fp, fn, tn, fixed_alarms=0, fixed_misses=0):
    """A before-calibration by its confusion cells, and an after that repairs some.

    ``fixed_alarms`` false alarms and ``fixed_misses`` misses become agreements
    under the revised rubric; nothing else moves. Every example keeps its human
    label, which is the point — the labels do not change when a rubric does.
    """
    human = ["fail"] * (tp + fn) + ["pass"] * (fp + tn)
    before = ["fail"] * tp + ["pass"] * fn + ["fail"] * fp + ["pass"] * tn
    after = (
        ["fail"] * tp
        + ["fail"] * fixed_misses
        + ["pass"] * (fn - fixed_misses)
        + ["pass"] * fixed_alarms
        + ["fail"] * (fp - fixed_alarms)
        + ["pass"] * tn
    )
    return table(human, before, after)


def unpaired_kappa_interval(human, before, after, level=DEFAULT_LEVEL):
    """**The wrong interval**, written down so the right one can be measured against it.

    Two kappas treated as independent samples: take each one's asymptotic
    standard error and add the variances. It discards the covariance that the
    shared examples and shared labels induce, and it is what a reader does by
    eye when they check whether two reported kappa intervals overlap.

    This belongs to the test suite and to nowhere else. ``core`` must not grow a
    function that computes it.
    """
    se_before = kappa_interval(confusion(human, before), level).width / (2 * Z)
    se_after = kappa_interval(confusion(human, after), level).width / (2 * Z)
    se = math.sqrt(se_before**2 + se_after**2)
    difference = cohen_kappa(confusion(human, after)) - cohen_kappa(confusion(human, before))
    return difference - Z * se, difference + Z * se


def population_kappa(prevalence, tpr, fpr):
    """Closed-form kappa for a judge with known operating characteristics.

    The value a simulation converges to, so a coverage check has something true
    to cover.
    """
    tp = prevalence * tpr
    fn = prevalence * (1 - tpr)
    fp = (1 - prevalence) * fpr
    tn = (1 - prevalence) * (1 - fpr)
    observed = tp + tn
    expected = (tp + fn) * (tp + fp) + (fn + tn) * (fp + tn)
    return (observed - expected) / (1 - expected)


# --- the statistics, against independent implementations ---------------------


@pytest.mark.parametrize("seed", range(8))
def test_vectorised_kappa_matches_the_scalar_one_draw_for_draw(seed):
    """The bootstrap uses its own copy of the kappa formula; it must not drift.

    ``agreement.cohen_kappa`` is itself checked against scikit-learn, so this
    chains the vectorised form back to the independent implementation.
    """
    rng = np.random.default_rng(seed)
    human, judge = labelled(rng, 150)
    h = np.array([v == "fail" for v in human])
    j = np.array([v == "fail" for v in judge])
    idx = rng.integers(0, h.size, size=(40, h.size))
    hh, jj = h[idx], j[idx]

    vectorised = kappa_from_cells(
        np.sum(hh & jj, axis=-1),
        np.sum(~hh & jj, axis=-1),
        np.sum(hh & ~jj, axis=-1),
        np.sum(~hh & ~jj, axis=-1),
    )
    for draw, got in zip(idx, vectorised, strict=True):
        expected = cohen_kappa(
            confusion([human[i] for i in draw], [judge[i] for i in draw]),
        )
        assert got == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("seed", range(8))
def test_kappa_delta_is_the_difference_of_two_sklearn_kappas(seed):
    rng = np.random.default_rng(seed)
    human, before = labelled(rng, 200)
    after = revised(rng, before)
    result = kappa_delta(human, before, after, draws=200)
    expected = cohen_kappa_score(_sk(human), _sk(after)) - cohen_kappa_score(
        _sk(human), _sk(before)
    )
    assert result.difference == pytest.approx(expected, abs=1e-12)
    assert result.before == pytest.approx(cohen_kappa_score(_sk(human), _sk(before)), abs=1e-12)
    assert result.after == pytest.approx(cohen_kappa_score(_sk(human), _sk(after)), abs=1e-12)


@pytest.mark.parametrize("seed", range(8))
def test_tpr_and_tnr_deltas_match_sklearn_recall(seed):
    """TNR is recall with the other class positive; sklearn computes both."""
    rng = np.random.default_rng(seed)
    human, before = labelled(rng, 200)
    after = revised(rng, before)
    result = delta(human, before, after, draws=200)

    expected_tpr = recall_score(_sk(human), _sk(after), pos_label=1) - recall_score(
        _sk(human), _sk(before), pos_label=1
    )
    expected_tnr = recall_score(_sk(human), _sk(after), pos_label=0) - recall_score(
        _sk(human), _sk(before), pos_label=0
    )
    assert result.tpr.difference == pytest.approx(expected_tpr, abs=1e-12)
    assert result.tnr.difference == pytest.approx(expected_tnr, abs=1e-12)
    # The levels too, not just the movement between them.
    assert result.tpr.after.value == pytest.approx(
        recall_score(_sk(human), _sk(after), pos_label=1), abs=1e-12
    )
    assert result.tnr.before.value == pytest.approx(
        recall_score(_sk(human), _sk(before), pos_label=0), abs=1e-12
    )


def test_the_rate_p_values_are_the_exact_mcnemar_on_their_own_subset():
    """Counted by hand on the human-fail rows, then checked against scipy."""
    human, before, after = scenario(tp=16, fp=8, fn=4, tn=32, fixed_misses=3)
    result = delta(human, before, after, draws=200)

    # Among the twenty human-fail examples, three the old rubric missed are now
    # caught and none went the other way. That is the whole of the evidence.
    assert result.tpr.discordance.fixed == 3
    assert result.tpr.discordance.broke == 0
    assert result.tpr.p_value == pytest.approx(binomtest(0, 3, 0.5).pvalue)
    # The human-pass rows did not move at all, so there is nothing to test there.
    assert result.tnr.discordance.discordant == 0
    assert result.tnr.p_value == 1.0


def test_holm_is_applied_across_the_family_of_two_and_kappa_is_not_in_it():
    human, before, after = scenario(tp=10, fp=18, fn=10, tn=62, fixed_alarms=14)
    result = delta(human, before, after, draws=2000)

    # Two tests in the family; the smaller p is doubled, the larger stands.
    assert result.tnr.p_adjusted == pytest.approx(min(1.0, 2 * result.tnr.p_value))
    assert result.tpr.p_adjusted == pytest.approx(result.tpr.p_value)
    # Kappa carries no p-value at all: its direction comes from its interval.
    assert "p_value" not in result.kappa.to_dict()


# --- the pairing -------------------------------------------------------------


@pytest.mark.parametrize("seed", range(6))
def test_the_paired_interval_is_narrower_than_the_unpaired_one(seed):
    """The covariance is real, and throwing it away costs width every time."""
    rng = np.random.default_rng(seed)
    human, before = labelled(rng, 160)
    after = revised(rng, before, churn=0.12)

    paired = kappa_delta(human, before, after, draws=4000).interval
    lo, hi = unpaired_kappa_interval(human, before, after)
    assert paired.width < (hi - lo), "the paired interval is not buying anything"
    # Not a rounding difference: a twelve-percent rubric churn leaves most of the
    # verdicts identical, so most of the marginal variance is common to both.
    assert paired.width < 0.75 * (hi - lo)


def test_an_unpaired_interval_would_miss_a_real_improvement():
    """The bug this module exists to prevent, in the shape it actually arrives in.

    A revised rubric stops crying wolf on seven of eight good answers and changes
    nothing else. Kappa moves from 0.57 to 0.81 — the revision plainly worked,
    and it worked on the same sixty labels, so the only uncertainty is which
    seven examples the sample happened to contain.

    Treat the two calibrations as independent samples and their standard errors
    add: the interval straddles zero, the finding is "no significant change", the
    rubric revision is discarded, and the loop never closes. This is the M3
    minimum-detectable-effect defect wearing different clothes.
    """
    human, before, after = scenario(tp=16, fp=8, fn=4, tn=32, fixed_alarms=7)

    result = delta(human, before, after)
    assert result.kappa.before == pytest.approx(0.5714285714285714)
    assert result.kappa.after == pytest.approx(0.8051948051948052)

    # Paired: every draw that contains a repaired example moves the same way.
    assert result.kappa.interval.lo > 0
    assert result.verdict == IMPROVED

    lo, hi = unpaired_kappa_interval(human, before, after)
    assert lo < 0 < hi, "the unpaired interval was supposed to straddle zero here"
    # And the marginal intervals overlap, which is the same mistake made by eye.
    assert result.kappa.before_interval.hi > result.kappa.after_interval.lo


def test_the_paired_interval_covers_the_truth_at_the_nominal_rate():
    """Coverage across many simulated draws, not correctness on one example.

    Both judges are generated from known operating characteristics, so the true
    delta has a closed form. The second judge copies the first three times in
    four and redraws otherwise, which is what makes the pair correlated — the
    property the interval has to respect.
    """
    prevalence, tpr_before, tnr_before = 0.35, 0.75, 0.85
    copy, tpr_redraw, tnr_redraw = 0.75, 0.95, 0.90

    tpr_after = copy * tpr_before + (1 - copy) * tpr_redraw
    fpr_after = copy * (1 - tnr_before) + (1 - copy) * (1 - tnr_redraw)
    truth = population_kappa(prevalence, tpr_after, fpr_after) - population_kappa(
        prevalence, tpr_before, 1 - tnr_before
    )

    rng = np.random.default_rng(11)
    n, trials, covered = 200, 200, 0
    for _ in range(trials):
        human, before = labelled(rng, n, prevalence, tpr_before, tnr_before)
        after = []
        for h, b in zip(human, before, strict=True):
            if rng.random() < copy:
                after.append(b)
            elif h == "fail":
                after.append("fail" if rng.random() < tpr_redraw else "pass")
            else:
                after.append("pass" if rng.random() < tnr_redraw else "fail")
        interval = kappa_delta(human, before, after, draws=400, seed=0).interval
        covered += interval.lo <= truth <= interval.hi

    rate = covered / trials
    assert 0.88 <= rate <= 0.995, f"nominal 95% interval covered {rate:.0%} of the time"


def test_an_unpaired_interval_would_be_wider_than_it_needs_to_be_on_that_same_model():
    """The other half of coverage: the paired interval is not merely valid, it is tighter."""
    rng = np.random.default_rng(5)
    human, before = labelled(rng, 200)
    after = [b if rng.random() < 0.85 else ("pass" if b == "fail" else "fail") for b in before]
    paired = kappa_delta(human, before, after, draws=4000).interval
    lo, hi = unpaired_kappa_interval(human, before, after)
    assert paired.width < hi - lo


# --- what the numbers mean ---------------------------------------------------


def test_an_identical_rubric_moves_nothing():
    """The null case has to be exactly zero, not nearly zero."""
    rng = np.random.default_rng(2)
    human, judge = labelled(rng, 80)
    result = delta(human, judge, judge, draws=500)
    assert result.kappa.difference == 0.0
    assert result.kappa.interval.lo == 0.0 and result.kappa.interval.hi == 0.0
    assert result.tpr.difference == 0.0 and result.tnr.difference == 0.0
    assert result.tpr.p_value == 1.0 and result.tnr.p_value == 1.0
    assert result.verdict == INCONCLUSIVE
    assert result.movement.moved == 0
    assert result.movement.unchanged == 80


def test_a_revision_that_only_stops_crying_wolf_leaves_the_catch_rate_alone():
    """Which bucket moved is the actionable half, so it has to be reported separately."""
    human, before, after = scenario(tp=10, fp=18, fn=10, tn=62, fixed_alarms=14)
    result = delta(human, before, after, draws=2000)

    assert result.tpr.difference == 0.0
    assert result.tpr.direction == INCONCLUSIVE
    assert result.tnr.difference == pytest.approx(14 / 80)
    assert result.tnr.direction == IMPROVED
    assert result.movement.false_alarms_fixed == 14
    assert result.movement.misses_fixed == result.movement.misses_introduced == 0


def test_a_revision_that_trades_misses_for_false_alarms_is_not_called_an_improvement():
    """Both halves move, in opposite directions; kappa is the arbiter and it shrugs."""
    human, before, after = scenario(tp=12, fp=6, fn=8, tn=44, fixed_misses=4, fixed_alarms=0)
    # Now break four clean answers in the other direction.
    after = list(after)
    broken = 0
    for index, (h, verdict) in enumerate(zip(human, after, strict=True)):
        if h == "pass" and verdict == "pass" and broken < 4:
            after[index] = "fail"
            broken += 1
    result = delta(human, before, after, draws=2000)
    assert result.movement.misses_fixed == 4
    assert result.movement.false_alarms_introduced == 4
    assert result.tpr.difference > 0 > result.tnr.difference


def test_movement_reconciles_with_the_discordant_cells():
    """Two routes to the same counts. If they disagree, one of them is wrong."""
    rng = np.random.default_rng(9)
    human, before = labelled(rng, 240)
    after = revised(rng, before, churn=0.2)
    result = delta(human, before, after, draws=200)

    assert result.movement.misses_fixed == result.tpr.discordance.fixed
    assert result.movement.misses_introduced == result.tpr.discordance.broke
    assert result.movement.false_alarms_fixed == result.tnr.discordance.fixed
    assert result.movement.false_alarms_introduced == result.tnr.discordance.broke
    assert result.movement.moved + result.movement.unchanged == result.n


def test_movement_names_the_examples_that_moved():
    human, before, after = scenario(tp=4, fp=4, fn=4, tn=8, fixed_alarms=2, fixed_misses=1)
    ids = [f"ex-{i:02}" for i in range(len(human))]
    moved = movement(human, before, after, ids)
    assert len(moved.examples["false_alarms_fixed"]) == 2
    assert len(moved.examples["misses_fixed"]) == 1
    assert all(name.startswith("ex-") for name in moved.examples["false_alarms_fixed"])


def test_a_direction_is_never_named_against_its_own_interval():
    """A payload that says 'improved' beside an interval containing zero is a lie."""
    rng = np.random.default_rng(6)
    for seed in range(12):
        human, before = labelled(rng, 90)
        after = revised(rng, before, churn=0.25)
        result = delta(human, before, after, draws=400, seed=seed)
        for part in (result.kappa, result.tpr, result.tnr):
            if part.direction == IMPROVED:
                assert part.interval.lo > 0
            elif part.direction == DEGRADED:
                assert part.interval.hi < 0


def test_the_delta_is_deterministic():
    """The contract calls `calibrate diff` deterministic; the seed is the pin."""
    rng = np.random.default_rng(13)
    human, before = labelled(rng, 100)
    after = revised(rng, before)
    first = delta(human, before, after, draws=1000).to_dict()
    second = delta(human, before, after, draws=1000).to_dict()
    assert first == second


def test_a_label_set_with_only_one_class_says_so_rather_than_reporting_zero():
    """No human called anything bad, so there is no catch rate to compare."""
    human = ["pass"] * 30
    before = ["fail"] * 6 + ["pass"] * 24
    after = ["fail"] * 2 + ["pass"] * 28
    result = delta(human, before, after, draws=300)
    assert result.tpr.discordance is None
    assert math.isnan(result.tpr.difference)
    assert result.tpr.direction == INCONCLUSIVE
    assert result.tnr.difference == pytest.approx(4 / 30)


def test_the_detection_limit_is_quoted_on_an_inconclusive_rate():
    """An inconclusive result is a finding, and the finding needs a number."""
    human, before, after = scenario(tp=10, fp=10, fn=10, tn=70, fixed_alarms=1)
    result = delta(human, before, after, draws=1000)
    assert result.tnr.direction == INCONCLUSIVE
    assert 0.0 < result.tnr.mde < 1.0


def test_mismatched_or_empty_or_unknown_verdicts_are_refused():
    with pytest.raises(ValueError, match="same length"):
        delta(["pass"], ["pass", "fail"], ["pass", "fail"])
    with pytest.raises(ValueError, match="same length"):
        delta(["pass", "fail"], ["pass", "fail"], ["pass"])
    with pytest.raises(ValueError, match="no labels"):
        delta([], [], [])
    with pytest.raises(ValueError, match="must be 'pass' or 'fail'"):
        delta(["pass", "fail"], ["pass", "maybe"], ["pass", "fail"])
    with pytest.raises(ValueError, match="must align"):
        movement(["pass", "fail"], ["pass", "fail"], ["pass", "fail"], ["only-one"])


def test_delta_serialises_to_plain_json():
    rng = np.random.default_rng(4)
    human, before = labelled(rng, 120)
    after = revised(rng, before)
    payload = delta(human, before, after, draws=300).to_dict()

    text = json.dumps(payload, sort_keys=True)
    assert json.loads(text)["pairing"] == "paired"
    assert payload["kappa"]["interval"]["level"] == 0.95
    assert payload["before"]["n"] == payload["after"]["n"] == 120
    assert payload["tpr"]["subset"] == "human_fail"
    assert payload["tnr"]["subset"] == "human_pass"
    # The note has to travel with the number: a delta quoted without it reads
    # like two independent measurements, which is what it deliberately is not.
    assert "paired" in payload["note"].lower()


def test_the_discordant_cells_are_the_only_thing_that_moves_a_rate():
    """Padding both calibrations with examples they agree on must change nothing."""
    small = delta(*scenario(tp=4, fp=6, fn=2, tn=8, fixed_alarms=4), draws=800)
    padded = delta(*scenario(tp=4, fp=6, fn=2, tn=208, fixed_alarms=4), draws=800)
    assert small.tnr.discordance.discordant == padded.tnr.discordance.discordant == 4
    assert small.tnr.p_value == padded.tnr.p_value
    # The rate itself is diluted by the padding, which is correct — the *evidence*
    # is not.
    assert padded.tnr.difference < small.tnr.difference


def test_discordance_is_counted_on_agreement_not_on_pass_and_fail():
    """A guard on the one mapping in this module that is easy to invert."""
    human, before, after = scenario(tp=5, fp=5, fn=5, tn=5, fixed_misses=2)
    result = delta(human, before, after, draws=200)
    agreed_before = ["pass" if b == h else "fail" for h, b in zip(human, before, strict=True)]
    agreed_after = ["pass" if a == h else "fail" for h, a in zip(human, after, strict=True)]
    overall = discordance(agreed_before, agreed_after)
    assert result.tpr.discordance.fixed + result.tnr.discordance.fixed == overall.fixed
    assert result.tpr.discordance.broke + result.tnr.discordance.broke == overall.broke

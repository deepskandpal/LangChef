"""M1 known-answer tests — DECISIONS.md #7.

Core hand-rolls every statistic it ships, so each one is checked here against an
independent implementation (scikit-learn, scipy) or a closed form. scikit-learn
is a *test* dependency for exactly this reason: if the product and its check
came from the same library, the check would only prove the library agrees with
itself.
"""

import numpy as np
import pytest
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score, confusion_matrix, matthews_corrcoef

from langchef.core.agreement import (
    agreement,
    cohen_kappa,
    confusion,
    kappa_interval,
    matthews,
    wilson,
)


def _labels(rng, n, prevalence=0.3, tpr=0.8, tnr=0.9):
    """A synthetic judge with known operating characteristics."""
    human = np.where(rng.random(n) < prevalence, "fail", "pass")
    judge = []
    for h in human:
        if h == "fail":
            judge.append("fail" if rng.random() < tpr else "pass")
        else:
            judge.append("pass" if rng.random() < tnr else "fail")
    return list(human), judge


def _sk(labels):
    """sklearn wants numbers; the positive class is 'fail' (see the module docstring)."""
    return [1 if v == "fail" else 0 for v in labels]


@pytest.mark.parametrize("seed", range(12))
def test_confusion_matches_sklearn(seed):
    rng = np.random.default_rng(seed)
    human, judge = _labels(rng, 200)
    c = confusion(human, judge)
    tn, fp, fn, tp = confusion_matrix(_sk(human), _sk(judge), labels=[0, 1]).ravel()
    assert (c.tp, c.fp, c.fn, c.tn) == (tp, fp, fn, tn)


@pytest.mark.parametrize("seed", range(12))
def test_kappa_matches_sklearn(seed):
    rng = np.random.default_rng(seed)
    human, judge = _labels(rng, 200)
    assert cohen_kappa(confusion(human, judge)) == pytest.approx(
        cohen_kappa_score(_sk(human), _sk(judge)), abs=1e-12
    )


@pytest.mark.parametrize("seed", range(12))
def test_mcc_matches_sklearn(seed):
    rng = np.random.default_rng(seed)
    human, judge = _labels(rng, 200)
    assert matthews(confusion(human, judge)) == pytest.approx(
        matthews_corrcoef(_sk(human), _sk(judge)), abs=1e-12
    )


@pytest.mark.parametrize(("k", "n"), [(17, 22), (0, 30), (30, 30), (1, 5), (450, 1000)])
def test_wilson_matches_scipy(k, n):
    """scipy's binomtest carries its own Wilson implementation."""
    expected = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    got = wilson(k, n)
    assert got.lo == pytest.approx(expected.low, abs=1e-12)
    assert got.hi == pytest.approx(expected.high, abs=1e-12)


def test_wilson_stays_inside_the_unit_interval_at_the_edges():
    """The reason we are not using the Wald approximation."""
    for k, n in [(0, 10), (10, 10), (1, 100), (99, 100)]:
        interval = wilson(k, n)
        assert 0.0 <= interval.lo <= interval.hi <= 1.0


def test_wilson_of_nothing_is_not_a_number():
    interval = wilson(0, 0)
    assert np.isnan(interval.lo) and np.isnan(interval.hi)


def test_perfect_and_chance_agreement_are_the_closed_forms():
    perfect = confusion(["fail", "pass"] * 20, ["fail", "pass"] * 20)
    assert cohen_kappa(perfect) == pytest.approx(1.0)

    # Judge flags exactly half at random against 50% prevalence: agreement is
    # entirely chance, so kappa is 0 even though accuracy is 50%.
    human = ["fail"] * 50 + ["pass"] * 50
    judge = (["fail"] * 25 + ["pass"] * 25) * 2
    assert cohen_kappa(confusion(human, judge)) == pytest.approx(0.0, abs=1e-12)


def test_a_judge_that_never_flags_anything_is_not_rewarded():
    """The whole reason the gate is written against kappa and not accuracy."""
    human = ["fail"] * 5 + ["pass"] * 95
    judge = ["pass"] * 100
    report = agreement(human, judge)
    assert report.accuracy.value == pytest.approx(0.95)
    # 95% accurate and worth nothing: kappa sees straight through it.
    assert report.kappa == pytest.approx(0.0)
    assert cohen_kappa_score(_sk(human), _sk(judge)) == pytest.approx(0.0)
    assert report.tpr.value == pytest.approx(0.0)
    assert report.mcc == pytest.approx(0.0)


def test_kappa_interval_brackets_kappa_and_narrows_with_evidence():
    rng = np.random.default_rng(0)
    widths = []
    for n in (50, 200, 800, 3200):
        human, judge = _labels(rng, n)
        c = confusion(human, judge)
        interval = kappa_interval(c)
        assert interval.lo <= cohen_kappa(c) <= interval.hi
        widths.append(interval.width)
    assert widths == sorted(widths, reverse=True)


def test_kappa_interval_agrees_with_a_bootstrap():
    """The asymptotic variance is the easiest formula in this file to get wrong.

    A bootstrap knows nothing about Fleiss-Cohen-Everitt, so if the two standard
    errors line up, the index gymnastics in ``kappa_interval`` is right.
    """
    rng = np.random.default_rng(7)
    human, judge = _labels(rng, 600, prevalence=0.35, tpr=0.75, tnr=0.85)
    asymptotic_se = kappa_interval(confusion(human, judge)).width / (2 * 1.959963984540054)

    human_arr, judge_arr = np.array(human), np.array(judge)
    draws = []
    for _ in range(400):
        idx = rng.integers(0, len(human_arr), len(human_arr))
        draws.append(cohen_kappa(confusion(list(human_arr[idx]), list(judge_arr[idx]))))
    bootstrap_se = float(np.std(draws, ddof=1))

    assert asymptotic_se == pytest.approx(bootstrap_se, rel=0.20)


def test_recovers_the_operating_characteristics_it_was_built_from():
    rng = np.random.default_rng(3)
    human, judge = _labels(rng, 4000, prevalence=0.3, tpr=0.8, tnr=0.9)
    report = agreement(human, judge)
    assert report.tpr.value == pytest.approx(0.8, abs=0.03)
    assert report.tnr.value == pytest.approx(0.9, abs=0.03)
    assert report.fpr == pytest.approx(0.1, abs=0.03)
    assert report.prevalence.value == pytest.approx(0.3, abs=0.03)
    assert report.tpr.interval.lo <= 0.8 <= report.tpr.interval.hi


def test_mismatched_or_empty_or_unknown_verdicts_are_refused():
    with pytest.raises(ValueError, match="same length"):
        confusion(["pass"], ["pass", "fail"])
    with pytest.raises(ValueError, match="no labels"):
        confusion([], [])
    with pytest.raises(ValueError, match="must be 'pass' or 'fail'"):
        confusion(["pass", "maybe"], ["pass", "fail"])


def test_report_serialises_to_plain_data():
    human, judge = _labels(np.random.default_rng(1), 120)
    payload = agreement(human, judge).to_dict()
    assert payload["n"] == 120
    assert payload["confusion"]["tp"] + payload["confusion"]["fn"] == payload["prevalence"]["k"]
    assert 0.0 <= payload["tpr"]["value"] <= 1.0
    assert payload["tpr"]["interval"]["level"] == 0.95

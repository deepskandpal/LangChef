"""M1/M6 — paired comparison. Checked against scipy and against simulation."""

import numpy as np
import pytest
from scipy.stats import binomtest

from langchef.core.compare import (
    compare,
    discordance,
    mcnemar_p,
    minimum_detectable_effect,
)


def arms(both_pass, fixed, broke, both_fail):
    """Build two arms with an exact discordance table."""
    baseline = ["pass"] * both_pass + ["fail"] * fixed + ["pass"] * broke + ["fail"] * both_fail
    variant = ["pass"] * both_pass + ["pass"] * fixed + ["fail"] * broke + ["fail"] * both_fail
    return baseline, variant


def test_discordance_counts_the_four_cells():
    d = discordance(*arms(both_pass=10, fixed=3, broke=7, both_fail=5))
    assert (d.both_pass, d.fixed, d.broke, d.both_fail) == (10, 3, 7, 5)
    assert d.n == 25
    assert d.discordant == 10


def test_mcnemar_matches_the_exact_binomial():
    d = discordance(*arms(12, 4, 11, 3))
    assert mcnemar_p(d) == pytest.approx(binomtest(11, 15, 0.5).pvalue)


def test_concordant_only_is_not_evidence_of_anything():
    """40 goldens, none flipped: p = 1, and the interval is a point at zero."""
    result = compare(*arms(both_pass=30, fixed=0, broke=0, both_fail=10))
    assert result.p_value == 1.0
    assert result.difference == 0.0
    assert result.inconclusive
    assert not result.regression and not result.improvement


def test_a_clear_regression_is_flagged():
    result = compare(*arms(both_pass=60, fixed=1, broke=19, both_fail=20))
    assert result.regression
    assert result.verdict == "regression"
    assert result.interval.hi < 0
    assert result.difference == pytest.approx(-0.18)


def test_a_clear_improvement_is_flagged():
    result = compare(*arms(both_pass=40, fixed=20, broke=1, both_fail=39))
    assert result.improvement
    assert result.verdict == "improvement"
    assert result.interval.lo > 0


def test_only_discordant_pairs_move_the_estimate():
    """The pairing is the point: adding agreeing pairs must not flip a verdict."""
    small = compare(*arms(both_pass=10, fixed=0, broke=8, both_fail=2))
    padded = compare(*arms(both_pass=310, fixed=0, broke=8, both_fail=2))
    assert small.discordance.discordant == padded.discordance.discordant
    assert small.p_value == padded.p_value  # McNemar ignores the concordant cells


def test_mde_shrinks_with_goldens_and_grows_with_churn():
    assert minimum_detectable_effect(400, 10) < minimum_detectable_effect(90, 10)
    assert minimum_detectable_effect(90, 40) > minimum_detectable_effect(90, 4)


def test_mde_of_a_quiet_run_is_bounded_not_zero():
    """Nothing flipped is not evidence that any effect was detectable."""
    quiet = minimum_detectable_effect(90, 0)
    assert 0.0 < quiet < 0.15
    assert minimum_detectable_effect(1000, 0) < quiet


def test_mde_is_honest_about_what_a_run_could_see():
    """Simulate at the MDE and confirm the run detects it about `power` of the time."""
    rng = np.random.default_rng(4)
    n, psi = 200, 0.30
    threshold = minimum_detectable_effect(n, int(psi * n))
    detected = 0
    trials = 200
    for _ in range(trials):
        # A true effect exactly at the reported threshold.
        broke_p = (psi + threshold) / 2
        flips = rng.random(n)
        baseline, variant = [], []
        for flip in flips:
            if flip < broke_p:
                baseline.append("pass")
                variant.append("fail")
            elif flip < psi:
                baseline.append("fail")
                variant.append("pass")
            else:
                baseline.append("pass")
                variant.append("pass")
        if compare(baseline, variant).regression:
            detected += 1
    # Generous band: the point is that the quoted threshold is roughly the
    # detection boundary, not that the normal approximation is exact.
    assert 0.55 <= detected / trials <= 0.98


def test_mismatched_or_empty_arms_are_refused():
    with pytest.raises(ValueError, match="same length"):
        discordance(["pass"], ["pass", "fail"])
    with pytest.raises(ValueError, match="no goldens"):
        discordance([], [])
    with pytest.raises(ValueError, match="must be 'pass' or 'fail'"):
        discordance(["pass", "unknown"], ["pass", "fail"])


def test_comparison_serialises_with_its_verdict():
    payload = compare(*arms(50, 2, 12, 6)).to_dict()
    assert payload["n"] == 70
    assert payload["discordant"] == 14
    assert payload["verdict"] in ("regression", "improvement", "inconclusive")
    assert payload["discordance"]["broke"] == 12

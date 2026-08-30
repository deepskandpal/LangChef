"""M1/M6 — paired comparison. Checked against scipy and against simulation."""

import numpy as np
import pytest
from scipy.stats import binomtest

from langchef.core.compare import (
    Outcome,
    by_criterion,
    compare,
    discordance,
    holm,
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


# --- per-criterion attribution -------------------------------------------------


def cell(spec):
    """``None`` is a pass; a string is a failure citing that criterion."""
    return Outcome("pass", None) if spec is None else Outcome("fail", spec)


def suite(*cells):
    """Two paired arms from ``(count, baseline, variant)`` cells."""
    left, right = [], []
    for count, before, after in cells:
        left += [cell(before)] * count
        right += [cell(after)] * count
    return left, right


def named(result, criterion):
    return next(c for c in result.criteria if c.criterion == criterion)


def test_holm_matches_the_ladder_computed_by_hand():
    """Four p-values whose adjustment can be checked without any library.

    Sorted the values are 0.01, 0.03, 0.04, 0.9 against multipliers 4, 3, 2, 1,
    giving 0.04, 0.09, 0.08, 0.9. The third one came out *below* the second, so
    the running maximum has to drag 0.09 forward — otherwise a larger p-value
    ends up more significant than a smaller one. That carry is the step a
    hand-rolled Holm gets wrong, which is why it is the example.
    """
    assert holm([0.01, 0.04, 0.03, 0.9]) == pytest.approx([0.04, 0.09, 0.09, 0.9])
    assert holm([0.5]) == pytest.approx([0.5])
    assert holm([]) == []
    # Everything tiny: the largest is still compared against alpha itself, which
    # is the whole reason to prefer Holm over Bonferroni.
    assert holm([0.001, 0.002, 0.049])[2] == pytest.approx(0.049)


def test_holm_holds_the_family_error_rate_that_five_raw_tests_do_not():
    """The reason the correction is here at all, as a rate rather than an assertion.

    Under a true null a p-value is uniform, so five independent criteria give
    about a 23% chance that at least one lands under 0.05. That is the false
    finding this module would otherwise print five times a week. Holm has to
    hold the same quantity at or under 0.05.
    """
    rng = np.random.default_rng(11)
    draws = rng.random((20_000, 5))
    uncorrected = float(np.mean(draws.min(axis=1) < 0.05))
    corrected = np.mean([min(holm(list(row))) < 0.05 for row in draws])
    assert uncorrected == pytest.approx(1 - 0.95**5, abs=0.01)  # ~0.226
    assert corrected <= 0.05


def test_one_criterion_broke_and_the_other_held():
    """The sentence the feature exists to produce, on a suite with a known answer.

    Twelve goldens break on Groundedness and nothing else moves except three
    Correctness failures that swap places. The overall verdict is one number;
    the useful reading is that retrieval broke and generation did not.
    """
    baseline, variant = suite(
        (70, None, None),
        (12, "Groundedness", "Groundedness"),
        (12, None, "Groundedness"),
        (3, "Correctness", None),
        (3, None, "Correctness"),
    )
    result = by_criterion(baseline, variant)

    grounded = named(result, "Groundedness")
    assert grounded.difference == pytest.approx(-0.12)
    assert grounded.discordance.broke == 12 and grounded.discordance.fixed == 0
    assert grounded.attribution == "moved_worse"

    correct = named(result, "Correctness")
    assert correct.difference == pytest.approx(0.0)
    assert correct.discordance.discordant == 6  # three each way: a wash, not a hold
    assert correct.attribution == "inconclusive"

    assert result.criteria[0].criterion == "Groundedness"  # worst first


def test_the_criteria_account_for_the_whole_overall_difference():
    """A breakdown that explains less than the headline is how a memo misleads.

    Exactly one criterion is cited per failure, so the per-criterion differences
    must sum to the overall difference to the last decimal. The remainder is
    reported rather than assumed to be zero.
    """
    baseline, variant = suite(
        (40, None, None),
        (9, None, "Groundedness"),
        (4, "Correctness", None),
        (5, None, "Directness"),
        (2, "Directness", "Correctness"),
    )
    result = by_criterion(baseline, variant)
    overall = compare([o.verdict for o in baseline], [o.verdict for o in variant])

    assert result.attributed == pytest.approx(overall.difference)
    assert result.unattributed == pytest.approx(0.0)
    assert result.uncited_failures == 0


def test_pairing_happens_inside_a_criterion_and_never_across_two():
    """An example that fails a different criterion in each arm moved, it did not hold.

    Overall the verdict never changes — fail in both arms — so the headline sees
    nothing. Within the criteria it is a Correctness fix and a Groundedness
    break, which is precisely the attribution a reader needs. Pairing across
    criteria would cancel it into silence.
    """
    baseline, variant = suite((30, None, None), (10, "Correctness", "Groundedness"))
    overall = compare([o.verdict for o in baseline], [o.verdict for o in variant])
    assert overall.discordance.discordant == 0

    result = by_criterion(baseline, variant)
    assert named(result, "Correctness").discordance.fixed == 10
    assert named(result, "Groundedness").discordance.broke == 10
    assert result.attributed == pytest.approx(0.0)


def test_the_exact_mcnemar_inside_a_criterion_is_the_same_test():
    """Per criterion is the same paired test on a subset, not a new one."""
    baseline, variant = suite(
        (50, None, None),
        (11, None, "Groundedness"),
        (4, "Groundedness", None),
        (6, None, "Correctness"),
    )
    grounded = named(by_criterion(baseline, variant), "Groundedness")
    assert grounded.p_value == pytest.approx(binomtest(11, 15, 0.5).pvalue)


def test_an_interval_clear_of_zero_is_not_on_its_own_an_attribution():
    """Five flips one way: the bootstrap excludes zero, the exact test cannot reject.

    Five heads in five tosses is p = 0.0625, and no correction makes that
    smaller. Naming a direction here on the strength of the interval alone is
    how a breakdown manufactures a finding out of five examples.
    """
    baseline, variant = suite((85, None, None), (5, "Correctness", None))
    correct = named(by_criterion(baseline, variant), "Correctness")

    assert correct.interval.lo > 0  # the interval alone would have called it
    assert correct.p_value == pytest.approx(0.0625)
    assert correct.p_adjusted == pytest.approx(0.0625)  # k = 1, nothing to correct
    assert correct.attribution == "inconclusive"


def test_the_correction_can_be_what_withholds_a_direction():
    """The same nine flips read differently once four criteria were examined.

    Nine one-way flips is p = 0.0039 on its own. Ask the same question of five
    criteria and the strictest rung of the ladder is 0.05/5 = 0.01, which 0.0039
    still clears — but a marginal criterion beside it does not, and that is the
    finding the uncorrected reading would have printed.
    """
    baseline, variant = suite(
        (60, None, None),
        (9, None, "Groundedness"),
        (6, None, "Correctness"),
        (5, "Directness", None),
        (5, None, "Fluency"),
        (5, "Citation", None),
    )
    result = by_criterion(baseline, variant)
    assert result.family == 5
    assert result.method == "holm"

    grounded = named(result, "Groundedness")
    assert grounded.p_value == pytest.approx(2 / 2**9)
    assert grounded.p_adjusted == pytest.approx(5 * 2 / 2**9)
    assert grounded.attribution == "moved_worse"

    correct = named(result, "Correctness")
    assert correct.p_value == pytest.approx(2 / 2**6)  # 0.031 — under alpha on its own
    assert correct.p_adjusted > 0.05
    assert correct.attribution == "inconclusive"


def test_a_criterion_reports_the_limit_it_was_actually_judged_against():
    """The trap the issue names: an overall limit quoted beside a per-criterion claim.

    Each criterion is tested at the strictest rung of the Holm ladder, alpha/k,
    so that is the level its detection limit has to be computed at. Quoting the
    nominal-level number instead would advertise a sensitivity no criterion was
    ever held to.
    """
    baseline, variant = suite(
        (70, None, None),
        (10, None, "Groundedness"),
        (10, "Correctness", None),
    )
    result = by_criterion(baseline, variant)
    assert result.mde_level == pytest.approx(1 - 0.05 / 2)

    for c in result.criteria:
        assert c.mde == pytest.approx(
            minimum_detectable_effect(90, c.discordance.discordant, 1 - 0.05 / 2)
        )
        assert c.mde > minimum_detectable_effect(90, c.discordance.discordant, 0.95)


def test_a_quiet_criterion_still_says_what_it_could_not_have_seen():
    """Nothing flipped on Directness. That is a bound, not a clean bill of health."""
    baseline, variant = suite((80, None, None), (10, "Directness", "Directness"))
    directness = named(by_criterion(baseline, variant), "Directness")
    assert directness.discordance.discordant == 0
    assert directness.attribution == "inconclusive"
    assert 0.0 < directness.mde < 0.15


def test_failures_that_named_no_criterion_are_left_over_rather_than_hidden():
    """A judge may fail an example without citing anything. That gap has to show."""
    baseline = [Outcome("pass")] * 40 + [Outcome("fail", "Groundedness")] * 5
    variant = [Outcome("fail", None)] * 8 + [Outcome("pass")] * 32 + [Outcome("pass")] * 5
    result = by_criterion(baseline, variant)

    assert result.uncited_failures == 8
    assert result.family == 1  # only Groundedness was ever cited
    assert result.unattributed < 0  # the eight uncited failures are a real loss
    overall = compare([o.verdict for o in baseline], [o.verdict for o in variant])
    assert result.attributed + result.unattributed == pytest.approx(overall.difference)


def test_a_criterion_recorded_beside_a_pass_does_not_become_a_failure():
    """Attribution is of failures. A criterion on a passing example is not one."""
    baseline = [Outcome("pass", "Groundedness")] * 20 + [Outcome("fail", "Correctness")] * 5
    variant = [Outcome("pass")] * 20 + [Outcome("fail", "Correctness")] * 5
    result = by_criterion(baseline, variant)
    assert [c.criterion for c in result.criteria] == ["Correctness"]
    assert named(result, "Correctness").discordance.discordant == 0


def test_the_breakdown_never_speaks_in_the_overall_verdict_s_words():
    """Five attributions are not five comparisons, so they do not get its vocabulary."""
    baseline, variant = suite((70, None, None), (20, None, "Groundedness"))
    result = by_criterion(baseline, variant)
    payload = result.to_dict()

    words = {c["attribution"] for c in payload["criteria"]}
    assert words <= {"moved_worse", "moved_better", "inconclusive"}
    assert not words & {"regression", "improvement"}
    assert "not independent findings" in payload["note"]
    assert payload["method"] == "holm"


def test_attribution_is_deterministic():
    """The contract calls compare deterministic; the breakdown is part of compare."""
    baseline, variant = suite(
        (50, None, None), (12, None, "Groundedness"), (7, "Correctness", None)
    )
    first = by_criterion(baseline, variant).to_dict()
    second = by_criterion(baseline, variant).to_dict()
    assert first == second


def test_a_breakdown_of_mismatched_or_empty_arms_is_refused():
    with pytest.raises(ValueError, match="same length"):
        by_criterion([Outcome("pass")], [Outcome("pass"), Outcome("pass")])
    with pytest.raises(ValueError, match="no goldens"):
        by_criterion([], [])
    with pytest.raises(ValueError, match="must be 'pass' or 'fail'"):
        by_criterion([Outcome("maybe")], [Outcome("pass")])  # type: ignore[arg-type]


def test_the_family_wise_rate_survives_the_whole_pipeline_not_just_holm():
    """Holm on paper is one thing; Holm wired to a discrete exact test is another.

    Two arms drawn from the same law over four criteria, so every attribution
    this produces is a false one and the rate of them is the family-wise error
    rate. The uncorrected reading — raw p under alpha with an interval clear of
    zero — is recorded from the same runs, and it does fire, which is what stops
    this from being a simulation that proves nothing because nothing happened.
    """
    rng = np.random.default_rng(7)
    criteria = ("Correctness", "Groundedness", "Directness", "Citation")
    n, trials = 80, 60
    corrected = uncorrected = 0

    for _ in range(trials):
        baseline, variant = [], []
        for _ in range(n):
            for arm in (baseline, variant):
                # Same law for both arms: any movement between them is chance.
                if rng.random() < 0.25:
                    arm.append(Outcome("fail", criteria[rng.integers(len(criteria))]))
                else:
                    arm.append(Outcome("pass"))
        result = by_criterion(baseline, variant)
        if any(c.attribution != "inconclusive" for c in result.criteria):
            corrected += 1
        if any(
            c.p_value < 0.05 and (c.interval.hi < 0 or c.interval.lo > 0) for c in result.criteria
        ):
            uncorrected += 1

    assert corrected <= 0.05 * trials
    assert uncorrected > 0, "the uncorrected rule never fired; the simulation proved nothing"
    assert corrected < uncorrected

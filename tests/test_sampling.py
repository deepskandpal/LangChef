"""M1 — which examples are worth a person's attention."""

from langchef.core.sampling import plan, summarise


def scores(n_fail, n_pass, confidence=0.9):
    rows = [
        {"example_id": f"f-{i:03}", "verdict": "fail", "confidence": confidence}
        for i in range(n_fail)
    ]
    rows += [
        {"example_id": f"p-{i:03}", "verdict": "pass", "confidence": confidence}
        for i in range(n_pass)
    ]
    return rows


def test_the_plan_is_balanced_across_the_judges_verdicts():
    """The whole point: a 2% fail rate must not spend the budget on passes."""
    chosen = plan(scores(n_fail=4, n_pass=196), budget=40)
    strata = {s.stratum for s in chosen}
    assert strata == {"fail", "pass"}
    assert sum(1 for s in chosen if s.stratum == "fail") == 4  # every one available
    assert len(chosen) == 40


def test_an_even_split_when_both_strata_are_plentiful():
    chosen = plan(scores(100, 100), budget=40)
    assert sum(1 for s in chosen if s.stratum == "fail") == 20
    assert sum(1 for s in chosen if s.stratum == "pass") == 20


def test_uncertain_judgements_are_preferred():
    rows = [
        {"example_id": "sure", "verdict": "pass", "confidence": 0.99},
        {"example_id": "unsure", "verdict": "pass", "confidence": 0.10},
        {"example_id": "middling", "verdict": "pass", "confidence": 0.55},
    ]
    assert [s.example_id for s in plan(rows, budget=2)] == ["unsure", "middling"]


def test_the_plan_is_deterministic_across_machines():
    rows = scores(50, 50)
    assert [s.example_id for s in plan(rows, 30, seed=7)] == [
        s.example_id for s in plan(rows, 30, seed=7)
    ]
    assert [s.example_id for s in plan(rows, 30, seed=7)] != [
        s.example_id for s in plan(rows, 30, seed=8)
    ]


def test_weights_record_the_unequal_inclusion_probability():
    """Stratified sampling biases raw rates; the weight is what makes that fixable."""
    chosen = plan(scores(10, 190), budget=20)
    fail_weight = next(s.weight for s in chosen if s.stratum == "fail")
    pass_weight = next(s.weight for s in chosen if s.stratum == "pass")
    assert fail_weight < pass_weight  # fails are oversampled, so each counts for less


def test_budget_larger_than_the_pool_takes_everything_once():
    chosen = plan(scores(3, 4), budget=100)
    assert len(chosen) == 7
    assert len({s.example_id for s in chosen}) == 7


def test_no_budget_and_no_rows_are_empty_not_errors():
    assert plan(scores(5, 5), budget=0) == []
    assert plan([], budget=10) == []
    assert plan([{"example_id": "x", "verdict": "skipped"}], budget=5) == []


def test_summary_reports_the_design_it_used():
    rows = scores(10, 90)
    chosen = plan(rows, budget=20)
    payload = summarise(chosen, rows)
    assert payload["selected"] == 20
    assert payload["available"] == 100
    assert "stratified" in payload["design"]


def test_the_reported_weight_is_the_weight_the_rows_carry():
    """The two must agree, or the figure a person reads is not the plan's.

    `summarise` used to compute `len(rows) / count` -- the whole suite over one
    stratum's count -- which is a suite-level numerator over a stratum-level
    denominator.
    """
    rows = scores(n_fail=15, n_pass=75)
    chosen = plan(rows, budget=40)
    reported = summarise(chosen, rows)["weights"]

    carried = {s.stratum: round(s.weight, 3) for s in chosen}
    assert reported == carried


def test_the_reported_weight_is_stratum_size_over_the_number_taken():
    """The issue's worked example, in full.

    A 90-example suite with 15 judge-fails and a budget of 40 takes all 15
    fails and 25 passes, so the weights are 15/15 and 75/25. The old formula
    reported 6.0 and 3.6.
    """
    rows = scores(n_fail=15, n_pass=75)
    chosen = plan(rows, budget=40)
    payload = summarise(chosen, rows)

    assert payload["by_stratum"] == {"fail": 15, "pass": 25}
    assert payload["weights"] == {"fail": 1.0, "pass": 3.0}


def test_a_weight_is_never_the_suite_size_over_a_stratum_count():
    """Guard against the old formula being reintroduced as an optimisation."""
    rows = scores(n_fail=15, n_pass=75)
    chosen = plan(rows, budget=40)
    payload = summarise(chosen, rows)

    wrong = {name: round(len(rows) / count, 3) for name, count in payload["by_stratum"].items()}
    assert payload["weights"] != wrong


def test_a_fully_sampled_stratum_weighs_one():
    """Taking every example in a stratum means no correction is owed for it."""
    rows = scores(n_fail=5, n_pass=95)
    chosen = plan(rows, budget=40)
    payload = summarise(chosen, rows)

    assert payload["by_stratum"]["fail"] == 5
    assert payload["weights"]["fail"] == 1.0


def test_weights_reconstruct_the_stratum_sizes():
    """The property that makes a weight usable: count x weight is the stratum."""
    rows = scores(n_fail=15, n_pass=75)
    payload = summarise(plan(rows, budget=40), rows)

    for name, count in payload["by_stratum"].items():
        assert count * payload["weights"][name] == len([r for r in rows if r["verdict"] == name])


def test_a_stratum_that_contributed_nothing_is_absent_from_the_weights():
    rows = scores(n_fail=0, n_pass=50)
    payload = summarise(plan(rows, budget=10), rows)

    assert "fail" not in payload["weights"]
    assert payload["weights"] == {"pass": 5.0}


def test_summarising_an_empty_plan_reports_no_weights():
    rows = scores(n_fail=5, n_pass=5)
    payload = summarise([], rows)

    assert payload["weights"] == {}
    assert payload["selected"] == 0
    assert payload["available"] == 10

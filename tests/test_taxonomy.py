"""M1 — the disagreement taxonomy."""

from langchef.core.taxonomy import Judgement, by_criterion, by_slice, concentrations, summarise


def rows(spec):
    """spec: (n, human, judge, criterion, slices)."""
    out = []
    counter = 0
    for count, human, judge, criterion, slices in spec:
        for _ in range(count):
            counter += 1
            out.append(Judgement(f"ex-{counter:03}", human, judge, criterion, dict(slices)))
    return out


def test_kind_names_disagreement_from_the_judges_point_of_view():
    assert Judgement("a", "fail", "pass").kind == "miss"
    assert Judgement("a", "pass", "fail").kind == "false_alarm"
    assert Judgement("a", "pass", "pass").kind is None
    assert Judgement("a", "fail", "fail").kind is None


def test_buckets_group_and_rank_by_criterion():
    data = rows(
        [
            (5, "pass", "fail", "Groundedness", {}),
            (2, "pass", "fail", "Correctness", {}),
            (9, "pass", "pass", "Correctness", {}),
        ]
    )
    buckets = {b.label: b for b in by_criterion(data)}
    assert buckets["Groundedness"].disagreements == 5
    assert buckets["Correctness"].disagreements == 2
    assert buckets["Correctness"].total == 11
    assert by_criterion(data)[0].label == "Groundedness"  # worst first


def test_examples_without_a_criterion_are_not_counted_against_the_rubric():
    data = rows([(4, "pass", "fail", None, {}), (1, "pass", "fail", "Correctness", {})])
    assert [b.label for b in by_criterion(data)] == ["Correctness"]
    assert by_criterion(data)[0].total == 1


def test_slices_rank_worst_rate_first():
    data = rows(
        [
            (8, "pass", "fail", None, {"topic": "returns"}),
            (2, "pass", "pass", None, {"topic": "returns"}),
            (1, "pass", "fail", None, {"topic": "billing"}),
            (9, "pass", "pass", None, {"topic": "billing"}),
        ]
    )
    ranked = by_slice(data, "topic")
    assert ranked[0].label == "returns"
    assert ranked[0].rate == 0.8
    assert ranked[1].rate == 0.1


def test_a_real_concentration_is_reported_as_separated():
    data = rows(
        [
            (28, "pass", "fail", None, {"topic": "returns"}),
            (2, "pass", "pass", None, {"topic": "returns"}),
            (2, "pass", "fail", None, {"topic": "billing"}),
            (98, "pass", "pass", None, {"topic": "billing"}),
        ]
    )
    found = concentrations(data)
    assert found[0].dimension == "topic"
    assert found[0].worst_value == "returns"
    assert found[0].separated
    assert found[0].lift > 3


def test_a_lift_that_rests_on_two_examples_is_not_reported_as_separated():
    """The honest filter: a wide interval straddling the base rate has shown nothing.

    2 of 8 is a 67% lift over a 15% base rate and looks alarming in a table. Its
    interval runs from 7% to 59%, so it is also entirely consistent with the
    slice being no worse than average, and the memo must not send anyone to
    investigate it.
    """
    data = rows(
        [
            (2, "pass", "fail", None, {"topic": "returns"}),
            (6, "pass", "pass", None, {"topic": "returns"}),
            (13, "pass", "fail", None, {"topic": "billing"}),
            (79, "pass", "pass", None, {"topic": "billing"}),
        ]
    )
    worst = next(c for c in concentrations(data, min_bucket=5) if c.worst_value == "returns")
    assert worst.lift > 1.5
    assert worst.worst.interval.lo < worst.base_rate < worst.worst.interval.hi
    assert not worst.separated


def test_tiny_buckets_are_excluded_entirely():
    data = rows(
        [
            (2, "pass", "fail", None, {"topic": "rare"}),
            (50, "pass", "pass", None, {"topic": "common"}),
        ]
    )
    assert [c.worst_value for c in concentrations(data, min_bucket=5)] == ["common"]


def test_summary_is_plain_data_with_capped_example_lists():
    data = rows([(40, "fail", "pass", "Correctness", {"topic": "returns"})])
    payload = summarise(data)
    assert payload["n"] == 40
    assert payload["disagreements"] == 40
    assert payload["kinds"] == {"false_alarm": 0, "miss": 40}
    assert len(payload["examples"]["miss"]) == 20  # capped, so a memo stays readable
    assert payload["by_slice"]["topic"][0]["label"] == "returns"


def test_no_rows_is_empty_not_an_error():
    assert concentrations([]) == []
    assert summarise([])["n"] == 0

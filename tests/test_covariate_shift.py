"""The covariate-shift knob: a classifier, and an aggregate that misattributes.

Build order §8's fourth knob. It could not be written until the `classification`
task class existed (#20), because the failure it plants has no analogue in a
judged pass rate.

The other five knobs degrade an answer. This one degrades a **classifier** under
covariate shift: the input distribution moves, `P(y|x)` does not, the model is
untouched, and accuracy falls only where the shift landed. What makes it worth a
test is the second half. The aggregate does not go quiet, which is what was
originally expected of it -- it goes *wrong*, reporting a small decline spread
over everything when the truth is a large one in a single topic.

Every number asserted here was measured first and written down afterwards, which
is the rule the first `top-k` knob taught this repository.
"""

import pytest
from dogfood.classifier import (
    CLASSIFIER_BASELINE,
    CLASSIFIER_VARIANTS,
    MISATTRIBUTION_RATIO,
    PLANTED_ACCURACY,
    PLANTED_CLASSIFIER_EFFECT,
    PLANTED_SHIFT_SLICE,
    accuracy,
    accuracy_by,
    rows,
)

from langchef.core.compare import compare

SHIFTED = "covariate-shift"


def verdicts(scored: list[dict]) -> list[str]:
    """The classification outcome, as the paired comparison consumes it.

    `predicted == ideal` is binary the moment it is read, so nothing is reduced
    on the way in (DECISIONS.md #12).
    """
    return ["pass" if row["predicted"] == row["ideal"] else "fail" for row in scored]


@pytest.fixture(scope="module")
def arms() -> tuple[list[dict], list[dict]]:
    return rows(CLASSIFIER_BASELINE), rows(CLASSIFIER_VARIANTS[SHIFTED])


def test_the_planted_accuracies_are_what_the_knob_claims(arms):
    """The knob moved ground truth. Assert that before trusting anything else."""
    baseline, shifted = arms

    assert accuracy(baseline) == pytest.approx(PLANTED_ACCURACY["baseline"], abs=1e-4)
    assert accuracy(shifted) == pytest.approx(PLANTED_ACCURACY[SHIFTED], abs=1e-4)


def test_the_labels_never_move_because_this_is_covariate_shift(arms):
    """Covariate shift, not concept drift or label shift.

    If the ideal labels moved, the arms would not be comparable and the whole
    knob would be measuring a different dataset rather than a degraded model.
    """
    baseline, shifted = arms

    assert [r["example_id"] for r in baseline] == [r["example_id"] for r in shifted]
    assert [r["ideal"] for r in baseline] == [r["ideal"] for r in shifted]


def test_only_the_shifted_cell_has_different_input_text(arms):
    """The shift is a cell -- one topic, one phrasing -- and touches nothing else."""
    baseline, shifted = arms
    moved = [
        b["example_id"] for b, v in zip(baseline, shifted, strict=True) if b["input"] != v["input"]
    ]

    assert moved, "the knob changed no input at all, which is the failure top-k had"

    by_id = {row["example_id"]: row for row in baseline}
    touched = {(by_id[eid]["slices"]["topic"], by_id[eid]["slices"]["phrasing"]) for eid in moved}
    assert touched == {("security", "terse")}
    assert len(moved) == 6, "six of ninety rows, which is what keeps the aggregate small"
    # `frequency` is not part of the cut. One of the six is a head query, so a
    # test that asserted all six were tail would be asserting a coincidence.
    assert {by_id[eid]["slices"]["frequency"] for eid in moved} == {"head", "tail"}


def test_the_slice_carries_the_finding_and_the_others_are_untouched(arms):
    """Four topics move by exactly zero. That is the planted truth."""
    baseline, shifted = arms

    for slice_name, expected in PLANTED_SHIFT_SLICE.items():
        before = accuracy_by(baseline, slice_name)
        after = accuracy_by(shifted, slice_name)
        for key, effect in expected.items():
            assert after[key] - before[key] == pytest.approx(effect, abs=1e-3), (
                f"{slice_name}={key} moved {after[key] - before[key]:+.4f}, planted {effect:+.4f}"
            )


def test_slice_attribution_finds_the_shift_the_aggregate_describes_wrongly(arms):
    """The knob's reason for existing.

    Both numbers below are correct arithmetic. Only one of them sends a person to
    the right place. The aggregate says quality fell about seven points, which
    reads as a model that got slightly worse everywhere; the truth is that one
    topic lost a third of its accuracy and four lost nothing.
    """
    baseline, shifted = arms
    aggregate = compare(verdicts(baseline), verdicts(shifted))

    security_before = [r for r in baseline if r["slices"]["topic"] == "security"]
    security_after = [r for r in shifted if r["slices"]["topic"] == "security"]
    security = compare(verdicts(security_before), verdicts(security_after))

    assert aggregate.verdict == "regression"
    assert aggregate.difference == pytest.approx(PLANTED_CLASSIFIER_EFFECT, abs=1e-3)
    assert security.verdict == "regression"
    assert security.difference == pytest.approx(-0.3333, abs=1e-3)
    # The slice effect is five times the aggregate. A tool that reports only the
    # aggregate has not missed the regression; it has misdescribed it.
    assert security.difference / aggregate.difference == pytest.approx(
        MISATTRIBUTION_RATIO, abs=0.2
    )


def test_the_unshifted_slices_report_nothing_rather_than_noise(arms):
    """Four topics are untouched, so each must come back inconclusive, not clean.

    An unshifted slice with a nonzero verdict would mean the knob leaked, and
    every attribution built on it would be reading its own noise.
    """
    baseline, shifted = arms

    for topic in ("account", "billing", "returns", "shipping"):
        before = [r for r in baseline if r["slices"]["topic"] == topic]
        after = [r for r in shifted if r["slices"]["topic"] == topic]
        result = compare(verdicts(before), verdicts(after))

        assert result.discordance.discordant == 0
        assert result.verdict == "inconclusive"


def test_the_aggregate_detection_limit_is_wider_than_the_effect_it_reported(arms):
    """A tension worth stating rather than hiding.

    The pre-hoc detection limit on 90 goldens is about 11 points, and the
    observed aggregate effect is 6.7. The verdict is still a regression, because
    every discordant pair moves the same way and exact McNemar reads that
    directly. The MDE is what a typical draw of this size could resolve; it is
    not a floor under what this particular draw did resolve.
    """
    baseline, shifted = arms
    aggregate = compare(verdicts(baseline), verdicts(shifted))

    assert aggregate.mde > abs(aggregate.difference)
    assert aggregate.discordance.fixed == 0
    assert aggregate.p_value < 0.05


def test_the_knob_is_deterministic(arms):
    """Same corpus, same config, same rows -- on any machine, in any order."""
    first = rows(CLASSIFIER_VARIANTS[SHIFTED])
    second = rows(CLASSIFIER_VARIANTS[SHIFTED])

    assert first == second
    assert first == arms[1]

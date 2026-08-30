"""The self-test: does LangChef detect regressions we planted ourselves?

Every other test here checks that a function computes what it claims. This one
checks the product's actual claim — that a team running this would find out
their system got worse — by breaking a known-good app in six known ways and
asking the harness what it sees.

Three of the six are worth reading, because for each of them the *required*
answer is something other than "regression detected":

``truncated-context``
    A real regression, smaller than 90 goldens can resolve. The required outcome
    is an inconclusive verdict with an honest account of what the run could have
    seen. A clean bill of health here would be worse than useless.

``embedding-swap``
    Head queries are untouched and the tail loses a third. "Quality fell" is
    true, useless, and a miss; the finding is a slice.

``temperature-0.9``
    Ground truth is identical in every trial, so a comparison of means finds
    nothing and is right to. The damage is the scatter between repeated calls,
    and only a spread sees it.
"""

import statistics

import pytest
from dogfood.app import (
    BASELINE,
    PLANTED_EFFECT,
    PLANTED_RECALL_EFFECT,
    PLANTED_SLICE_EFFECT,
    PLANTED_VARIANCE_RATIO,
    TRIALS,
    VARIANTS,
    recall,
)
from dogfood.app import run as run_app
from dogfood.corpus import questions

from langchef.core.agreement import agreement
from langchef.core.compare import Outcome, by_criterion, compare
from langchef.judge.cache import Cache
from langchef.judge.providers import ContainmentProvider
from langchef.judge.rubric import parse
from langchef.judge.runner import run as judge_run
from langchef.workspace.scaffold import RUBRIC

RUBRIC_OBJ = parse(RUBRIC, "answer-quality")


@pytest.fixture(scope="module")
def asked():
    return questions()


def _judge(rows, tmp_path, name):
    from langchef.judge.example import Example

    examples = [
        Example.from_dict({k: v for k, v in row.items() if not k.startswith("_")}) for row in rows
    ]
    result = judge_run(
        examples,
        RUBRIC_OBJ,
        ContainmentProvider(),
        cheap_model="containment/v2",
        cache=Cache(tmp_path / f"{name}.jsonl"),
    )
    return result.verdicts()


def _truth(rows):
    return [row["_truth"] for row in rows]


def test_the_planted_effects_are_what_the_dogfood_claims(asked):
    """The harness is only meaningful if the plant is what the label says."""
    baseline = _truth(run_app(BASELINE, asked))
    base_rate = baseline.count("pass") / len(baseline)
    for name, config in VARIANTS.items():
        rows = _truth(run_app(config, asked))
        observed = rows.count("pass") / len(rows) - base_rate
        assert observed == pytest.approx(PLANTED_EFFECT[name], abs=0.02), name


def test_the_large_regressions_are_detected(asked, tmp_path):
    baseline = _judge(run_app(BASELINE, asked), tmp_path, "base")
    for name in ("stale-index", "eager-hedging", "embedding-swap"):
        variant = _judge(run_app(VARIANTS[name], asked), tmp_path, name)
        result = compare(baseline, variant)
        assert result.regression, f"{name} went undetected"
        # The measured effect should land on the planted one.
        assert result.difference == pytest.approx(PLANTED_EFFECT[name], abs=0.03), name
        assert result.interval.lo <= PLANTED_EFFECT[name] <= result.interval.hi, name


def test_the_small_regression_is_reported_as_inconclusive_not_as_clean(asked, tmp_path):
    baseline = _judge(run_app(BASELINE, asked), tmp_path, "base")
    variant = _judge(run_app(VARIANTS["truncated-context"], asked), tmp_path, "trunc")
    result = compare(baseline, variant)

    assert result.inconclusive
    assert not result.regression and not result.improvement
    # And it says so honestly: the effect it could not see is larger than the
    # one that is actually there.
    assert result.mde > abs(PLANTED_EFFECT["truncated-context"])


def test_the_chunking_knob_breaks_retrieval_before_it_breaks_the_answer(asked, tmp_path):
    """Doubling the chunk is a retrieval regression that the pass rate under-reports.

    Both halves are planted and both are checked, because the gap between them
    is the finding. A chunk holding two facts sits half way between them, so the
    gold document reaches the prompt 14 points less often — unmistakable, and
    measured at the retrieval layer. Only about half of that survives into a
    wrong answer, which puts the end-to-end effect under what 90 goldens can
    resolve. The honest report is "retrieval is broken, and this suite is the
    wrong instrument to prove it".
    """
    variant = VARIANTS["chunk-size-doubled"]
    measured = recall(variant, asked) - recall(BASELINE, asked)
    assert measured == pytest.approx(PLANTED_RECALL_EFFECT["chunk-size-doubled"], abs=0.02)

    base_rows = run_app(BASELINE, asked)
    rows = run_app(variant, asked)
    base_chars = statistics.mean(len(row["answer"]) for row in base_rows)
    chars = statistics.mean(len(row["answer"]) for row in rows)
    assert chars > 1.8 * base_chars, "a doubled chunk should roughly double the answer"

    result = compare(_judge(base_rows, tmp_path, "base"), _judge(rows, tmp_path, "chunk"))
    assert result.inconclusive
    assert result.mde > abs(PLANTED_EFFECT["chunk-size-doubled"])
    assert result.interval.lo <= PLANTED_EFFECT["chunk-size-doubled"] <= result.interval.hi


def test_the_embedding_swap_is_a_tail_finding_not_a_quality_finding(asked, tmp_path):
    """Slice attribution has to find what the aggregate only hints at.

    The planted truth is that the swapped model matches the old one exactly on
    head queries and loses a third of the tail. A harness that reports "quality
    fell by 12 points" has said something true and sent someone to look in the
    wrong place.
    """
    name = "embedding-swap"
    base_rows = run_app(BASELINE, asked)
    rows = run_app(VARIANTS[name], asked)
    baseline = _judge(base_rows, tmp_path, "base")
    variant = _judge(rows, tmp_path, name)

    assert compare(baseline, variant).regression

    planted = PLANTED_SLICE_EFFECT[name]
    for label, expected in planted.items():
        keep = [i for i, q in enumerate(asked) if q.frequency == label]
        assert keep, label
        sliced = compare([baseline[i] for i in keep], [variant[i] for i in keep])
        assert sliced.difference == pytest.approx(expected, abs=0.06), label

    head = [i for i, q in enumerate(asked) if q.frequency == "head"]
    head_result = compare([baseline[i] for i in head], [variant[i] for i in head])
    assert head_result.discordance.discordant == 0, "head queries must be untouched"
    assert head_result.inconclusive

    tail = [i for i, q in enumerate(asked) if q.frequency == "tail"]
    tail_result = compare([baseline[i] for i in tail], [variant[i] for i in tail])
    assert tail_result.regression, "the tail is where the swap shows"
    assert tail_result.difference < head_result.difference - 0.2


@pytest.fixture(scope="module")
def repeated(asked, tmp_path_factory):
    """The same question set asked ``TRIALS`` times under both temperatures.

    Judged once and shared: the consistency knob is the only one that needs more
    than a single call, and it needs two statistics off the same calls.
    """
    tmp = tmp_path_factory.mktemp("trials")
    return {
        tag: [_judge(run_app(config, asked, trial=t), tmp, f"{tag}{t}") for t in range(TRIALS)]
        for tag, config in (("baseline", BASELINE), ("hot", VARIANTS["temperature-0.9"]))
    }


def test_a_means_only_comparison_finds_nothing_in_the_temperature_knob(asked, repeated):
    """The case that justifies reporting a spread at all.

    Ground truth is identical in every trial — the wording moves, the content
    does not — so every comparison of means here is *correctly* inconclusive,
    including the pooled one over every trial at once. Nothing is wrong with the
    statistic. It is measuring the wrong thing, and that is the finding.
    """
    base_truth = _truth(run_app(BASELINE, asked))
    for trial in range(TRIALS):
        rows = run_app(VARIANTS["temperature-0.9"], asked, trial=trial)
        assert _truth(rows) == base_truth, f"trial {trial} moved ground truth"

    for trial in range(TRIALS):
        result = compare(repeated["baseline"][trial], repeated["hot"][trial])
        assert result.inconclusive, f"trial {trial} claimed a mean shift"

    pooled = compare(
        [v for trial in repeated["baseline"] for v in trial],
        [v for trial in repeated["hot"] for v in trial],
    )
    assert pooled.discordance.n == TRIALS * len(asked)
    assert pooled.inconclusive, "24x the goldens and there is still no shift in the mean"
    assert abs(pooled.difference) < 0.01
    # And it is not for want of power: the pooled run could have seen a shift an
    # order of magnitude smaller than the smallest knob in the rig.
    assert pooled.mde < 0.02


def test_the_temperature_knob_moves_the_spread_the_mean_hid(asked, repeated):
    """The other half: the measured pass rate will not sit still.

    Same rewording rate at both temperatures, so the same mean. What changes is
    whether a call keeps the wording it used last time — 37 times likelier to
    depart at 0.9 than at 0.2 — and the pass rate scatters accordingly.
    """
    rates = {
        tag: [trial.count("pass") / len(asked) for trial in trials]
        for tag, trials in repeated.items()
    }
    assert statistics.mean(rates["hot"]) == pytest.approx(
        statistics.mean(rates["baseline"]), abs=0.01
    )

    ratio = statistics.pvariance(rates["hot"]) / statistics.pvariance(rates["baseline"])
    # The estimate is an F ratio off TRIALS draws and is wide; the planted value
    # is quoted in the README and the assertion is the floor it must clear.
    assert ratio > PLANTED_VARIANCE_RATIO["temperature-0.9"] / 4, ratio
    assert len(set(rates["baseline"])) < len(set(rates["hot"]))


def test_the_judge_has_the_blind_spot_the_dogfood_planted(asked, tmp_path):
    """Calibration against ground truth should find the paraphrase weakness.

    A quarter of the baseline's answers are correct but reworded. A person reads
    through a paraphrase; a token-overlap judge does not. The agreement figures
    are the product's way of telling you that before you trust the suite.
    """
    rows = run_app(BASELINE, asked)
    judge = _judge(rows, tmp_path, "base")
    truth = _truth(rows)
    report = agreement(truth, judge)

    assert report.confusion.n == len(rows)
    assert 0.0 < report.kappa < 1.0  # neither useless nor suspiciously perfect
    assert report.confusion.fp > 0, "the paraphrase blind spot should cause false alarms"

    paraphrased = {row["example_id"] for row in rows if row["_provenance"].get("paraphrased")}
    false_alarms = {
        row["example_id"]
        for row, t, j in zip(rows, truth, judge, strict=True)
        if t == "pass" and j == "fail"
    }
    assert false_alarms & paraphrased, "false alarms should land on the reworded answers"


def test_the_run_is_reproducible(asked, tmp_path):
    """Same inputs, same verdicts — on any machine, with no model involved."""
    first = _judge(run_app(BASELINE, asked), tmp_path, "a")
    second = _judge(run_app(BASELINE, asked), tmp_path, "b")
    assert first == second


def _outcomes(rows, tmp_path, name):
    from langchef.judge.example import Example

    examples = [
        Example.from_dict({k: v for k, v in row.items() if not k.startswith("_")}) for row in rows
    ]
    result = judge_run(
        examples,
        RUBRIC_OBJ,
        ContainmentProvider(),
        cheap_model="containment/v2",
        cache=Cache(tmp_path / f"{name}.jsonl"),
    )
    return [Outcome(j.verdict, j.criterion) for j in result.judgements]


def test_the_attribution_names_the_component_that_actually_broke(asked, tmp_path):
    """The point of the whole feature: which half of the system moved.

    ``eager-hedging`` turns the generator cautious — it declines answers it used
    to give — and touches retrieval not at all. A harness that reported "quality
    fell 11 points" would send someone to look at the retriever. The attribution
    has to put the loss on Directness and decline to put any of it on
    Correctness, whose flips here are too few to survive the correction.
    """
    baseline = _outcomes(run_app(BASELINE, asked), tmp_path, "base")
    variant = _outcomes(run_app(VARIANTS["eager-hedging"], asked), tmp_path, "hedge")
    result = by_criterion(baseline, variant)

    directness = next(c for c in result.criteria if c.criterion == "Directness")
    assert directness.attribution == "moved_worse"
    assert directness.difference < -0.10

    correctness = next(c for c in result.criteria if c.criterion == "Correctness")
    assert correctness.attribution == "inconclusive"

    # And the parts add up to the whole, so nothing was quietly dropped.
    overall = compare([o.verdict for o in baseline], [o.verdict for o in variant])
    assert result.attributed == pytest.approx(overall.difference)
    assert result.uncited_failures == 0


def test_a_stale_index_lands_mostly_on_the_criterion_it_should(asked, tmp_path):
    """Documents missing from the index cost correctness first, hedging second.

    The judge here is token containment, so an answer drawn from the wrong
    document is still grounded in what was retrieved — the loss shows up as
    Correctness, not Groundedness. That is a property of this judge rather than
    of the arithmetic, and the attribution is only ever as good as the judge
    doing the citing.
    """
    baseline = _outcomes(run_app(BASELINE, asked), tmp_path, "base")
    variant = _outcomes(run_app(VARIANTS["stale-index"], asked), tmp_path, "stale")
    result = by_criterion(baseline, variant)

    worst = result.criteria[0]
    assert worst.criterion == "Correctness"
    assert worst.attribution == "moved_worse"
    assert result.attributed == pytest.approx(PLANTED_EFFECT["stale-index"], abs=0.03)


def test_the_unresolvable_arm_attributes_nothing_and_says_what_it_missed(asked, tmp_path):
    """The third arm again, one level down — and the same rule has to hold.

    ``truncated-context`` plants a regression smaller than 90 goldens can
    resolve. Slicing the comparison five ways is exactly where a tool starts
    finding something anyway, so the required outcome is that every criterion
    comes back inconclusive *with its own limit*, and that no limit is small
    enough to have caught the planted effect.
    """
    baseline = _outcomes(run_app(BASELINE, asked), tmp_path, "base")
    variant = _outcomes(run_app(VARIANTS["truncated-context"], asked), tmp_path, "trunc")
    result = by_criterion(baseline, variant)

    assert result.criteria, "the breakdown should still name what it looked at"
    for c in result.criteria:
        assert c.attribution == "inconclusive", c.criterion
        assert c.mde > abs(PLANTED_EFFECT["truncated-context"]), c.criterion


def test_a_trial_is_reproducible_not_merely_repeatable(asked):
    """Temperature must not smuggle in randomness that survives a restart.

    A trial is a pure function of its number, so trial 7 is the same call on
    every machine and in every process. Without that the spread the consistency
    knob plants would be indistinguishable from an unseeded generator, and the
    rig could not tell a detected regression from a different random seed.
    """
    hot = VARIANTS["temperature-0.9"]
    for trial in (0, 7, TRIALS - 1):
        first = [row["answer"] for row in run_app(hot, asked, trial=trial)]
        second = [row["answer"] for row in run_app(hot, asked, trial=trial)]
        assert first == second, trial
    assert [row["answer"] for row in run_app(hot, asked, trial=0)] != [
        row["answer"] for row in run_app(hot, asked, trial=1)
    ], "two calls at temperature 0.9 should not be word-for-word identical"

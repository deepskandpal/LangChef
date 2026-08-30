"""The self-test: does LangChef detect regressions we planted ourselves?

Every other test here checks that a function computes what it claims. This one
checks the product's actual claim — that a team running this would find out
their system got worse — by breaking a known-good app in three known ways and
asking the harness what it sees.

The third arm is the one worth reading. Its regression is real and smaller than
90 goldens can resolve, and the required outcome is *not* a detection: it is an
inconclusive verdict with an honest account of what the run could have seen. A
harness that reported a clean bill of health there would be worse than useless.
"""

import pytest
from dogfood.app import BASELINE, PLANTED_EFFECT, VARIANTS
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


def test_the_two_large_regressions_are_detected(asked, tmp_path):
    baseline = _judge(run_app(BASELINE, asked), tmp_path, "base")
    for name in ("stale-index", "eager-hedging"):
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

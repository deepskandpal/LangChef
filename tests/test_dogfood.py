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
from langchef.core.compare import compare
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

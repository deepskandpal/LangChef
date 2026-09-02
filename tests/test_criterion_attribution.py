"""The sentence the product leads with, made reproducible.

#28 and `docs/index.html` both promise the same thing: not "quality dropped four
points" but **"groundedness dropped nine points while correctness held"**. The
attribution machinery to produce that shipped with `by_criterion`. What did not
ship was an arm that exercises it.

Every knob in `dogfood/app.py` before this one answers out of a retrieved
document, so whatever else is wrong with the answer it is still grounded in what
the retriever handed over. Measured across the whole rig, `Groundedness` was
never once cited, and the only criteria the attribution ever named were
`Correctness` and `Directness`. The flagship claim was arithmetic nobody had run
end to end.

`hallucinated-detail` is the missing arm. Every sixth answer gains an invented
clause whose content words appear in no document and in no expected answer,
which is exactly what the groundedness check looks for, and the requested fact
stays where it was, which is what makes Correctness hold.
"""

import pathlib
import tempfile

import pytest
from dogfood.app import BASELINE, PLANTED_CRITERION_EFFECT, PLANTED_EFFECT, VARIANTS
from dogfood.app import run as run_app
from dogfood.corpus import questions

from langchef.core.compare import Outcome, by_criterion, compare
from langchef.judge.cache import Cache
from langchef.judge.example import Example
from langchef.judge.providers import ContainmentProvider
from langchef.judge.rubric import parse
from langchef.judge.runner import run as judge_run
from langchef.workspace.scaffold import RUBRIC

KNOB = "hallucinated-detail"
RUBRIC_OBJ = parse(RUBRIC, "answer-quality")


def _outcomes(rows, cache_dir, name):
    examples = [
        Example.from_dict({k: v for k, v in row.items() if not k.startswith("_")}) for row in rows
    ]
    scored = judge_run(
        examples,
        RUBRIC_OBJ,
        ContainmentProvider(),
        cheap_model="containment/v2",
        cache=Cache(cache_dir / f"{name}.jsonl"),
    ).by_id()
    return [Outcome(scored[e.example_id].verdict, scored[e.example_id].criterion) for e in examples]


@pytest.fixture(scope="module")
def arms():
    asked = questions()
    cache = pathlib.Path(tempfile.mkdtemp())
    baseline = _outcomes(run_app(BASELINE, asked), cache, "baseline")
    variant = _outcomes(run_app(VARIANTS[KNOB], asked), cache, KNOB)
    return baseline, variant


def test_the_knob_moves_ground_truth_before_anything_else_is_believed(arms):
    """The lesson the first top-k knob taught: verify the effect, then test it."""
    asked = questions()
    baseline = run_app(BASELINE, asked)
    variant = run_app(VARIANTS[KNOB], asked)

    def rate(rows):
        return sum(1 for r in rows if r["_truth"] == "pass") / len(rows)

    assert rate(variant) - rate(baseline) == pytest.approx(PLANTED_EFFECT[KNOB], abs=0.01)


def test_groundedness_falls_and_correctness_holds(arms):
    """The claim, verbatim, as the product makes it.

    The overall verdict is a regression either way. The finding is *which part*
    of the system broke, and it is the difference between a person going to look
    at the retriever and a person going to look at the generator.
    """
    baseline, variant = arms
    attribution = by_criterion(baseline, variant)
    named = {c.criterion: c for c in attribution.criteria}

    grounded = named["Groundedness"]
    assert grounded.attribution == "moved_worse"
    assert grounded.difference == pytest.approx(
        PLANTED_CRITERION_EFFECT[KNOB]["Groundedness"], abs=0.01
    )
    assert grounded.interval.hi < 0, "the whole interval has to agree with the direction"

    correctness = named["Correctness"]
    assert correctness.attribution == "inconclusive"
    assert correctness.difference == pytest.approx(
        PLANTED_CRITERION_EFFECT[KNOB]["Correctness"], abs=1e-9
    )


def test_this_is_the_only_arm_that_ever_cites_groundedness(arms):
    """A guard on the gap this knob closes, not a property of the arithmetic.

    If a future knob starts moving Groundedness too, this test should be updated
    rather than deleted -- but it should be *noticed*, because the reason the
    flagship claim went untested for so long is that nothing said out loud which
    criteria the rig could reach.
    """
    asked = questions()
    cache = pathlib.Path(tempfile.mkdtemp())
    baseline = _outcomes(run_app(BASELINE, asked), cache, "base")

    cited = set()
    for name in ("stale-index", "eager-hedging", "truncated-context"):
        variant = _outcomes(run_app(VARIANTS[name], asked), cache, name)
        cited |= {c.criterion for c in by_criterion(baseline, variant).criteria}

    assert "Groundedness" not in cited
    assert cited == {"Correctness", "Directness"}


def test_the_parts_add_up_to_the_whole(arms):
    """Nothing is quietly dropped between the overall number and the breakdown."""
    baseline, variant = arms
    overall = compare([o.verdict for o in baseline], [o.verdict for o in variant])
    attribution = by_criterion(baseline, variant)

    assert attribution.attributed == pytest.approx(overall.difference)
    assert attribution.unattributed == pytest.approx(0.0, abs=1e-9)
    assert attribution.uncited_failures == 0


def test_the_per_criterion_limit_is_computed_not_borrowed(arms):
    """The trap #28 names: an overall limit pasted beside a per-criterion finding.

    Each criterion's limit is computed at the corrected level, which is the
    strictest rung of the Holm ladder and the one a lone signal faces. It is not
    automatically wider than the overall limit -- a criterion with few flips is
    estimated more precisely, not less -- so the assertion is that it differs and
    was computed, not that it is bigger.
    """
    baseline, variant = arms
    overall = compare([o.verdict for o in baseline], [o.verdict for o in variant])
    attribution = by_criterion(baseline, variant)

    assert attribution.mde_level > attribution.level
    assert attribution.family == 2
    assert all(c.mde != overall.mde for c in attribution.criteria)


def test_the_arm_is_deterministic(arms):
    """Same config, same answers, same attribution."""
    asked = questions()
    assert run_app(VARIANTS[KNOB], asked) == run_app(VARIANTS[KNOB], asked)

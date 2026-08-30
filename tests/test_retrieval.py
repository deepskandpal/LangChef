"""Retrieval metrics, and the paired comparison over the scores they produce.

Every metric here is checked against an independent implementation, because a
statistic without one does not ship. The edge cases get more attention than the
happy path: every nDCG implementation differs on ties and truncation, and
silence about which choice was made is how two teams' numbers stop being
comparable while both look correct.
"""

from __future__ import annotations

import numpy as np
import pytest

from langchef.core.compare import compare_continuous
from langchef.core.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank

# --- known answers against scikit-learn --------------------------------------


def test_ndcg_matches_sklearn():
    """The one most likely to differ between implementations, so pinned hardest."""
    sklearn_metrics = pytest.importorskip("sklearn.metrics")

    ranking = ["d1", "d2", "d3", "d4", "d5"]
    relevant = {"d2", "d4"}

    true_relevance = np.array([[1.0 if d in relevant else 0.0 for d in ranking]])
    # sklearn scores a ranking by giving the first position the highest score.
    scores = np.array([[float(len(ranking) - i) for i in range(len(ranking))]])
    expected = sklearn_metrics.ndcg_score(true_relevance, scores)

    assert ndcg_at_k(ranking, relevant) == pytest.approx(expected)


def test_recall_at_k_is_the_definition():
    """Checked against the set arithmetic written out longhand."""
    ranking = ["d1", "d2", "d3", "d4"]
    relevant = {"d2", "d4", "d9"}

    longhand = len({"d2", "d4"}) / len(relevant)

    assert recall_at_k(ranking, relevant) == pytest.approx(longhand)
    assert recall_at_k(ranking, relevant, k=2) == pytest.approx(1 / 3)
    assert recall_at_k(ranking, relevant, k=1) == pytest.approx(0.0)


def test_reciprocal_rank_is_one_over_the_first_hit():
    ranking = ["d1", "d2", "d3"]

    assert reciprocal_rank(ranking, {"d1"}) == pytest.approx(1.0)
    assert reciprocal_rank(ranking, {"d2"}) == pytest.approx(0.5)
    assert reciprocal_rank(ranking, {"d3"}) == pytest.approx(1 / 3)
    # Answerable and missed is a real zero, unlike an unanswerable query.
    assert reciprocal_rank(ranking, {"d9"}) == 0.0


# --- the edges, which is where implementations diverge -----------------------


def test_a_short_list_is_evaluated_not_padded():
    """Asking for recall@10 from six documents scores the six.

    Padding would score the retriever for a truncation the caller chose, and
    erroring would treat an ordinary situation as a fault.
    """
    ranking = ["d1", "d2"]
    relevant = {"d1", "d2"}

    assert recall_at_k(ranking, relevant, k=10) == pytest.approx(1.0)


def test_a_duplicate_is_counted_once():
    """Counting it twice would reward a retriever for a bug."""
    assert recall_at_k(["d1", "d1", "d1"], {"d1", "d2"}) == pytest.approx(0.5)
    assert ndcg_at_k(["d1", "d1"], {"d1"}) == pytest.approx(1.0)


def test_an_unanswerable_query_is_nan_not_zero():
    """A query with no relevant documents cannot be scored.

    Returning 0.0 would drag a mean down with a number meaning 'we could not
    ask', which is the same error as counting an unmeasurable example as a
    failure. nan propagates and forces the caller to decide.
    """
    for metric in (recall_at_k, reciprocal_rank, ndcg_at_k):
        value = metric(["d1"], set())
        assert value != value, metric.__name__


def test_a_perfect_ranking_scores_one_and_a_reversed_one_scores_less():
    """Order has to matter, or nDCG is measuring nothing that recall does not."""
    relevant = {"d1", "d2"}

    assert ndcg_at_k(["d1", "d2", "d3"], relevant) == pytest.approx(1.0)
    assert ndcg_at_k(["d3", "d1", "d2"], relevant) < 1.0
    # Recall cannot tell those apart, which is the argument for reporting both.
    assert recall_at_k(["d1", "d2", "d3"], relevant) == recall_at_k(["d3", "d1", "d2"], relevant)


# --- the paired continuous comparison ----------------------------------------


def test_the_comparison_is_paired_and_it_matters():
    """Query difficulty varies far more than the gap between two retrievers.

    Read unpaired, a consistent small improvement drowns in that variation. Read
    paired, it is obvious. This is the same argument as the binary case and the
    reason retrieval was not allowed to reduce to a threshold.
    """
    rng = np.random.default_rng(21)
    difficulty = rng.uniform(0.2, 0.9, size=60)
    baseline = difficulty
    variant = np.clip(difficulty + 0.04, 0, 1)  # same queries, uniformly better

    result = compare_continuous(baseline, variant)

    assert result.verdict == "improvement"
    assert result.difference == pytest.approx(0.04, abs=0.005)
    # The differences barely vary, so the interval is tight despite the arms
    # themselves ranging over most of [0, 1].
    assert result.sd_difference < 0.01
    assert result.interval.lo > 0


def test_identical_arms_are_inconclusive_rather_than_a_crash():
    """Every difference zero is what a no-op change looks like.

    Wilcoxon cannot rank an all-zero vector and raises; reporting p=1 says the
    same thing without a traceback reaching a user.
    """
    scores = [0.4, 0.7, 0.9, 0.2]

    result = compare_continuous(scores, scores)

    assert result.verdict == "inconclusive"
    assert result.p_value == 1.0
    assert result.difference == pytest.approx(0.0)


def test_unscorable_pairs_are_dropped_and_counted():
    """A nan from an unanswerable query must not poison the mean."""
    baseline = [0.5, float("nan"), 0.8]
    variant = [0.6, 0.9, 0.9]

    result = compare_continuous(baseline, variant)

    assert result.n == 2
    assert result.difference == pytest.approx(0.1)


def test_a_regression_is_named_only_when_the_whole_interval_agrees():
    """The same rule as the binary path: no direction from a straddling interval."""
    rng = np.random.default_rng(7)
    baseline = rng.uniform(0.3, 0.8, size=50)
    variant = baseline - 0.15  # unambiguous

    result = compare_continuous(baseline, variant)

    assert result.verdict == "regression"
    assert result.interval.hi < 0


def test_the_detection_limit_is_reported_and_is_the_continuous_one():
    """An inconclusive continuous run must say what it could not have seen.

    And it must use #68's continuous arithmetic, not the discordant-rate one,
    which is undefined here.
    """
    from langchef.core.design import minimum_detectable_effect_continuous

    rng = np.random.default_rng(3)
    baseline = rng.uniform(0.2, 0.9, size=40)
    variant = baseline + rng.normal(0, 0.2, size=40)

    result = compare_continuous(baseline, variant)

    assert result.mde == pytest.approx(
        minimum_detectable_effect_continuous(result.n, result.sd_difference)
    )
    assert result.mde > 0

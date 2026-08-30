"""The classification pack's own reporting, loaded the way the product loads it.

Nothing here imports ``packs.classification.metrics`` directly. Every test goes
through ``load_class`` and ``reporting``, because the thing worth testing is not
the arithmetic alone — it is that a pack can carry code, that the loader finds it
through the manifest, and that ``core/`` is not involved at any point.

The arithmetic is checked twice, as the working agreement requires of any
statistic: once against a confusion matrix small enough to work out by hand, and
once against scikit-learn over a larger set. scikit-learn is a test dependency
precisely so the product and its check never come from the same code.
"""

import random

import pytest
from sklearn.metrics import precision_recall_fscore_support

from langchef.core.compare import compare
from langchef.core.design import DesignError, propose
from langchef.packs import entry_point, load_class, reporting

LABELS = ("billing", "technical", "account", "spam")


@pytest.fixture(scope="module")
def report():
    """The pack's reporting function, resolved exactly as the CLI would."""
    return reporting(*load_class("classification"))


@pytest.fixture(scope="module")
def outcomes():
    """The per-example outcome, also loaded out of the pack rather than imported."""
    manifest, _ = load_class("classification")
    return entry_point(manifest, "metrics.py:outcomes")


def rows(pairs):
    """``(ideal, predicted)`` pairs as the rows a workspace would hold."""
    return [
        {"example_id": f"e{index}", "input": f"row {index}", "ideal": ideal, "predicted": predicted}
        for index, (ideal, predicted) in enumerate(pairs)
    ]


# Eight examples, three labels, worked out by hand in the docstring below.
BY_HAND = rows(
    [
        ("a", "a"),
        ("a", "a"),
        ("a", "b"),
        ("b", "b"),
        ("b", "b"),
        ("b", "b"),
        ("b", "a"),
        ("c", "a"),
    ]
)


def test_precision_and_recall_against_a_confusion_matrix_worked_by_hand(report):
    """Label `a`: 4 predicted, 2 right → precision 1/2. Support 3, 2 found → recall 2/3.

    Label `b`: 4 predicted, 3 right → precision 3/4. Support 4, 3 found → recall 3/4.
    Label `c`: never predicted → precision undefined. Support 1, none found → recall 0.
    Five of eight right → accuracy 0.625.
    """
    result = report(BY_HAND)

    assert result["n"] == 8
    assert result["accuracy"] == pytest.approx(0.625)
    assert result["labels"] == ["a", "b", "c"]

    assert result["per_class"]["a"] == {
        "support": 3,
        "predicted": 4,
        "true_positive": 2,
        "precision": pytest.approx(0.5),
        "recall": pytest.approx(2 / 3),
    }
    assert result["per_class"]["b"]["precision"] == pytest.approx(0.75)
    assert result["per_class"]["b"]["recall"] == pytest.approx(0.75)
    assert result["macro"]["precision"] == pytest.approx((0.5 + 0.75 + 0.0) / 3)
    assert result["macro"]["recall"] == pytest.approx((2 / 3 + 0.75 + 0.0) / 3)


def test_a_label_that_was_never_predicted_has_no_precision_rather_than_zero(report):
    """Zero would read as "always wrong". Absent is the honest answer."""
    result = report(BY_HAND)
    assert result["per_class"]["c"]["precision"] is None
    assert result["per_class"]["c"]["recall"] == pytest.approx(0.0)
    assert result["undefined"] == ["c"]


def test_precision_and_recall_match_scikit_learn(report):
    """Known-answer, against an independent implementation. AGENTS.md, testing table."""
    rng = random.Random(11)
    pairs = []
    for _ in range(240):
        ideal = rng.choice(LABELS)
        # Wrong about a fifth of the time, and never predicts `spam` at all —
        # the failure a per-class number catches and accuracy hides.
        if rng.random() < 0.2:
            predicted = rng.choice([label for label in LABELS[:3] if label != ideal])
        else:
            predicted = ideal if ideal != "spam" else "technical"
        pairs.append((ideal, predicted))

    result = report(rows(pairs))
    labels = result["labels"]
    expected_precision, expected_recall, _, expected_support = precision_recall_fscore_support(
        [ideal for ideal, _ in pairs],
        [predicted for _, predicted in pairs],
        labels=labels,
        zero_division=0,
    )

    for index, label in enumerate(labels):
        counts = result["per_class"][label]
        assert counts["support"] == expected_support[index]
        # scikit-learn reports the undefined cases as zero; the pack reports them
        # as absent and folds them in as zero only when averaging.
        assert (counts["precision"] or 0.0) == pytest.approx(expected_precision[index])
        assert (counts["recall"] or 0.0) == pytest.approx(expected_recall[index])

    macro_precision, macro_recall, _, _ = precision_recall_fscore_support(
        [ideal for ideal, _ in pairs],
        [predicted for _, predicted in pairs],
        labels=labels,
        average="macro",
        zero_division=0,
    )
    assert result["macro"]["precision"] == pytest.approx(macro_precision)
    assert result["macro"]["recall"] == pytest.approx(macro_recall)
    assert "spam" in result["undefined"]


def test_the_outcome_is_predicted_equals_ideal_and_nothing_is_reduced(outcomes, report):
    """DECISIONS.md #12 — the comparison a team wants, not a reduction of the label."""
    scored = outcomes(BY_HAND)
    assert [row["correct"] for row in scored] == [True, True, False, True, True, True, False, False]
    assert sum(row["correct"] for row in scored) / len(scored) == report(BY_HAND)["accuracy"]
    # The label survives alongside the outcome: nothing is thrown away on the
    # way in, which is what makes the per-class report possible at all.
    assert scored[7]["ideal"] == "c" and scored[7]["predicted"] == "a"


def test_the_core_compares_these_outcomes_without_knowing_what_they_are(outcomes):
    """The split, end to end: the pack produces outcomes, the core does statistics.

    ``compare`` is handed pass/fail and has no idea a label was ever involved —
    which is exactly why classification needed no new statistics, only a pack.
    """
    ideal = [LABELS[index % 4] for index in range(120)]
    baseline_pred = list(ideal)
    variant_pred = list(ideal)
    for index in range(0, 30):  # the variant breaks 30 of them
        variant_pred[index] = "spam" if ideal[index] != "spam" else "billing"

    def verdicts(predictions):
        scored = outcomes(rows(zip(ideal, predictions, strict=True)))
        return ["pass" if row["correct"] else "fail" for row in scored]

    result = compare(verdicts(baseline_pred), verdicts(variant_pred))
    assert result.discordance.broke == 30
    assert result.discordance.fixed == 0
    assert result.regression is True


def test_the_class_reaches_the_core_as_a_shape_and_never_as_a_name():
    """The other half of #68: the caller resolves class to shape, core sizes shapes.

    ``core/design.py`` says in its own comment that it must not know "retrieval"
    exists and that the caller does the resolving. This is the caller: the class
    is looked up in a pack manifest, its declared ``outcome_shape`` is handed to
    ``propose``, and the word `classification` never crosses the boundary.
    """
    _, task_class = load_class("classification")
    designs = propose(
        suite="intents",
        intent="does the new router beat the old one?",
        n_available=400,
        baseline_arm="baseline",
        variant_arm="variant",
        target_effect=0.05,
        outcome=task_class.outcome_shape,
    )
    assert designs and all(design.outcome == "binary" for design in designs)

    # And a shape it cannot size is refused rather than guessed, which is why the
    # manifest holds a pack to the same two words.
    with pytest.raises(DesignError, match="no sizing rule"):
        propose(
            suite="intents",
            intent="x",
            n_available=400,
            baseline_arm="baseline",
            variant_arm="variant",
            outcome="ordinal",
        )


def test_a_row_missing_its_target_is_refused_by_name(report):
    with pytest.raises(ValueError, match="e1"):
        report([{"example_id": "e0", "ideal": "a", "predicted": "a"}, {"example_id": "e1"}])


def test_a_duplicated_example_id_is_refused_rather_than_counted_twice(report):
    duplicated = rows([("a", "a"), ("a", "b")])
    duplicated[1]["example_id"] = duplicated[0]["example_id"]
    with pytest.raises(ValueError, match="twice"):
        report(duplicated)


def test_an_empty_set_is_refused_rather_than_scored_zero(report):
    with pytest.raises(ValueError, match="no rows"):
        report([])


def test_the_pack_ships_its_own_reporting_and_the_manifest_names_it(report):
    """The code is in the pack, and the manifest is how anything finds it."""
    manifest, task_class = load_class("classification")
    assert task_class.reporting == "metrics.py:report"
    assert (manifest.path / "metrics.py").is_file()
    assert report.__name__ == "report"
    assert report.__module__.startswith("langchef_pack.classification")

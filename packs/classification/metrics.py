"""Reporting for the `classification` task class.

This file is **pack code**. It ships inside the pack, is resolved through
``[task_classes.classification].reporting`` in ``pack.toml``, and is loaded by
``langchef.packs.loader.reporting``. Nothing under ``src/langchef/core/`` may
import it, or know that it exists, or know the word `classification` at all —
``tests/test_boundaries.py`` enforces that, and DECISIONS.md #5 explains what it
costs when it stops being true.

Two things live here, and the split is the whole design.

**The outcome** is ``predicted == ideal``. It is binary the moment it is read, so
the deterministic core needs nothing new to compare two arms of a classification
experiment: the same paired McNemar path that serves a judged pass/fail serves
this exactly, and it is exact rather than approximate (DECISIONS.md #12). No
reduction happens on ingestion because there is nothing to reduce.

**Per-class precision and recall** are what a classification team will actually
read, and they are not core statistics. Accuracy answers "how often is it
right"; precision and recall answer "which label is it wrong about, and in which
direction" — an intent router at 91% accuracy that never once predicts
`escalate` is a broken router, and only the per-class numbers say so. That is
domain reporting about a multi-class label, which is pack expertise, so it lives
here. Deliberately stdlib-only: a pack has to run wherever it is installed.

Undefined is reported as ``None``, never as zero. Precision is undefined when a
label was never predicted, recall when it never appeared as a target. Zero would
read as "it predicted this label and got it wrong every time", which is a
different and much more alarming fact than "it never predicted this label".
The macro averages do fold undefined in as zero, because a label the system
never reaches is a failure to average over rather than one to skip — the two
conventions disagree, so both numbers are reported rather than one of them
chosen silently.
"""

from collections.abc import Iterable, Mapping

#: The class this file reports on, as declared in ``pack.toml``.
TASK_CLASS = "classification"

#: The two fields the outcome is computed from.
PREDICTED = "predicted"
IDEAL = "ideal"


class RowError(ValueError):
    """A row does not carry what this task class requires."""


def _label(row: Mapping, key: str, where: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise RowError(
            f"{where}: no {key!r} — a classification row needs both a prediction and a target"
        )
    return str(value)


def outcomes(rows: Iterable[Mapping]) -> list[dict]:
    """One binary outcome per example: was the predicted label the ideal one?

    The list the core's paired comparison consumes. Order is preserved, and the
    example id travels with it, because the pairing between two arms is by id
    and a positional pairing silently compares different questions.
    """
    scored: list[dict] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        where = f"row {index}"
        example_id = row.get("example_id")
        if example_id is None or str(example_id) == "":
            raise RowError(f"{where}: no 'example_id' — nothing to pair the other arm against")
        example_id = str(example_id)
        if example_id in seen:
            raise RowError(
                f"{where}: example_id {example_id!r} appears twice; it would count twice"
            )
        seen.add(example_id)
        where = f"example {example_id!r}"
        predicted = _label(row, PREDICTED, where)
        ideal = _label(row, IDEAL, where)
        scored.append(
            {
                "example_id": example_id,
                "predicted": predicted,
                "ideal": ideal,
                "correct": predicted == ideal,
            }
        )
    return scored


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def report(rows: Iterable[Mapping]) -> dict:
    """Accuracy, and precision and recall per class, over one arm's rows.

    Counting, not inference: no interval and no p-value, because a single arm
    has nothing to be compared against. Two arms go through the core's paired
    comparison over ``outcomes``, which is where the statistics live.
    """
    scored = outcomes(rows)
    if not scored:
        raise RowError(
            "no rows: precision and recall over an empty set are not zero, they are absent"
        )

    labels = sorted({row["ideal"] for row in scored} | {row["predicted"] for row in scored})
    per_class: dict[str, dict] = {}
    for label in labels:
        true_positive = sum(1 for r in scored if r["predicted"] == label and r["ideal"] == label)
        predicted_count = sum(1 for r in scored if r["predicted"] == label)
        support = sum(1 for r in scored if r["ideal"] == label)
        per_class[label] = {
            "support": support,
            "predicted": predicted_count,
            "true_positive": true_positive,
            "precision": _ratio(true_positive, predicted_count),
            "recall": _ratio(true_positive, support),
        }

    correct = sum(1 for r in scored if r["correct"])
    macro_precision = sum(c["precision"] or 0.0 for c in per_class.values()) / len(labels)
    macro_recall = sum(c["recall"] or 0.0 for c in per_class.values()) / len(labels)

    return {
        "task_class": TASK_CLASS,
        "n": len(scored),
        "correct": correct,
        "accuracy": correct / len(scored),
        "labels": labels,
        "per_class": per_class,
        # Undefined folded in as zero, matching the usual convention. The
        # per-class None values above are the honest version.
        "macro": {"precision": macro_precision, "recall": macro_recall},
        "undefined": sorted(
            label
            for label, counts in per_class.items()
            if counts["precision"] is None or counts["recall"] is None
        ),
    }

"""Choosing which examples a person should label.

Human labels are the scarce input in this whole product — they cost attention,
not money — so which examples get labelled matters more than how many.

Two things drive the choice. **Balance**, because a suite where the judge flags
2% of examples will, under simple random sampling, spend an entire labelling
budget on cases the judge already called clean, and the resulting TPR rests on
one or two examples. **Uncertainty**, because a judgement the judge was unsure
about separates two rubrics, and one it was certain about usually does not.

Sampling is stratified by the judge's own verdict, so allocation differs between
strata and a ``weight`` is recorded per row. Rates computed on the labelled set
are sample rates, not population rates, and anything quoting them has to say so.

**That weight is not a valid inclusion weight, and post-stratification will not
make it one.** Selection *within* a stratum is deterministic: the lowest
confidence rows are taken, so a row's inclusion probability is 0 or 1 given its
confidence rank rather than ``n/N``. Post-stratification corrects allocation
*between* strata and cannot recover population rates when selection inside one
tracks the quantity being estimated, which confidence does almost by definition.

A seeded coverage check on #30 put a nominal 95% interval at 43% actual coverage
for TPR and 100% for TNR, the opposite failure and equally useless. Whether one
label budget can buy estimation and diagnosis at once is open at #60; it probably
cannot, in which case this splits into a random part for measuring and an
uncertainty-selected part for diagnosing.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Selection:
    """One example chosen for labelling, and why."""

    example_id: str
    stratum: str
    confidence: float
    weight: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "stratum": self.stratum,
            "confidence": self.confidence,
            "weight": self.weight,
            "reason": self.reason,
        }


def _tiebreak(example_id: str, seed: int) -> str:
    """A stable pseudo-random order. Same inputs, same plan, on any machine."""
    return hashlib.sha256(f"{seed}\x00{example_id}".encode()).hexdigest()


def plan(rows: Sequence[dict], budget: int, seed: int = 0) -> list[Selection]:
    """Pick up to ``budget`` examples to label, balanced across the judge's verdicts.

    ``rows`` are score records: ``example_id``, ``verdict`` and ``confidence``.
    The result is deterministic — the same run and the same budget produce the
    same list, so a plan can be regenerated without re-labelling anything.
    """
    if budget <= 0:
        return []

    strata: dict[str, list[dict]] = {"fail": [], "pass": []}
    for row in rows:
        verdict = row.get("verdict")
        if verdict in strata:
            strata[verdict].append(row)

    available = {name: len(group) for name, group in strata.items()}
    if not sum(available.values()):
        return []

    # Even split, then give the remainder to whichever stratum can still fill it.
    target = {name: min(budget // 2, count) for name, count in available.items()}
    for name in ("fail", "pass"):
        spare = budget - sum(target.values())
        if spare > 0:
            target[name] = min(available[name], target[name] + spare)

    selections: list[Selection] = []
    for name, group in strata.items():
        take = target[name]
        if not take:
            continue
        ordered = sorted(
            group,
            key=lambda row: (float(row.get("confidence", 1.0)), _tiebreak(row["example_id"], seed)),
        )
        weight = available[name] / take
        for position, row in enumerate(ordered[:take]):
            confidence = float(row.get("confidence", 1.0))
            selections.append(
                Selection(
                    example_id=str(row["example_id"]),
                    stratum=name,
                    confidence=confidence,
                    weight=weight,
                    reason=(
                        "judge was unsure"
                        if position < take // 2 and confidence < 0.75
                        else f"stratum coverage ({name})"
                    ),
                )
            )
    return sorted(selections, key=lambda s: (s.confidence, s.example_id))


def summarise(selections: Sequence[Selection], rows: Sequence[dict]) -> dict:
    """What the plan did, in the terms the person labelling will ask about."""
    strata: dict[str, int] = {}
    weights: dict[str, float] = {}
    for selection in selections:
        strata[selection.stratum] = strata.get(selection.stratum, 0) + 1
        # Read the weight `plan` recorded rather than deriving a second one.
        #
        # This used to compute `len(rows) / count` -- the whole suite over one
        # stratum's count -- which put a suite-level numerator over a
        # stratum-level denominator and is not a quantity that means anything.
        # On a 90-example suite with 15 judge-fails and a budget of 40 it
        # reported 6.0 and 3.6 where the rows carried 1.0 and 3.0.
        #
        # Nothing consumed the reported figure, so no published number was
        # wrong; the cost was that one module offered two candidate weights
        # with nothing to say which was intended. Taking it from the selection
        # leaves exactly one definition, in `plan`.
        weights[selection.stratum] = round(selection.weight, 3)
    return {
        "selected": len(selections),
        "available": len(rows),
        "by_stratum": strata,
        "design": "stratified by judge verdict; inclusion probability differs between strata",
        "weights": weights,
    }

"""Choosing which examples a person should label.

Human labels are the scarce input in this whole product — they cost attention,
not money — so which examples get labelled matters more than how many.

Two things drive the choice. **Balance**, because a suite where the judge flags
2% of examples will, under simple random sampling, spend an entire labelling
budget on cases the judge already called clean, and the resulting TPR rests on
one or two examples. **Uncertainty**, because a judgement the judge was unsure
about separates two rubrics, and one it was certain about usually does not.

Sampling is stratified by the judge's own verdict, so the inclusion probability
differs between strata and is recorded per row. Rates computed on the labelled
set are therefore sample rates, not population rates, and anything that quotes
them has to say so — ``weight`` is here so that a later post-stratified
estimator has what it needs.
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
    for selection in selections:
        strata[selection.stratum] = strata.get(selection.stratum, 0) + 1
    return {
        "selected": len(selections),
        "available": len(rows),
        "by_stratum": strata,
        "design": "stratified by judge verdict; inclusion probability differs between strata",
        "weights": {name: round(len(rows) / count, 3) for name, count in strata.items() if count},
    }

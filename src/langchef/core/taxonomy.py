"""Where a judge disagrees, not just how often.

An agreement number tells you a judge is 78% accurate. It does not tell you the
misses are all on long answers, which is the only form of the finding anyone can
act on. This module turns paired verdicts plus whatever slice metadata came with
the examples into a ranked account of *where* the disagreement lives.

Two shapes of disagreement, named from the judge's point of view:

``false_alarm``
    Judge said fail, human said pass. Costs trust — every one of these is a
    human going to look at something that turned out to be fine.
``miss``
    Judge said pass, human said fail. Costs the whole suite — these are the
    regressions that ship.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from langchef.core.agreement import DEFAULT_LEVEL, Interval, Verdict, wilson

Kind = Literal["false_alarm", "miss"]


@dataclass(frozen=True)
class Judgement:
    """One example, as both raters saw it."""

    example_id: str
    human: Verdict
    judge: Verdict
    criterion: str | None = None
    slices: dict[str, str] = field(default_factory=dict)

    @property
    def kind(self) -> Kind | None:
        if self.human == self.judge:
            return None
        return "miss" if self.human == "fail" else "false_alarm"


@dataclass(frozen=True)
class Bucket:
    """A group of disagreements sharing a criterion or a slice value."""

    label: str
    disagreements: int
    total: int
    kinds: dict[str, int]
    interval: Interval

    @property
    def rate(self) -> float:
        return self.disagreements / self.total if self.total else float("nan")


@dataclass(frozen=True)
class Concentration:
    """One slice dimension where disagreement is not spread evenly.

    ``lift`` is the worst value's rate over the base rate. It is reported with
    the worst value's interval so a reader can see whether "twice as bad on long
    answers" rests on four examples or four hundred.
    """

    dimension: str
    worst_value: str
    worst: Bucket
    base_rate: float
    lift: float
    separated: bool


def _bucket(label: str, rows: Sequence[Judgement], level: float) -> Bucket:
    kinds: dict[str, int] = defaultdict(int)
    for row in rows:
        kind = row.kind
        if kind:
            kinds[kind] += 1
    disagreements = sum(kinds.values())
    return Bucket(
        label=label,
        disagreements=disagreements,
        total=len(rows),
        kinds=dict(kinds),
        interval=wilson(disagreements, len(rows), level),
    )


def by_criterion(rows: Sequence[Judgement], level: float = DEFAULT_LEVEL) -> list[Bucket]:
    """Disagreements grouped by the rubric criterion the judge cited.

    Only judgements that cited a criterion are counted, so the totals here are
    not the suite totals — a judge that returns no criterion tells us nothing
    about which part of the rubric is at fault.
    """
    grouped: dict[str, list[Judgement]] = defaultdict(list)
    for row in rows:
        if row.criterion:
            grouped[row.criterion].append(row)
    buckets = [_bucket(name, group, level) for name, group in grouped.items()]
    return sorted(buckets, key=lambda b: (-b.disagreements, b.label))


def by_slice(
    rows: Sequence[Judgement], dimension: str, level: float = DEFAULT_LEVEL
) -> list[Bucket]:
    """Disagreements grouped by one slice dimension, worst first."""
    grouped: dict[str, list[Judgement]] = defaultdict(list)
    for row in rows:
        value = row.slices.get(dimension)
        if value is not None:
            grouped[value].append(row)
    buckets = [_bucket(value, group, level) for value, group in grouped.items()]
    return sorted(buckets, key=lambda b: (-b.rate, b.label))


def dimensions(rows: Sequence[Judgement]) -> list[str]:
    """Every slice dimension present, in a stable order."""
    return sorted({key for row in rows for key in row.slices})


def concentrations(
    rows: Sequence[Judgement],
    level: float = DEFAULT_LEVEL,
    min_bucket: int = 5,
) -> list[Concentration]:
    """Slice dimensions where disagreement clusters, worst lift first.

    ``separated`` is the honest filter: it is true only when the worst value's
    interval sits entirely above the base rate. A slice with a scary-looking
    lift and an interval straddling the base rate has not shown us anything, and
    the memo says so rather than sending someone to investigate noise.
    """
    total = len(rows)
    if not total:
        return []
    base_rate = sum(1 for row in rows if row.kind) / total

    found: list[Concentration] = []
    for dimension in dimensions(rows):
        buckets = [b for b in by_slice(rows, dimension, level) if b.total >= min_bucket]
        if not buckets:
            continue
        worst = buckets[0]
        found.append(
            Concentration(
                dimension=dimension,
                worst_value=worst.label,
                worst=worst,
                base_rate=base_rate,
                lift=worst.rate / base_rate if base_rate else float("inf"),
                separated=bool(worst.interval.lo > base_rate),
            )
        )
    return sorted(found, key=lambda c: (-c.separated, -c.lift))


def summarise(
    rows: Sequence[Judgement],
    level: float = DEFAULT_LEVEL,
    min_bucket: int = 5,
) -> dict:
    """The taxonomy as plain data, ready for ``emit``."""
    disagreements = [row for row in rows if row.kind]
    counts: dict[str, int] = defaultdict(int)
    for row in disagreements:
        counts[str(row.kind)] += 1

    def bucket_dict(b: Bucket) -> dict:
        return {
            "label": b.label,
            "disagreements": b.disagreements,
            "total": b.total,
            "rate": b.rate,
            "kinds": b.kinds,
            "interval": {"lo": b.interval.lo, "hi": b.interval.hi, "level": b.interval.level},
        }

    return {
        "n": len(rows),
        "disagreements": len(disagreements),
        "kinds": {"false_alarm": counts["false_alarm"], "miss": counts["miss"]},
        "by_criterion": [bucket_dict(b) for b in by_criterion(rows, level)],
        "by_slice": {
            dimension: [bucket_dict(b) for b in by_slice(rows, dimension, level)]
            for dimension in dimensions(rows)
        },
        "concentrations": [
            {
                "dimension": c.dimension,
                "worst_value": c.worst_value,
                "rate": c.worst.rate,
                "base_rate": c.base_rate,
                "lift": c.lift,
                "separated": c.separated,
                "n": c.worst.total,
                "interval": {
                    "lo": c.worst.interval.lo,
                    "hi": c.worst.interval.hi,
                    "level": c.worst.interval.level,
                },
            }
            for c in concentrations(rows, level, min_bucket)
        ],
        "examples": {
            kind: [row.example_id for row in disagreements if row.kind == kind][:20]
            for kind in ("miss", "false_alarm")
        },
    }

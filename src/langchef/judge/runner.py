"""Running a judge over a batch: cache, two tiers, and the pin.

Two-tier judging is here from the start rather than added as an optimisation
(DECISIONS.md #9). A cheap model scores everything; a strong model re-scores
only the cases the cheap one was unsure about. The model is part of the cache
key, so retrofitting the tiering later would invalidate every cached judgement
in every workspace — an hour now against a migration afterwards.

The pin is the other half. A run records the rubric hash, the provider and both
models; comparing two runs whose pins disagree is not a comparison, it is two
different measurements, and the CLI exits 5 rather than pretending otherwise.
"""

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from langchef.judge.cache import Cache, judgement_key
from langchef.judge.example import Example
from langchef.judge.providers import Judgement, Provider
from langchef.judge.rubric import Rubric

ESCALATE_BELOW = 0.6


class PinMismatch(RuntimeError):
    """Two runs were produced under different measuring instruments."""

    def __init__(self, moved: dict[str, tuple[str, str]]) -> None:
        parts = ", ".join(f"{field}: {was!r} -> {now!r}" for field, (was, now) in moved.items())
        super().__init__(f"pin moved — {parts}")
        self.moved = moved


@dataclass(frozen=True)
class Pin:
    """What produced a set of verdicts. Recorded on every run."""

    rubric: str
    provider: str
    cheap_model: str
    strong_model: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Pin":
        return cls(
            rubric=raw["rubric"],
            provider=raw["provider"],
            cheap_model=raw["cheap_model"],
            strong_model=raw.get("strong_model"),
        )


def check_pin(expected: Pin, actual: Pin) -> None:
    """Raise unless two runs were measured the same way."""
    moved = {
        field: (str(getattr(expected, field)), str(getattr(actual, field)))
        for field in ("rubric", "provider", "cheap_model", "strong_model")
        if getattr(expected, field) != getattr(actual, field)
    }
    if moved:
        raise PinMismatch(moved)


@dataclass(frozen=True)
class RunResult:
    """One ``judge run``: the verdicts, how they were produced, what it cost."""

    judgements: tuple[Judgement, ...]
    pin: Pin
    stats: dict

    def verdicts(self) -> list[str]:
        return [j.verdict for j in self.judgements]

    def by_id(self) -> dict[str, Judgement]:
        return {j.example_id: j for j in self.judgements}


def run(
    examples: Sequence[Example],
    rubric: Rubric,
    provider: Provider,
    cheap_model: str,
    cache: Cache,
    strong_model: str | None = None,
    escalate_below: float = ESCALATE_BELOW,
) -> RunResult:
    """Score every example, escalating only the unsure ones."""
    judgements: list[Judgement] = []
    escalated: list[str] = []
    called = 0

    for example in examples:
        key = judgement_key(example, rubric, cheap_model, "cheap")
        judgement = cache.get(key)
        if judgement is None:
            judgement = provider.judge(example, rubric, cheap_model)
            called += 1
            cache.put(key, judgement, "cheap", rubric.ref)

        if strong_model and judgement.confidence < escalate_below:
            strong_key = judgement_key(example, rubric, strong_model, "strong")
            stronger = cache.get(strong_key)
            if stronger is None:
                stronger = provider.judge(example, rubric, strong_model)
                called += 1
                cache.put(strong_key, stronger, "strong", rubric.ref)
            escalated.append(example.example_id)
            judgement = stronger

        judgements.append(judgement)

    fails = sum(1 for j in judgements if j.verdict == "fail")
    return RunResult(
        judgements=tuple(judgements),
        pin=Pin(
            rubric=rubric.ref,
            provider=provider.name,
            cheap_model=cheap_model,
            strong_model=strong_model,
        ),
        stats={
            "n": len(judgements),
            "provider_calls": called,
            "cache_hits": cache.hits,
            "cache_misses": cache.misses,
            "escalated": len(escalated),
            "escalated_ids": escalated[:20],
            "fail": fails,
            "pass": len(judgements) - fails,
            "fail_rate": fails / len(judgements) if judgements else float("nan"),
        },
    )


def pass_rate(judgements: Iterable[Judgement]) -> float:
    """Share of examples the judge let through."""
    verdicts = [j.verdict for j in judgements]
    return verdicts.count("pass") / len(verdicts) if verdicts else float("nan")

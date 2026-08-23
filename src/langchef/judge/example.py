"""The unit a judge scores.

Deliberately flat and provider-independent: a judge backend receives one of
these and returns a verdict, and nothing about the retrieval stack, the app, or
the connector leaks past this boundary.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Example:
    """One production trace or golden, ready to be judged."""

    example_id: str
    question: str
    answer: str
    context: tuple[str, ...] = ()
    expected: str | None = None
    slices: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict) -> "Example":
        return cls(
            example_id=str(raw["example_id"]),
            question=str(raw.get("question", "")),
            answer=str(raw.get("answer", "")),
            context=tuple(raw.get("context") or ()),
            expected=raw.get("expected"),
            slices={str(k): str(v) for k, v in (raw.get("slices") or {}).items()},
        )

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "question": self.question,
            "answer": self.answer,
            "context": list(self.context),
            "expected": self.expected,
            "slices": dict(self.slices),
        }

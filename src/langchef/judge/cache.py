"""Content-addressed judgement cache.

The key is the example, the rubric hash, the model and the tier — everything
that could change the verdict, and nothing that could not. So a rerun of an
unchanged suite costs nothing, and a one-word rubric edit correctly invalidates
every score it produced.

The store is a JSONL file (DECISIONS.md #4): appendable, diffable, and readable
in a pull request. Later lines win, so a re-record is an append rather than a
rewrite, and the history of what a judge said stays in the file.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from langchef.judge.example import Example
from langchef.judge.providers import Judgement
from langchef.judge.rubric import Rubric


def prompt_key(prompt: str, model: str) -> str:
    """Cassette key: the exact bytes sent, under the model that answered."""
    return hashlib.sha256(f"{model}\x00{prompt}".encode()).hexdigest()[:16]


def judgement_key(example: Example, rubric: Rubric, model: str, tier: str) -> str:
    """Cache key for one verdict.

    ``expected`` and ``context`` are in the key because both change what a
    correct verdict is. ``slices`` are not: they are metadata for grouping, and
    including them would miss the cache every time someone adds a tag.
    """
    material = json.dumps(
        {
            "example_id": example.example_id,
            "question": example.question,
            "answer": example.answer,
            "context": list(example.context),
            "expected": example.expected,
            "rubric": rubric.ref,
            "model": model,
            "tier": tier,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


@dataclass
class Cache:
    """A JSONL-backed judgement store. Absent file means an empty cache."""

    path: Path
    entries: dict[str, dict] | None = None
    hits: int = 0
    misses: int = 0

    def __post_init__(self) -> None:
        self.entries = {}
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                self.entries[record["key"]] = record

    def get(self, key: str) -> Judgement | None:
        record = (self.entries or {}).get(key)
        if record is None:
            self.misses += 1
            return None
        self.hits += 1
        payload = record["judgement"]
        return Judgement(
            example_id=payload["example_id"],
            verdict=payload["verdict"],
            confidence=payload["confidence"],
            criterion=payload["criterion"],
            rationale=payload["rationale"],
            model=payload["model"],
        )

    def put(self, key: str, judgement: Judgement, tier: str, rubric_ref: str) -> None:
        record = {
            "key": key,
            "tier": tier,
            "rubric": rubric_ref,
            "judgement": judgement.to_dict(),
        }
        (self.entries if self.entries is not None else {})[key] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    @property
    def size(self) -> int:
        return len(self.entries or {})

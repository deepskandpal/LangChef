"""Rubrics, and the hash that pins them.

A rubric is Markdown (DECISIONS.md #4): a person has to be able to review it in
a pull request, and a prompt buried in a Python string is not reviewable. Its
criteria are the ``###`` headings, which is also how the judge is told to cite
one.

The hash matters more than the text. Every cached judgement is keyed on it, so
editing one word of a rubric correctly invalidates every score it produced —
that is what stops a suite from silently mixing verdicts from two different
definitions of "good", which is the most common way an eval suite starts lying.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

HEADING = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


class RubricError(ValueError):
    """A rubric is missing, empty, or has no criteria."""


@dataclass(frozen=True)
class Rubric:
    """One judging rubric, with the pin that identifies it."""

    name: str
    text: str
    criteria: tuple[str, ...]
    path: Path | None = None

    @property
    def digest(self) -> str:
        """Content hash. Twelve hex characters is plenty to pin a file."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12]

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.digest}"


def parse(text: str, name: str, path: Path | None = None) -> Rubric:
    """Build a rubric from Markdown. Criteria are the ``###`` headings."""
    if not text.strip():
        raise RubricError(f"rubric {name!r} is empty")
    criteria = tuple(match.group(1).strip() for match in HEADING.finditer(text))
    if not criteria:
        raise RubricError(
            f"rubric {name!r} has no criteria — each one is a '### ' heading, "
            "and the judge is required to cite one by name"
        )
    return Rubric(name=name, text=text, criteria=criteria, path=path)


def load(path: Path) -> Rubric:
    """Read a rubric from disk."""
    if not path.is_file():
        raise RubricError(f"no rubric at {path}")
    return parse(path.read_text(encoding="utf-8"), name=path.stem, path=path)

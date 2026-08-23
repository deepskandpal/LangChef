"""The quality ledger — the persistent record, and the reason this is not a leaderboard.

A leaderboard says which variant is ahead today. It hides the two things that
decide whether the number means anything: how well the judge agreed with a
person when it was last checked, and what was decided last time. The ledger
keeps both, append-only, in a file a reviewer can read.

Entries are never edited. A correction is a new entry, so the record of what was
believed at the time survives — which is what makes a post-mortem possible.
"""

from datetime import UTC, datetime
from pathlib import Path

from langchef.workspace.formats import append_jsonl, read_jsonl

KINDS = ("calibration", "run", "experiment", "decision", "note")


class LedgerError(ValueError):
    """An entry that would make the record less trustworthy than no record."""


def append(path: Path, kind: str, summary: str, **detail) -> dict:
    """Add one entry. ``kind`` is constrained so the ledger stays queryable."""
    if kind not in KINDS:
        raise LedgerError(f"unknown ledger kind {kind!r}: expected one of {', '.join(KINDS)}")
    entry = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        "summary": summary,
        **detail,
    }
    append_jsonl(path, entry)
    return entry


def read(path: Path, kind: str | None = None, limit: int | None = None) -> list[dict]:
    """Entries, newest first."""
    if not path.is_file():
        return []
    rows = read_jsonl(path)
    if kind:
        rows = [row for row in rows if row.get("kind") == kind]
    rows.reverse()
    return rows[:limit] if limit else rows


def last_calibration(path: Path) -> dict | None:
    """The most recent calibration entry — what the judge was worth last time."""
    entries = read(path, kind="calibration", limit=1)
    return entries[0] if entries else None

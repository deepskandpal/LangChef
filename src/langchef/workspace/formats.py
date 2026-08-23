"""Reading and writing the workspace's file formats.

Text is the record (DECISIONS.md #4): TOML for configuration, JSONL for goldens
and labels, JSON for baselines and reports, Markdown for rubrics and memos.
Parquet appears exactly once, for per-example scores, because that is the only
thing here that gets large and the only thing nobody reads by eye.
"""

import json
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


class FormatError(ValueError):
    """A workspace file could not be read as the format it claims to be."""


def read_jsonl(path: Path) -> list[dict]:
    """Every non-blank line as an object. Reports the line number on failure."""
    if not path.is_file():
        raise FormatError(f"no such file: {path}")
    rows: list[dict] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise FormatError(f"{path}:{number}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            written += 1
    return written


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise FormatError(f"no such file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FormatError(f"{path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_toml(path: Path) -> dict:
    if not path.is_file():
        raise FormatError(f"no such file: {path}")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise FormatError(f"{path}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_scores(path: Path, rows: Sequence[dict]) -> int:
    """Per-example scores. The one binary file in the workspace.

    pyarrow is imported here rather than at module scope so that every other
    format keeps working if the wheel is unavailable on some platform.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pq.write_table(pa.table({}), path)
        return 0
    columns = sorted({key for row in rows for key in row})
    table = pa.table({column: [row.get(column) for row in rows] for column in columns})
    pq.write_table(table, path)
    return len(rows)


def read_scores(path: Path) -> list[dict]:
    import pyarrow.parquet as pq

    if not path.is_file():
        raise FormatError(f"no such file: {path}")
    return pq.read_table(path).to_pylist()

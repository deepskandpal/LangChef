"""``[dataset]`` in ``evals/config.toml``: point at a file you already own.

The expensive way in is collect traces, hand-assemble JSONL, write a rubric,
label forty examples. That is an afternoon of work before the tool has told
anybody anything, asked of a team that does not yet believe it works. Most teams
already have a labelled test set sitting in a CSV.

**The column mapping is a workspace artifact, not a flag.** Which column is the
input and which is the target is a claim about what the data means, and it
belongs somewhere a reviewer can object to it in a pull request. Passing it on
the command line would make it invisible and unversioned, which is the same
argument as DECISIONS #4.

```toml
[dataset]
path  = "data/support-tickets.parquet"
class = "classification"
input = "ticket_body"
label = "resolved_category"
```

The ``class`` field is load-bearing rather than decorative. It selects the
comparison arithmetic through the pack's ``outcome_shape`` and decides whether
calibration applies at all, so an unknown class fails here rather than
defaulting to ``qna`` and quietly measuring the wrong thing.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from langchef.packs.loader import load_class
from langchef.packs.manifest import ManifestError

__all__ = ["DatasetError", "DatasetSpec", "load_rows", "spec_from_config"]


class DatasetError(ValueError):
    """The dataset could not be read as declared."""


@dataclass(frozen=True)
class DatasetSpec:
    """A declared mapping from one file's columns onto the internal shape."""

    path: Path
    task_class: str
    outcome_shape: str
    requires_judge: bool
    columns: dict[str, str]

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()


def spec_from_config(raw: dict, root: Path) -> DatasetSpec | None:
    """Resolve ``[dataset]`` against the packs, or None when it is absent.

    Every failure here names the field and what was found, because a stack trace
    from a TOML parser tells a person nothing about which of their columns was
    wrong.
    """
    table = raw.get("dataset")
    if not table:
        return None

    path = table.get("path")
    if not path:
        raise DatasetError("[dataset] needs a path to the file to read")

    name = table.get("class")
    if not name:
        known = "qna, generation, classification, retrieval, reranking"
        raise DatasetError(
            f"[dataset] needs a class: it decides the comparison arithmetic and "
            f"whether calibration applies. Try one of: {known}"
        )
    try:
        _, task_class = load_class(name)
    except ManifestError as exc:
        raise DatasetError(str(exc)) from exc

    columns = {k: v for k, v in table.items() if k not in {"path", "class"}}
    if not columns:
        raise DatasetError(
            f"[dataset] declares no column mapping. Task class {name!r} expects "
            f"{', '.join(task_class.required_fields)}."
        )

    resolved = (root / path).resolve() if not Path(path).is_absolute() else Path(path)
    return DatasetSpec(
        path=resolved,
        task_class=task_class.name,
        outcome_shape=task_class.outcome_shape,
        requires_judge=task_class.requires_judge,
        columns=columns,
    )


def _read_csv(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def _read_parquet(path: Path) -> Iterator[dict]:
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    yield from table.to_pylist()


def load_rows(spec: DatasetSpec) -> tuple[list[dict], list[str]]:
    """Rows in the internal shape, and one complaint per row that could not be read.

    Returns the problems rather than raising on the first one, and never drops a
    row silently: **silent row loss changes the denominator of every statistic
    downstream**, so a run over 900 of 1000 rows that reports 900 is lying about
    what it measured by omission.
    """
    if not spec.path.exists():
        raise DatasetError(f"no dataset at {spec.path}")

    if spec.suffix in {".csv", ".tsv"}:
        raw = _read_csv(spec.path)
    elif spec.suffix in {".parquet", ".pq"}:
        raw = _read_parquet(spec.path)
    else:
        raise DatasetError(
            f"cannot read {spec.suffix or 'a file with no extension'}: this reads .csv and .parquet"
        )

    rows: list[dict] = []
    problems: list[str] = []
    wanted = spec.columns
    for index, source in enumerate(raw, start=1):
        missing = [column for column in wanted.values() if column not in source]
        if missing:
            found = ", ".join(sorted(source)) or "no columns at all"
            problems.append(f"row {index}: no column named {', '.join(missing)}. Found: {found}")
            continue
        row = {field: source[column] for field, column in wanted.items()}
        row.setdefault("example_id", str(index))
        rows.append(row)

    return rows, problems

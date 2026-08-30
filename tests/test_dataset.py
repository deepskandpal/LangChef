"""``[dataset]``: reading a file somebody already owns.

The tests that matter here are the failure ones. A loader that reads a clean CSV
is easy; a loader that loses ten rows quietly changes the denominator of every
statistic downstream, and nothing later can detect that it happened.
"""

from __future__ import annotations

import csv

import pytest

from langchef.workspace.dataset import DatasetError, load_rows, spec_from_config


def _csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


CONFIG = {
    "dataset": {
        "path": "data/tickets.csv",
        "class": "classification",
        "input": "ticket_body",
        "label": "resolved_category",
    }
}


def test_a_csv_someone_already_owns_loads(tmp_path):
    _csv(
        tmp_path / "data" / "tickets.csv",
        [{"ticket_body": "card declined", "resolved_category": "billing"}],
        ["ticket_body", "resolved_category"],
    )
    spec = spec_from_config(CONFIG, tmp_path)
    rows, problems = load_rows(spec)

    assert problems == []
    assert rows == [{"input": "card declined", "label": "billing", "example_id": "1"}]


def test_parquet_loads_the_same_way(tmp_path):
    pq = pytest.importorskip("pyarrow.parquet")
    pa = pytest.importorskip("pyarrow")

    path = tmp_path / "data" / "tickets.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table({"ticket_body": ["card declined"], "resolved_category": ["billing"]}), path
    )
    config = {**CONFIG, "dataset": {**CONFIG["dataset"], "path": "data/tickets.parquet"}}
    rows, problems = load_rows(spec_from_config(config, tmp_path))

    assert problems == []
    assert rows[0]["input"] == "card declined"


def test_an_unreadable_row_is_reported_not_dropped(tmp_path):
    """The one that matters.

    Silent row loss changes the denominator of every statistic downstream, and a
    run over 900 of 1000 rows that reports 900 is lying by omission. So a row
    that cannot be read comes back as a complaint, and the caller decides.
    """
    path = tmp_path / "data" / "tickets.csv"
    path.parent.mkdir(parents=True)
    path.write_text("ticket_body,wrong_name\ncard declined,billing\n", encoding="utf-8")

    rows, problems = load_rows(spec_from_config(CONFIG, tmp_path))

    assert rows == []
    assert len(problems) == 1
    assert "resolved_category" in problems[0]
    assert "ticket_body" in problems[0]  # and it says what it DID find


def test_a_misnamed_column_names_itself_and_what_was_found(tmp_path):
    """Not a KeyError. A person needs to know which of their columns was wrong."""
    _csv(
        tmp_path / "data" / "tickets.csv",
        [{"body": "x", "category": "y"}],
        ["body", "category"],
    )
    _, problems = load_rows(spec_from_config(CONFIG, tmp_path))

    assert problems
    assert "Found: body, category" in problems[0]


def test_an_unknown_class_fails_rather_than_defaulting(tmp_path):
    """The class selects the arithmetic, so guessing it measures the wrong thing.

    Defaulting to qna would silently apply a judge and a calibration to a dataset
    with a hard label, which DECISIONS #12 says is meaningless.
    """
    config = {"dataset": {**CONFIG["dataset"], "class": "telepathy"}}

    with pytest.raises(DatasetError) as caught:
        spec_from_config(config, tmp_path)

    assert "telepathy" in str(caught.value)
    assert "available" in str(caught.value)


def test_the_class_carries_its_outcome_shape_and_judge_requirement(tmp_path):
    """This is the seam: the pack answers, core never learns the class name."""
    spec = spec_from_config(CONFIG, tmp_path)

    assert spec.task_class == "classification"
    assert spec.outcome_shape == "binary"
    assert spec.requires_judge is False


def test_no_dataset_table_is_not_an_error(tmp_path):
    """BYOD is opt-in. A workspace without one behaves exactly as before."""
    assert spec_from_config({"workspace": {"name": "x"}}, tmp_path) is None


@pytest.mark.parametrize(
    "table, expected",
    [
        ({"class": "classification", "input": "a"}, "needs a path"),
        ({"path": "d.csv", "input": "a"}, "needs a class"),
        ({"path": "d.csv", "class": "classification"}, "no column mapping"),
    ],
)
def test_an_incomplete_declaration_says_which_part_is_missing(tmp_path, table, expected):
    with pytest.raises(DatasetError) as caught:
        spec_from_config({"dataset": table}, tmp_path)
    assert expected in str(caught.value)


def test_an_unsupported_format_says_what_it_reads(tmp_path):
    path = tmp_path / "data" / "tickets.xlsx"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not really a spreadsheet")
    config = {"dataset": {**CONFIG["dataset"], "path": "data/tickets.xlsx"}}

    with pytest.raises(DatasetError) as caught:
        load_rows(spec_from_config(config, tmp_path))

    assert ".csv and .parquet" in str(caught.value)


def test_a_missing_file_says_where_it_looked(tmp_path):
    with pytest.raises(DatasetError) as caught:
        load_rows(spec_from_config(CONFIG, tmp_path))
    assert "tickets.csv" in str(caught.value)

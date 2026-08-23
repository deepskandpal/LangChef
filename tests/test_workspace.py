"""M3 — layout, formats, runs, ledger, and the approval gate's bookkeeping."""

import pytest

from langchef.core.gates import rubric_gate, unmet
from langchef.workspace import ledger, runs, scaffold
from langchef.workspace.config import approve_rubric, load
from langchef.workspace.formats import (
    FormatError,
    append_jsonl,
    read_json,
    read_jsonl,
    read_scores,
    write_jsonl,
    write_scores,
)
from langchef.workspace.paths import WORKSPACE_DIR, Workspace, WorkspaceError, find


@pytest.fixture
def workspace(tmp_path):
    ws = Workspace(tmp_path / WORKSPACE_DIR)
    scaffold.create(ws, name="test")
    return ws


def test_init_writes_a_usable_workspace(workspace):
    assert workspace.exists()
    assert (workspace.rubrics / "answer-quality.md").is_file()
    for directory in workspace.directories():
        assert directory.is_dir()


def test_init_never_overwrites(workspace):
    workspace.config.write_text("# edited by a person\n", encoding="utf-8")
    assert scaffold.create(workspace, name="test") == []
    assert "edited by a person" in workspace.config.read_text()


def test_a_workspace_is_found_from_below_it(workspace):
    deep = workspace.root.parent / "src" / "deep" / "nested"
    deep.mkdir(parents=True)
    assert find(deep).root == workspace.root


def test_no_workspace_says_what_to_run(tmp_path):
    with pytest.raises(WorkspaceError, match="langchef init"):
        find(tmp_path)


def test_jsonl_round_trips_and_reports_the_bad_line(tmp_path):
    path = tmp_path / "rows.jsonl"
    write_jsonl(path, [{"a": 1}, {"a": 2}])
    assert read_jsonl(path) == [{"a": 1}, {"a": 2}]
    append_jsonl(path, {"a": 3})
    assert len(read_jsonl(path)) == 3

    path.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    with pytest.raises(FormatError, match=":2:"):
        read_jsonl(path)


def test_scores_round_trip_through_parquet(tmp_path):
    rows = [
        {"example_id": "a", "verdict": "pass", "confidence": 1.0},
        {"example_id": "b", "verdict": "fail", "confidence": 0.2},
    ]
    path = tmp_path / "scores.parquet"
    assert write_scores(path, rows) == 2
    back = {row["example_id"]: row for row in read_scores(path)}
    assert back["b"]["verdict"] == "fail"


def test_runs_save_load_and_sort_newest_first(workspace):
    for run_id in ("suite-20260101T000000Z", "suite-20260301T000000Z"):
        runs.Run(workspace, run_id, suite="suite", pin={"rubric": "r@1"}).save()
    assert runs.latest(workspace).run_id == "suite-20260301T000000Z"
    assert [r.run_id for r in runs.every(workspace)][0] == "suite-20260301T000000Z"
    assert runs.load(workspace, "suite-20260101T000000Z").pin == {"rubric": "r@1"}


def test_run_ids_are_sortable_and_readable():
    from datetime import UTC, datetime

    when = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)
    assert runs.new_run_id("Support Suite", "top-k 1", when) == (
        "support-suite-top-k-1-20260823T120000Z"
    )


def test_latest_filters_by_suite_and_arm(workspace):
    runs.Run(workspace, "a-20260101T000000Z", suite="a", arm="baseline").save()
    runs.Run(workspace, "b-20260201T000000Z", suite="b", arm="variant").save()
    assert runs.latest(workspace, suite="a").run_id == "a-20260101T000000Z"
    assert runs.latest(workspace, arm="variant").run_id == "b-20260201T000000Z"
    assert runs.latest(workspace, suite="a", arm="variant") is None


def test_the_ledger_is_append_only_and_queryable(workspace):
    ledger.append(workspace.ledger, "run", "first")
    ledger.append(workspace.ledger, "calibration", "kappa 0.7", kappa=0.7, run_id="r1")
    ledger.append(workspace.ledger, "run", "second")

    assert [e["summary"] for e in ledger.read(workspace.ledger)] == ["second", "kappa 0.7", "first"]
    assert len(ledger.read(workspace.ledger, kind="run")) == 2
    assert ledger.last_calibration(workspace.ledger)["kappa"] == 0.7


def test_an_unknown_ledger_kind_is_refused(workspace):
    with pytest.raises(ledger.LedgerError, match="unknown ledger kind"):
        ledger.append(workspace.ledger, "vibes", "something happened")


def test_an_absent_ledger_reads_as_empty(workspace):
    assert ledger.read(workspace.ledger) == []
    assert ledger.last_calibration(workspace.ledger) is None


def test_approval_is_recorded_without_destroying_the_comments(workspace):
    before = workspace.config.read_text(encoding="utf-8")
    assert "# Gate one." in before

    approve_rubric(workspace, "answer-quality@abc123")
    settings = load(workspace)
    assert settings.approved_rubric == "answer-quality@abc123"
    assert "# Gate one." in workspace.config.read_text(encoding="utf-8")

    approve_rubric(workspace, "answer-quality@def456")
    assert load(workspace).approved_rubric == "answer-quality@def456"


def test_the_gate_is_unmet_when_absent_and_when_moved():
    assert unmet([rubric_gate(None, "r@1")])
    assert "no rubric approved" in rubric_gate(None, "r@1").remedy

    moved = rubric_gate("r@1", "r@2")
    assert not moved.met
    assert "changed since it was approved" in moved.remedy

    assert rubric_gate("r@1", "r@1").met


def test_defaults_survive_a_minimal_config(workspace):
    workspace.config.write_text('[workspace]\nname = "x"\n', encoding="utf-8")
    settings = load(workspace)
    assert settings.judge.provider == "containment"
    assert settings.level == 0.95
    assert settings.approved_rubric is None


def test_unknown_config_keys_are_ignored_not_fatal(workspace):
    workspace.config.write_text(
        '[workspace]\nname = "x"\n\n[judge]\nprovider = "containment"\n'
        'future_option = "from a newer langchef"\n',
        encoding="utf-8",
    )
    assert load(workspace).judge.provider == "containment"


def test_baselines_and_reports_are_plain_json(workspace):
    run = runs.Run(workspace, "r-1", suite="s")
    run.save()
    run.artifact("compare.json", {"verdict": "regression"})
    assert read_json(run.file("compare.json"))["verdict"] == "regression"

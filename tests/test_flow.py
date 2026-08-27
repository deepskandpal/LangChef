"""The whole loop, through the CLI, with no key and no network.

init -> approve -> judge -> plan -> label -> calibrate -> baseline -> compare -> memo,
plus the two refusals that make the gates real: an edited rubric (exit 2) and a
comparison across moved pins (exit 5).
"""

import json

import pytest

from langchef.core.exits import Exit
from langchef.workspace.formats import read_jsonl, write_jsonl

CONTEXT = "Payment terms on every Northwind invoice are net thirty days."


def golden(example_id, answer, expected="net thirty days", topic="billing"):
    return {
        "example_id": example_id,
        "question": "Tell me the payment terms.",
        "answer": answer,
        "context": [CONTEXT],
        "expected": expected,
        "slices": {"topic": topic},
    }


SUITE_SIZE = 30
WRONG = "Payment is due immediately on receipt."


def suite(correct):
    """The same 30 example ids in every arm; the first `correct` are answered right.

    Stable ids across arms are the whole point — a comparison pairs on them, and
    two arms that answer different questions are not two arms.
    """
    return [golden(f"ex-{i:02}", CONTEXT if i < correct else WRONG) for i in range(SUITE_SIZE)]


@pytest.fixture
def workspace(tmp_path, run_cli):
    code, payload, _ = run_cli("init", "--name", "flow-test", cwd=tmp_path)
    assert code == Exit.OK, payload
    evals = tmp_path / "evals"
    # Two arms over the same example ids: the variant gets six more wrong answers.
    write_jsonl(evals / "goldens" / "support.baseline.jsonl", suite(correct=24))
    write_jsonl(evals / "goldens" / "support.variant.jsonl", suite(correct=18))
    return tmp_path


def test_the_whole_loop(workspace, run_cli):
    def cli(*args):
        return run_cli(*args, cwd=workspace)

    # Gate one: nothing runs before a person has approved the rubric.
    code, payload, _ = cli("judge", "run", "--arm", "baseline")
    assert code == Exit.REFUSED
    assert payload["gate"]["name"] == "rubric-approved"

    code, approval, _ = cli("approve", "rubric")
    assert code == Exit.OK
    assert approval["rubric"].startswith("answer-quality@")

    code, run, _ = cli("judge", "run", "--arm", "baseline", "--run-id", "base")
    assert code == Exit.OK
    assert run["stats"]["n"] == 30
    assert run["stats"]["pass"] == 24
    assert run["pin"]["rubric"] == approval["rubric"]

    # A rerun is free.
    code, again, _ = cli("judge", "run", "--arm", "baseline", "--run-id", "base-2")
    assert again["stats"]["provider_calls"] == 0
    assert again["stats"]["cache_hits"] == 30

    # Labelling: plan, answer the plan, import.
    code, plan, _ = cli("label", "plan", "--budget", "20", "--run", "base")
    assert code == Exit.OK
    assert plan["selected"] == 20
    assert set(plan["by_stratum"]) == {"pass", "fail"}

    todo = workspace / "evals" / "labels" / "answer-quality.todo.jsonl"
    rows = read_jsonl(todo)
    assert all(row["verdict"] is None for row in rows)
    # A person agrees with the judge except on two, which they call the other way.
    write_jsonl(
        todo,
        [
            {**row, "verdict": "pass" if index >= 2 else "fail"}
            for index, row in enumerate(
                sorted(rows, key=lambda r: r["example_id"]),
            )
        ],
    )
    code, imported, _ = cli("label", "import", str(todo))
    assert code == Exit.OK
    assert imported["imported"] == 20

    code, calibration, _ = cli("calibrate", "report", "--run", "base")
    assert code == Exit.OK
    assert calibration["n"] == 20
    assert -1.0 <= calibration["kappa"] <= 1.0
    assert "taxonomy" in calibration
    assert (workspace / "evals" / "runs" / "base" / "calibration.json").is_file()

    # The experiment.
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    code, variant, _ = cli("judge", "run", "--arm", "variant", "--run-id", "var")
    assert code == Exit.OK
    assert variant["stats"]["pass"] == 18

    code, comparison, _ = cli("compare", "--variant", "var")
    assert code == Exit.OK
    assert comparison["verdict"] == "regression"
    assert comparison["difference"] == pytest.approx(-0.2)
    assert comparison["discordance"]["broke"] == 6
    assert comparison["interval"]["hi"] < 0

    # The memo.
    code, memo, _ = cli("memo", "render", "--run", "var")
    assert code == Exit.OK
    text = (workspace / "evals" / "memos" / "var.md").read_text(encoding="utf-8")
    assert "Can this judge be trusted" in text
    assert "A regression" in text
    assert memo["has_comparison"] and memo["has_calibration"]

    # And the record.
    code, ledger, _ = cli("ledger", "query", "--limit", "50")
    kinds = {entry["kind"] for entry in ledger["entries"]}
    assert {"run", "calibration", "experiment"} <= kinds


def test_editing_the_rubric_revokes_the_approval(workspace, run_cli):
    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK

    rubric = workspace / "evals" / "rubrics" / "answer-quality.md"
    rubric.write_text(rubric.read_text() + "\nAnd be brief.\n", encoding="utf-8")

    code, payload, _ = cli("judge", "run", "--arm", "baseline", "--run-id", "after")
    assert code == Exit.REFUSED
    assert "changed since it was approved" in payload["message"]


def test_comparing_across_pins_is_refused(workspace, run_cli):
    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK

    rubric = workspace / "evals" / "rubrics" / "answer-quality.md"
    rubric.write_text(rubric.read_text() + "\nAnd be brief.\n", encoding="utf-8")
    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK

    code, payload, _ = cli("compare", "--variant", "var")
    assert code == Exit.PIN_MISMATCH
    assert "rubric" in payload["moved"]


def test_calibrating_without_labels_says_what_to_run(workspace, run_cli):
    assert run_cli("approve", "rubric", cwd=workspace).code == Exit.OK
    assert run_cli("judge", "run", "--arm", "baseline", "--run-id", "b", cwd=workspace).code == 0
    code, payload, _ = run_cli("calibrate", "report", "--run", "b", cwd=workspace)
    assert code == Exit.ERROR
    assert "langchef label plan" in payload["message"]


def test_a_memo_without_calibration_says_so_rather_than_omitting_it(workspace, run_cli):
    assert run_cli("approve", "rubric", cwd=workspace).code == Exit.OK
    assert run_cli("judge", "run", "--arm", "baseline", "--run-id", "b", cwd=workspace).code == 0
    code, payload, _ = run_cli("memo", "render", "--run", "b", cwd=workspace)
    assert code == Exit.OK
    assert payload["has_calibration"] is False
    text = (workspace / "evals" / "memos" / "b.md").read_text(encoding="utf-8")
    assert "never been checked against a person" in text


def test_every_command_writes_json_to_stdout_and_prose_to_stderr(workspace, run_cli):
    """DECISIONS.md #3, checked rather than intended."""
    assert run_cli("approve", "rubric", cwd=workspace).code == Exit.OK
    for args in (
        ("doctor",),
        ("contract",),
        ("packs", "list"),
        ("judge", "run", "--arm", "baseline", "--run-id", "b"),
        ("ledger", "query"),
    ):
        result = run_cli(*args, cwd=workspace)
        assert json.loads(result.out), f"{args} did not put JSON on stdout"
        assert result.err.strip(), f"{args} said nothing to a person on stderr"


def test_compare_warns_when_it_picks_among_repeated_variant_runs(workspace, run_cli):
    """Outside the gate, ambiguity is a disclosure — not a silent latest pick.

    Twin of readout's refusal (#13): compare stays exit 0 and keeps going, but
    names the run it chose and how many others matched, on stderr.
    """

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    for run_id in ("var-a", "var-b"):
        assert cli("judge", "run", "--arm", "variant", "--run-id", run_id).code == Exit.OK

    result = cli("compare")
    assert result.code == Exit.OK
    assert result.payload["ok"] is True
    assert result.payload["variant_run"] == "var-b"  # newest of the two
    assert "2 variant runs matched" in result.err
    assert "var-b" in result.err
    assert "1 other" in result.err
    # stdout stays pure JSON — the disclosure is stderr-only.
    assert json.loads(result.out)["variant_run"] == "var-b"


def test_compare_is_quiet_about_resolution_when_only_one_variant_matches(workspace, run_cli):
    """One match is not a choice; no disclosure noise."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var-only").code == Exit.OK

    result = cli("compare")
    assert result.code == Exit.OK
    assert result.payload["variant_run"] == "var-only"
    assert "variant runs matched" not in result.err
    assert "Pass --variant" not in result.err

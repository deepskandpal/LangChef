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


# --- #25: an ambiguous `compare` discloses which run it chose ----------------


def _two_variant_runs(cli):
    """A workspace with a pinned baseline and two runs on the variant arm."""
    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var-a").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var-b").code == Exit.OK


def test_ambiguous_compare_names_the_run_it_chose(workspace, run_cli):
    """Two runs match and none was named, so say which one was used."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _two_variant_runs(cli)

    result = cli("compare")

    assert result.code == Exit.OK, result.payload
    # Newest first: ids sort chronologically, so var-b wins.
    assert result.payload["variant_run"] == "var-b"
    assert "var-b" in result.err
    assert "2 runs" in result.err
    assert "--variant" in result.err


def test_ambiguous_compare_keeps_stdout_pure_json(workspace, run_cli):
    """The contract has no --format flag, and this must not become one."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _two_variant_runs(cli)

    result = cli("compare")

    assert result.code == Exit.OK
    # Parses whole, and nothing but the document is on stdout.
    assert json.loads(result.out)["variant_run"] == "var-b"
    assert "Pass --variant" not in result.out


def test_unambiguous_compare_stays_silent(workspace, run_cli):
    """One matching run is not ambiguous, so there is nothing to disclose."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK

    result = cli("compare")

    assert result.code == Exit.OK
    assert result.payload["variant_run"] == "var"
    assert "not compared" not in result.err
    assert "Pass --variant" not in result.err


def test_named_variant_is_never_ambiguous(workspace, run_cli):
    """Naming the run is the remedy the warning suggests; it must silence it."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _two_variant_runs(cli)

    result = cli("compare", "--variant", "var-a")

    assert result.code == Exit.OK
    assert result.payload["variant_run"] == "var-a"
    assert "not compared" not in result.err


def test_compare_says_which_criterion_the_regression_landed_on(workspace, run_cli):
    """One verdict is a fact; the criterion it landed on is the actionable half.

    Six goldens break, all of them by stating the wrong fact, so the whole of
    the twenty-point drop has to be attributed to Correctness — and the artifact
    has to carry it, because a memo may quote no number that is not in a file
    under ``runs/``.
    """

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK

    code, payload, err = cli("compare", "--variant", "var")
    assert code == Exit.OK

    breakdown = payload["by_criterion"]
    assert breakdown["method"] == "holm"
    assert breakdown["uncited_failures"] == 0
    assert breakdown["attributed"] == pytest.approx(payload["difference"])

    correctness = next(c for c in breakdown["criteria"] if c["criterion"] == "Correctness")
    assert correctness["attribution"] == "moved_worse"
    assert correctness["difference"] == pytest.approx(-0.2)
    assert correctness["mde"] > 0
    # Not the overall comparison's word, and never both at once.
    assert correctness["attribution"] not in ("regression", "improvement")

    written = json.loads(
        (workspace / "evals" / "runs" / "var" / "compare.json").read_text(encoding="utf-8")
    )
    assert written["by_criterion"] == breakdown
    assert "Correctness" in err and "MOVED WORSE" in err


# --- #29: a declared tolerance turns compare into a non-inferiority test -----


def _baseline_and_variant(cli):
    """A pinned baseline and one variant run, the minimum a comparison needs."""
    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "baseline", "--run-id", "base").code == Exit.OK
    assert cli("baseline", "set", "--run", "base").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK


def test_a_tolerance_asks_did_it_hold_rather_than_is_it_better(workspace, run_cli):
    """The question most real changes ask.

    A cheaper model, a dropped reranker, a fine-tune: none of these hope to be
    better, they need to not be meaningfully worse. Read as a superiority test a
    null result means nothing, and it routinely gets read as permission to ship.
    """

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _baseline_and_variant(cli)
    result = cli("compare", "--variant", "var", "--tolerance", "0.03")

    assert result.code == Exit.OK
    block = result.payload["non_inferiority"]
    assert block["verdict"] in ("held", "failed", "unresolved")
    assert block["margin"] == pytest.approx(0.03)


def test_unresolved_is_not_held_and_says_so(workspace, run_cli):
    """The whole failure this flag exists to prevent.

    An underpowered run reading as a pass is how a regression ships. So the
    third verdict is named, distinct, and carries the detection limit that
    explains why it could not decide.
    """

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _baseline_and_variant(cli)

    # Find the margin band that this fixture's interval cannot resolve, rather
    # than assuming one: the arms here genuinely differ, so too small a margin
    # gives `failed` (a correct answer) and too large gives `held`.
    seen = {}
    for margin in ("0.001", "0.02", "0.05", "0.10", "0.30"):
        block = cli("compare", "--variant", "var", "--tolerance", margin).payload["non_inferiority"]
        seen[margin] = block["verdict"]

    assert "unresolved" in seen.values(), seen
    undecidable = next(m for m, v in seen.items() if v == "unresolved")
    result = cli("compare", "--variant", "var", "--tolerance", undecidable)
    block = result.payload["non_inferiority"]

    assert block["verdict"] == "unresolved"
    assert block["verdict"] != "held"
    assert "unresolved is not held" in result.err
    # And it carries the number that explains why it could not decide.
    assert block["mde"] > 0


def test_the_payload_records_where_the_margin_came_from(workspace, run_cli):
    """A flag and a pre-registration produce the same three words.

    They are not the same evidence: one was decided before the interval was
    visible and one may not have been. Only the payload can carry that, because
    the verdict string cannot.
    """

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _baseline_and_variant(cli)
    result = cli("compare", "--variant", "var", "--tolerance", "0.03")

    block = result.payload["non_inferiority"]
    assert block["source"] == "command-line flag"
    assert block["declared_before_the_run"] is False
    assert "constrains nobody" in result.err


def test_the_one_sided_level_is_stated_not_implied(workspace, run_cli):
    """The interval is two-sided; a non-inferiority test reads one bound of it.

    That makes the effective one-sided level (1+level)/2, which is the
    conservative direction. Reporting the two-sided level beside a one-sided
    test would misstate how sharp the test is, so both are named.
    """

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _baseline_and_variant(cli)
    block = cli("compare", "--variant", "var", "--tolerance", "0.03").payload["non_inferiority"]

    assert block["one_sided_level"] == pytest.approx((1 + block["level"]) / 2)


def test_no_tolerance_means_no_non_inferiority_block(workspace, run_cli):
    """Superiority stays the default. Nothing about the old output moves."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    _baseline_and_variant(cli)
    result = cli("compare", "--variant", "var")

    assert result.payload["non_inferiority"] is None
    assert "QUALITY" not in result.err

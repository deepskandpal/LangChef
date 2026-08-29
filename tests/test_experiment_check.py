"""`experiment check` must not report a match when there is no run.

The command's own help says "Reports, never decides." It was answering the
first half and asserting the second: an experiment whose variant arm had never
been scored printed `the run matches the pre-registration` at exit 0, with
`"variant_run": null` in the same payload.

That is the shape of failure this product exists to prevent -- nothing crashes,
no number is wrong, and a reassuring sentence is printed about something that
did not happen.
"""

import pytest

from langchef.core.exits import Exit
from langchef.workspace.formats import write_jsonl

CONTEXT = "Payment terms on every Northwind invoice are net thirty days."
WRONG = "Payment is due immediately on receipt."


def golden(example_id, answer):
    return {
        "example_id": example_id,
        "question": "Tell me the payment terms.",
        "answer": answer,
        "context": [CONTEXT],
        "expected": "net thirty days",
        "slices": {"topic": "billing"},
    }


def suite(correct, size=10):
    return [golden(f"ex-{i:02}", CONTEXT if i < correct else WRONG) for i in range(size)]


@pytest.fixture
def workspace(tmp_path, run_cli):
    code, payload, _ = run_cli("init", "--name", "check-test", cwd=tmp_path)
    assert code == Exit.OK, payload
    evals = tmp_path / "evals"
    write_jsonl(evals / "goldens" / "support.baseline.jsonl", suite(correct=8))
    write_jsonl(evals / "goldens" / "support.variant.jsonl", suite(correct=6))
    return tmp_path


@pytest.fixture
def approved_ghost(workspace, run_cli):
    """An approved experiment whose variant arm has never been scored."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert (
        cli(
            "experiment",
            "design",
            "--suite",
            "support",
            "--variant-arm",
            "never-ran",
            "--intent",
            "a variant nobody scored",
            "--id",
            "ghost",
        ).code
        == Exit.OK
    )
    assert cli("experiment", "approve", "ghost").code == Exit.OK
    return workspace


def test_a_missing_run_is_reported_as_a_violation(approved_ghost, run_cli):
    code, payload, _ = run_cli("experiment", "check", "ghost", cwd=approved_ghost)

    assert payload["violations"], "an experiment with no run reported no problems"
    assert any("no run for arm" in v for v in payload["violations"])
    assert payload["ok"] is False
    assert payload["variant_run"] is None
    assert payload["compared"] is False


def test_the_match_sentence_is_not_printed_without_a_run(approved_ghost, run_cli):
    """The exact regression: a reassuring sentence about a run that does not exist."""
    result = run_cli("experiment", "check", "ghost", cwd=approved_ghost)

    assert "the run matches the pre-registration" not in result.out
    assert "the run matches the pre-registration" not in result.err


def test_check_still_exits_zero_when_the_run_is_missing(approved_ghost, run_cli):
    """`check` reports and never decides. Refusing belongs to `readout`."""
    code, _, _ = run_cli("experiment", "check", "ghost", cwd=approved_ghost)
    assert code == Exit.OK


def test_the_approval_gate_is_still_reported_as_met(approved_ghost, run_cli):
    """A missing run is not an approval problem, and must not be conflated with one."""
    _, payload, _ = run_cli("experiment", "check", "ghost", cwd=approved_ghost)
    assert payload["gate"]["met"] is True
    assert payload["gate"]["name"] == "experiment-preregistered"


def test_a_scored_run_is_found_without_naming_it(workspace, run_cli):
    """The other half: resolution has to work, or every check reports a false absence."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK
    assert (
        cli(
            "experiment",
            "design",
            "--suite",
            "support",
            "--variant-arm",
            "variant",
            "--intent",
            "a variant that was scored",
            "--id",
            "real",
        ).code
        == Exit.OK
    )
    assert cli("experiment", "approve", "real").code == Exit.OK

    code, payload, _ = cli("experiment", "check", "real")

    assert code == Exit.OK
    assert payload["compared"] is True
    assert payload["variant_run"] == "var"
    assert not any("no run for arm" in v for v in payload["violations"])


def test_the_match_sentence_is_printed_when_a_run_was_compared(workspace, run_cli):
    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK
    assert (
        cli(
            "experiment",
            "design",
            "--suite",
            "support",
            "--variant-arm",
            "variant",
            "--intent",
            "a variant that was scored",
            "--id",
            "real",
        ).code
        == Exit.OK
    )
    assert cli("experiment", "approve", "real").code == Exit.OK

    result = cli("experiment", "check", "real")
    assert result.payload["violations"] == []
    # say() writes to stderr; stdout carries the JSON payload only.
    assert "the run matches the pre-registration" in result.err


def test_an_explicitly_named_run_is_still_honoured(workspace, run_cli):
    """--variant must keep working exactly as before."""

    def cli(*args):
        return run_cli(*args, cwd=workspace)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--arm", "variant", "--run-id", "var").code == Exit.OK
    assert (
        cli(
            "experiment",
            "design",
            "--suite",
            "support",
            "--variant-arm",
            "variant",
            "--intent",
            "named explicitly",
            "--id",
            "named",
        ).code
        == Exit.OK
    )
    assert cli("experiment", "approve", "named").code == Exit.OK

    code, payload, _ = cli("experiment", "check", "named", "--variant", "var")

    assert code == Exit.OK
    assert payload["variant_run"] == "var"
    assert payload["compared"] is True

"""The stdout/stderr contract, exercised through a real process."""

import json
import os

from langchef import __version__
from langchef.core.contract import COMMANDS

JSON_COMMANDS = (("--version",), ("contract",), ("doctor",), ("packs", "list"))


def test_every_command_writes_json_to_stdout_and_prose_to_stderr(run_cli):
    for args in JSON_COMMANDS:
        code, payload, err = run_cli(*args)
        assert code == 0, f"{args} exited {code}: {err}"
        assert isinstance(payload, dict), f"{args} did not write a JSON object to stdout"
        assert err.strip(), f"{args} wrote no narration to stderr"


def test_version_matches_the_package(run_cli):
    code, payload, _ = run_cli("--version")
    assert code == 0
    assert payload == {"name": "langchef", "version": __version__}


def test_contract_is_the_same_document_the_code_holds(run_cli):
    _, payload, _ = run_cli("contract")
    assert payload["version"] == 1
    assert {c["name"] for c in payload["commands"]} == {c.name for c in COMMANDS}
    assert payload["exit_codes"]["2"].startswith("refused")


def test_doctor_reports_green_here(run_cli):
    code, payload, err = run_cli("doctor")
    assert code == 0, err
    assert payload["ok"] is True
    assert payload["packs"] == ["classification@0.1.0", "genai-rag@0.2.0"]
    required = [c for c in payload["checks"] if c["required"]]
    assert required and all(c["ok"] for c in required)
    # a soft check that is merely unmet must not shout FAIL at a green run
    assert "FAIL" not in err


def test_packs_list_resolves_both_packs_and_the_classes_they_serve(run_cli):
    """#20's first acceptance criterion, through the process an agent runs.

    Two packs, and every task class the product knows about arriving from a
    manifest rather than from anything under ``src/langchef/core/``.
    """
    code, payload, err = run_cli("packs", "list")
    assert code == 0, err
    packs = {p["name"]: p for p in payload["packs"]}
    assert set(packs) == {"genai-rag", "classification"}

    classes = {c["name"]: c for pack in payload["packs"] for c in pack["task_classes"]}
    assert set(classes) == {"qna", "generation", "classification"}
    assert classes["classification"]["requires_judge"] is False
    # The one field of a task class the deterministic core acts on.
    assert {c["outcome_shape"] for c in classes.values()} == {"binary"}
    assert classes["qna"]["requires_judge"] is True
    assert "example_id" in classes["classification"]["schema"]["required"]
    assert packs["classification"]["rubrics"] == []  # empty on purpose, not empty by accident
    assert "2 pack(s)" in err and "3 task class(es)" in err


def test_json_output_is_readable_utf8(run_cli):
    result = run_cli("doctor")
    assert "\\u2014" not in result.out


def test_doctor_never_prints_a_credential_value(run_cli):
    env = {**os.environ, "ANTHROPIC_API_KEY": "sk-ant-not-a-real-key-000"}
    code, payload, err = run_cli("doctor", env=env)
    assert code == 0
    assert payload["credentials_present"] == ["ANTHROPIC_API_KEY"]
    blob = json.dumps(payload) + err
    assert "sk-ant-not-a-real-key-000" not in blob


def test_help_is_the_only_thing_allowed_on_stdout_that_is_not_json(run_cli):
    result = run_cli("--help")
    assert result.code == 0
    assert result.payload is None  # help text, not JSON — the documented exception
    assert "Usage" in result.out


def test_nothing_else_writes_prose_to_stdout(run_cli):
    """Every non-help command must leave stdout machine-readable."""
    for args in JSON_COMMANDS:
        result = run_cli(*args)
        assert result.payload is not None, f"{args} put non-JSON on stdout: {result.out[:120]!r}"

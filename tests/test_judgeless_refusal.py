"""A task class with a hard target refuses calibration, at exit 2.

DECISIONS.md #12 settled that three of the four task classes have a hard target,
so nothing judges them. The failure this guards is not a crash. It is
``calibrate report`` computing a kappa between a hard label and itself, printing
a number that reads exactly like every other kappa this tool produces, and
somebody quoting it.

The refusal is asserted through a real process because the contract being kept
is a process contract: exit 2, pure JSON on stdout, prose on stderr.
"""

import json

import pytest

from langchef.core.exits import Exit
from langchef.workspace.formats import write_jsonl

CALIBRATION_COMMANDS = (
    ("label", "plan"),
    ("calibrate", "report"),
    ("calibrate", "diff"),
)


def _dataset(root, task_class: str, columns: str) -> None:
    """Point the workspace at a file somebody already owns, as #19 does."""
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "rows.csv").write_text("a,b\nx,y\n", encoding="utf-8")
    config = root / "evals" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + f'\n[dataset]\npath = "../data/rows.csv"\nclass = "{task_class}"\n{columns}\n',
        encoding="utf-8",
    )


@pytest.fixture
def judgeless(tmp_path, run_cli):
    """A workspace declaring `classification`, which has no judge."""
    code, payload, _ = run_cli("init", "--name", "hard-target", cwd=tmp_path)
    assert code == Exit.OK, payload
    _dataset(tmp_path, "classification", 'input = "a"\nlabel = "b"')
    return tmp_path


@pytest.fixture
def judged(tmp_path, run_cli):
    """The same workspace declaring `qna`, which does have a judge."""
    code, payload, _ = run_cli("init", "--name", "free-text", cwd=tmp_path)
    assert code == Exit.OK, payload
    _dataset(tmp_path, "qna", 'question = "a"\nanswer = "b"')
    return tmp_path


@pytest.mark.parametrize("command", CALIBRATION_COMMANDS)
def test_every_calibration_command_refuses_at_exit_two(judgeless, run_cli, command):
    code, payload, err = run_cli(*command, cwd=judgeless)

    assert code == Exit.REFUSED, f"{command} exited {code}, not 2: {err}"
    assert payload["ok"] is False
    assert payload["task_class"] == "classification"
    assert payload["requires_judge"] is False


@pytest.mark.parametrize("command", CALIBRATION_COMMANDS)
def test_the_refusal_names_the_class_and_what_is_still_available(judgeless, run_cli, command):
    """One line of why, and a line of what to do instead.

    A refusal that only says no sends the reader back to the docs. This one names
    the class, says why in the same sentence, and points at the three things that
    do work for a hard target.
    """
    _, payload, err = run_cli(*command, cwd=judgeless)
    message = payload["message"]

    assert message.startswith("classification has a hard target")
    assert "no judge" in message
    assert "paired comparison" in message and "detection limit" in message
    assert payload["available"] == [
        "compare",
        "experiment design",
        "experiment approve",
        "experiment readout",
    ]
    # The person reading stderr gets the same sentence, not a stack trace.
    assert "classification has a hard target" in err


@pytest.mark.parametrize("command", CALIBRATION_COMMANDS)
def test_stdout_stays_pure_json_on_the_refusal(judgeless, run_cli, command):
    """Exit 2 is a machine path. An agent parses stdout on every exit code."""
    result = run_cli(*command, cwd=judgeless)

    assert json.loads(result.out)["exit"] == int(Exit.REFUSED)
    assert result.err.strip(), "a refusal still narrates to stderr"


@pytest.mark.parametrize("command", CALIBRATION_COMMANDS)
def test_a_judged_class_is_not_refused(judged, run_cli, command):
    """`qna` declares a judge, so the gate must not fire.

    These commands still fail here, because the workspace has no runs and no
    labels yet. The assertion is that they fail for *that* reason and at exit 1,
    which is the only way to tell a working gate from one that refuses
    everything.
    """
    code, payload, err = run_cli(*command, cwd=judged)

    assert code == Exit.ERROR, f"{command} exited {code}: {err}"
    assert "task_class" not in payload
    assert "hard target" not in payload["message"]


def test_the_trace_collection_path_has_no_dataset_and_is_never_refused(tmp_path, run_cli):
    """No ``[dataset]`` table at all is the original path, judged by construction."""
    assert run_cli("init", "--name", "traces", cwd=tmp_path).code == Exit.OK
    write_jsonl(
        tmp_path / "evals" / "goldens" / "support.jsonl",
        [{"example_id": "ex-1", "question": "q", "answer": "a", "context": ["c"]}],
    )

    code, payload, _ = run_cli("calibrate", "report", cwd=tmp_path)

    assert code == Exit.ERROR
    assert "hard target" not in payload["message"]

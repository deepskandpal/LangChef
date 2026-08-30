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


def _diff_suite():
    """Thirty examples, and what an honest person says about each.

    Twelve quote the context, ten paraphrase it correctly, eight are wrong. The
    shipped rubric flags all eighteen of the paraphrases and wrong answers; a
    person only calls the eight wrong ones bad, so the ten paraphrases are false
    alarms and the revision's whole job is to stop them.
    """
    rows, labels = [], {}
    for index in range(CORRECT + PARAPHRASED + WRONG_ANSWER):
        if index < CORRECT:
            answer, human = DIFF_CONTEXT, "pass"
        elif index < CORRECT + PARAPHRASED:
            answer, human = PARAPHRASE, "pass"
        else:
            answer, human = DIFF_WRONG, "fail"
        example_id = f"ex-{index:02}"
        rows.append(
            {
                "example_id": example_id,
                "question": "Tell me the payment terms.",
                "answer": answer,
                "context": [DIFF_CONTEXT],
                "expected": "net thirty days",
                "slices": {"topic": "billing"},
            }
        )
        labels[example_id] = human
    return rows, labels


@pytest.fixture
def calibrated(tmp_path, run_cli):
    """A workspace with one scored run and a full set of human labels on it."""
    code, payload, _ = run_cli("init", "--name", "diff-test", cwd=tmp_path)
    assert code == Exit.OK, payload
    rows, labels = _diff_suite()
    write_jsonl(tmp_path / "evals" / "goldens" / "support.jsonl", rows)

    def cli(*args):
        return run_cli(*args, cwd=tmp_path)

    assert cli("approve", "rubric").code == Exit.OK
    assert cli("judge", "run", "--run-id", "base").code == Exit.OK
    assert cli("label", "plan", "--budget", "40", "--run", "base").code == Exit.OK

    todo = tmp_path / "evals" / "labels" / "answer-quality.todo.jsonl"
    write_jsonl(todo, [{**row, "verdict": labels[row["example_id"]]} for row in read_jsonl(todo)])
    assert cli("label", "import", str(todo)).code == Exit.OK
    return tmp_path


def _write_v2(workspace):
    path = workspace / "evals" / "rubrics" / "answer-quality-v2.md"
    path.write_text(RUBRIC_V2, encoding="utf-8")
    return path


DIFF_CONTEXT = (
    "Payment terms on every Northwind invoice are net thirty days, payable one month from receipt."
)
PARAPHRASE = "Payable one month from receipt."
DIFF_WRONG = "Payment is due immediately on receipt."
CORRECT, PARAPHRASED, WRONG_ANSWER = 12, 10, 8

RUBRIC_V2 = """# Answer quality, revised

Correctness has been dropped: the judge was reading it as word containment and
flagging correct paraphrases. Whether that helped is what `calibrate diff` says.

### Groundedness

Every claim in the answer is supported by the retrieved context.

### Directness

The answer answers rather than declining.
"""


def _write_v2(workspace):
    path = workspace / "evals" / "rubrics" / "answer-quality-v2.md"
    path.write_text(RUBRIC_V2, encoding="utf-8")
    return path


def test_calibrate_diff_reports_the_delta_a_rubric_revision_bought(calibrated, run_cli):
    def cli(*args):
        return run_cli(*args, cwd=calibrated)

    code, before, _ = cli("calibrate", "report", "--run", "base")
    assert code == Exit.OK
    assert before["confusion"] == {"tp": 8, "fp": 10, "fn": 0, "tn": 12}

    _write_v2(calibrated)
    code, payload, err = cli("calibrate", "diff", "--run", "base", "--rubric", "answer-quality-v2")
    assert code == Exit.OK, payload

    # Both hashes on the record: a delta between two unnamed rubrics is unusable.
    assert payload["rubric"]["before"] == before["pin"]["rubric"]
    assert payload["rubric"]["after"].startswith("answer-quality-v2@")
    assert payload["rubric"]["before"] != payload["rubric"]["after"]
    assert payload["approved"] == {"before": True, "after": False}

    # Ten false alarms stop, nothing else moves.
    assert payload["movement"]["false_alarms_fixed"] == PARAPHRASED
    assert payload["movement"]["misses_introduced"] == 0
    assert payload["n"] == CORRECT + PARAPHRASED + WRONG_ANSWER

    assert payload["kappa"]["after"] > payload["kappa"]["before"]
    assert payload["kappa"]["interval"]["lo"] > 0
    assert payload["verdict"] == "improved"
    assert payload["pairing"] == "paired"

    # Both statistics, each with an interval — the acceptance criteria, literally.
    for part in ("kappa", "tpr", "tnr"):
        assert {"lo", "hi", "level"} <= set(payload[part]["interval"])
    assert payload["tnr"]["difference"] == pytest.approx(PARAPHRASED / (CORRECT + PARAPHRASED))
    assert payload["tpr"]["difference"] == 0.0

    # The taxonomy for both, so a person can see which bucket moved.
    assert payload["taxonomy"]["before"]["kinds"] == {"false_alarm": PARAPHRASED, "miss": 0}
    assert payload["taxonomy"]["after"]["kinds"] == {"false_alarm": 0, "miss": 0}

    artifact = calibrated / "evals" / "runs" / "base" / "delta.json"
    assert artifact.is_file()
    assert json.loads(artifact.read_text(encoding="utf-8"))["kappa"] == payload["kappa"]
    assert "paired" in err


def test_calibrate_diff_pays_only_for_the_new_rubric(calibrated, run_cli):
    """The cache does the work: the old verdicts are on file and the new ones stick."""

    def cli(*args):
        return run_cli(*args, cwd=calibrated)

    _write_v2(calibrated)
    scores = calibrated / "evals" / "runs" / "base" / "scores.parquet"
    original = scores.read_bytes()

    code, first, _ = cli("calibrate", "diff", "--run", "base", "--rubric", "answer-quality-v2")
    assert code == Exit.OK
    assert first["cost"]["judge_calls"] == CORRECT + PARAPHRASED + WRONG_ANSWER

    code, again, _ = cli("calibrate", "diff", "--run", "base", "--rubric", "answer-quality-v2")
    assert code == Exit.OK
    assert again["cost"]["judge_calls"] == 0
    assert again["cost"]["cache_hits"] == CORRECT + PARAPHRASED + WRONG_ANSWER
    assert again["kappa"] == first["kappa"]  # deterministic, per the contract

    # The old rubric was never re-run; its verdicts were read, not recomputed.
    assert scores.read_bytes() == original


def test_calibrate_diff_takes_an_edited_rubric_without_a_fresh_approval(calibrated, run_cli):
    """Deliberately outside gate one: this is the evidence approval rests on."""

    def cli(*args):
        return run_cli(*args, cwd=calibrated)

    rubric = calibrated / "evals" / "rubrics" / "answer-quality.md"
    rubric.write_text(RUBRIC_V2, encoding="utf-8")
    # The edit has revoked the approval, and scoring is refused because of it.
    assert cli("judge", "run", "--run-id", "after").code == Exit.REFUSED

    code, payload, err = cli("calibrate", "diff", "--run", "base")
    assert code == Exit.OK, payload
    assert payload["approved"]["after"] is False
    assert payload["movement"]["false_alarms_fixed"] == PARAPHRASED
    assert "not approved" in err


def test_calibrate_diff_refuses_at_exit_5_when_the_model_pin_moved(calibrated, run_cli):
    """A rubric delta across a model change measures the model as much as the rubric."""
    _write_v2(calibrated)
    config = calibrated / "evals" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'cheap_model = "containment/v2"', 'cheap_model = "containment/v3"'
        ),
        encoding="utf-8",
    )

    code, payload, err = run_cli(
        "calibrate", "diff", "--run", "base", "--rubric", "answer-quality-v2", cwd=calibrated
    )
    assert code == Exit.PIN_MISMATCH
    assert payload["moved"] == {"cheap_model": ["containment/v2", "containment/v3"]}
    assert "rubric" not in payload["moved"]  # the rubric is the thing being changed
    assert "measures nothing" in err
    assert not (calibrated / "evals" / "runs" / "base" / "delta.json").exists()


def test_calibrate_diff_refuses_a_rubric_that_did_not_move(calibrated, run_cli):
    code, payload, _ = run_cli("calibrate", "diff", "--run", "base", cwd=calibrated)
    assert code == Exit.ERROR
    assert "nothing to diff" in payload["message"]


def test_calibrate_diff_without_labels_says_what_to_run(workspace, run_cli):
    assert run_cli("approve", "rubric", cwd=workspace).code == Exit.OK
    assert run_cli("judge", "run", "--arm", "baseline", "--run-id", "b", cwd=workspace).code == 0
    code, payload, _ = run_cli("calibrate", "diff", "--run", "b", cwd=workspace)
    assert code == Exit.ERROR
    assert "langchef label plan" in payload["message"]


def test_calibrate_diff_keeps_the_two_streams_apart(calibrated, run_cli):
    """DECISIONS.md #3, on the newest command rather than only the oldest."""
    _write_v2(calibrated)
    result = run_cli(
        "calibrate", "diff", "--run", "base", "--rubric", "answer-quality-v2", cwd=calibrated
    )
    assert result.code == Exit.OK
    assert json.loads(result.out)["verdict"] == "improved"
    assert result.err.strip()
    assert "kappa" in result.err and "{" not in result.err


def test_calibrate_diff_files_a_note_rather_than_a_calibration(calibrated, run_cli):
    """An unapproved candidate's kappa must never become a memo's headline."""

    def cli(*args):
        return run_cli(*args, cwd=calibrated)

    assert cli("calibrate", "report", "--run", "base").code == Exit.OK
    _write_v2(calibrated)
    assert cli("calibrate", "diff", "--run", "base", "--rubric", "answer-quality-v2").code == 0

    code, ledger, _ = cli("ledger", "query", "--limit", "50")
    assert code == Exit.OK
    entries = ledger["entries"]
    notes = [e for e in entries if e.get("what") == "calibration-delta"]
    assert len(notes) == 1 and notes[0]["kind"] == "note"
    # The most recent calibration entry is still the approved rubric's.
    calibrations = [e for e in entries if e["kind"] == "calibration"]
    assert calibrations and calibrations[0]["kappa"] == pytest.approx(
        json.loads(
            (calibrated / "evals" / "runs" / "base" / "calibration.json").read_text(
                encoding="utf-8"
            )
        )["kappa"]
    )

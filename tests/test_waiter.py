"""M4.5 — the pre-registration store, and gate two through the CLI.

The point of gate two is that it refuses. These tests are mostly about the
refusals: an unapproved design, a design edited after approval, a run that did
not finish, and a budget that ran out mid-run.
"""

import numpy as np
import pytest

from langchef.core import design
from langchef.core.exits import Exit
from langchef.workspace import experiments as store
from langchef.workspace import scaffold
from langchef.workspace.formats import read_json, write_jsonl
from langchef.workspace.paths import WORKSPACE_DIR, Workspace

CONTEXT = "Payment terms on every Northwind invoice are net thirty days."
WRONG = "Payment is due immediately on receipt."
SIZE = 30


def golden(example_id, answer):
    return {
        "example_id": example_id,
        "question": "Tell me the payment terms.",
        "answer": answer,
        "context": [CONTEXT],
        "expected": "net thirty days",
        "slices": {"topic": "billing"},
    }


def suite(correct):
    return [golden(f"ex-{i:02}", CONTEXT if i < correct else WRONG) for i in range(SIZE)]


# --- the store ----------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path):
    ws = Workspace(tmp_path / WORKSPACE_DIR)
    scaffold.create(ws, name="waiter-test")
    return ws


def test_a_preregistration_round_trips_as_reviewable_toml(workspace):
    written = store.write(
        workspace,
        "exp-1",
        {
            "kind": "superiority",
            "n": 90,
            "mde": 0.13,
            "guardrails": ["one", "two"],
            "cost": {"judge_calls": 53, "usd": None},
        },
    )
    text = written.path.read_text(encoding="utf-8")
    assert "[experiment]" in text and "[cost]" in text
    assert "# LangChef pre-registration." in text  # a person is meant to read this

    reloaded = store.load(workspace, "exp-1")
    assert reloaded.design["n"] == 90
    assert reloaded.design["guardrails"] == ["one", "two"]
    assert reloaded.design["cost"]["judge_calls"] == 53
    assert not reloaded.approved


def test_writing_over_an_existing_preregistration_is_refused(workspace):
    store.write(workspace, "exp-1", {"n": 10})
    with pytest.raises(store.ExperimentError, match="already exists"):
        store.write(workspace, "exp-1", {"n": 20})


def test_approval_sticks_and_an_edit_revokes_it(workspace):
    store.write(workspace, "exp-1", {"kind": "superiority", "n": 90, "margin": 0.03})
    approved = store.approve(workspace, "exp-1")
    assert approved.approved
    before = approved.digest

    text = approved.path.read_text(encoding="utf-8")
    approved.path.write_text(text.replace("margin = 0.03", "margin = 0.15"), encoding="utf-8")

    after = store.load(workspace, "exp-1")
    assert after.digest != before
    assert not after.approved  # no revoke command needed; it stops matching


def test_a_null_cannot_be_written_into_a_preregistration(workspace):
    with pytest.raises(store.ExperimentError, match="cannot contain a null"):
        store.write(workspace, "exp-1", {"cost": {"usd": None, "note": [None]}})


# --- gate two, through the CLI -------------------------------------------------


@pytest.fixture
def project(tmp_path, run_cli):
    assert run_cli("init", "--name", "waiter", cwd=tmp_path).code == Exit.OK
    evals = tmp_path / "evals"
    write_jsonl(evals / "goldens" / "support.baseline.jsonl", suite(correct=24))
    write_jsonl(evals / "goldens" / "support.variant.jsonl", suite(correct=18))
    assert run_cli("approve", "rubric", cwd=tmp_path).code == Exit.OK
    assert run_cli("judge", "run", "--arm", "baseline", "--run-id", "base", cwd=tmp_path).code == 0
    assert run_cli("baseline", "set", "--run", "base", cwd=tmp_path).code == Exit.OK
    return tmp_path


def test_the_waiter_proposes_before_anything_runs(project, run_cli):
    code, payload, _ = run_cli(
        "experiment",
        "design",
        "--intent",
        "is the variant better",
        "--variant-arm",
        "variant",
        "--target-effect",
        "0.02",
        "--id",
        "e1",
        cwd=project,
    )
    assert code == Exit.OK
    assert payload["approved"] is False
    names = [c["name"] for c in payload["candidates"]]
    assert names == ["as-it-stands", "powered"]  # 30 goldens cannot resolve 2 points
    assert payload["candidates"][1]["n"] > payload["candidates"][0]["n"]
    assert (project / "evals" / "experiments" / "e1.toml").is_file()


def test_readout_refuses_an_unapproved_design(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    assert run_cli("judge", "run", "--arm", "variant", "--run-id", "var", cwd=project).code == 0

    code, payload, _ = run_cli("experiment", "readout", "e1", "--variant", "var", cwd=project)
    assert code == Exit.REFUSED
    assert "has not been approved" in payload["message"]


def test_the_full_gated_readout(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "is the variant better",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    assert run_cli("experiment", "approve", "e1", cwd=project).code == Exit.OK
    assert run_cli("judge", "run", "--arm", "variant", "--run-id", "var", cwd=project).code == 0

    code, checked, _ = run_cli("experiment", "check", "e1", "--variant", "var", cwd=project)
    assert checked["ok"] and checked["violations"] == []

    code, payload, _ = run_cli("experiment", "readout", "e1", "--variant", "var", cwd=project)
    assert code == Exit.OK
    assert payload["pre_registered"] is True
    assert payload["exploratory"] is False
    assert payload["readout_verdict"] == "regression"
    assert (project / "evals" / "runs" / "var" / "readout.json").is_file()


def test_a_non_inferiority_readout_tests_the_margin_not_the_estimate(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "cheaper, quality must hold",
        "--variant-arm",
        "variant",
        "--kind",
        "non-inferiority",
        "--margin",
        "0.03",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)
    run_cli("judge", "run", "--arm", "variant", "--run-id", "var", cwd=project)

    code, payload, _ = run_cli("experiment", "readout", "e1", "--variant", "var", cwd=project)
    assert code == Exit.OK
    assert payload["kind"] == "non_inferiority"
    # A 20-point drop against a 3-point tolerance is not a close call.
    assert payload["readout_verdict"] == "failed"


def test_an_edited_design_stops_the_readout(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--kind",
        "non-inferiority",
        "--margin",
        "0.03",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)
    run_cli("judge", "run", "--arm", "variant", "--run-id", "var", cwd=project)

    path = project / "evals" / "experiments" / "e1.toml"
    path.write_text(path.read_text().replace("margin = 0.03", "margin = 0.25"), encoding="utf-8")

    code, payload, _ = run_cli("experiment", "readout", "e1", "--variant", "var", cwd=project)
    assert code == Exit.REFUSED
    assert "changed since it was approved" in payload["message"]


def test_an_override_is_recorded_as_exploratory_not_hidden(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("judge", "run", "--arm", "variant", "--run-id", "var", cwd=project)

    code, payload, _ = run_cli(
        "experiment",
        "readout",
        "e1",
        "--variant",
        "var",
        "--override",
        "looked after the fact",
        cwd=project,
    )
    assert code == Exit.OK
    assert payload["exploratory"] is True
    assert payload["pre_registered"] is False
    assert payload["override"] == "looked after the fact"


def test_a_budget_stops_the_run_and_reports_what_is_left(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--budget-calls",
        "4",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)

    # Cold cache, so every example needs a call and the ceiling bites.
    (project / "evals" / ".cache" / "judgements.jsonl").unlink(missing_ok=True)
    code, payload, _ = run_cli(
        "judge", "run", "--arm", "variant", "--run-id", "var", "--experiment", "e1", cwd=project
    )
    assert code == Exit.BUDGET
    assert payload["stats"]["provider_calls"] == 4
    assert payload["unscored"] == SIZE - 4

    undone = read_json(project / "evals" / "runs" / "var" / "undone.json")
    assert undone["scored"] + len(undone["unscored"]) == SIZE
    assert undone["remedy"]

    # And a half-finished run is not the registered design.
    code, refused, _ = run_cli("experiment", "readout", "e1", "--variant", "var", cwd=project)
    assert code == Exit.REFUSED
    assert "stopping rule" in refused["message"]


def test_a_run_records_which_experiment_it_belongs_to(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)
    assert (
        run_cli(
            "judge", "run", "--arm", "variant", "--run-id", "var", "--experiment", "e1", cwd=project
        ).code
        == 0
    )

    manifest = read_json(project / "evals" / "runs" / "var" / "run.json")
    assert manifest["experiment_id"] == "e1"
    # A run scored outside an experiment records no link rather than a wrong one.
    run_cli("judge", "run", "--arm", "variant", "--run-id", "loose", cwd=project)
    assert read_json(project / "evals" / "runs" / "loose" / "run.json")["experiment_id"] is None


def test_readout_refuses_to_choose_between_repeated_runs(project, run_cli):
    """Re-running an arm until it reads out better is what gate two is against.

    With a warm cache a re-run costs nothing, so an arm accumulates runs in
    seconds. Silently taking the newest would make that free.
    """
    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)
    for run_id in ("var-a", "var-b"):
        assert (
            run_cli(
                "judge",
                "run",
                "--arm",
                "variant",
                "--run-id",
                run_id,
                "--experiment",
                "e1",
                cwd=project,
            ).code
            == 0
        )

    code, payload, _ = run_cli("experiment", "readout", "e1", cwd=project)
    assert code == Exit.REFUSED
    assert set(payload["candidates"]) == {"var-a", "var-b"}
    assert "--variant" in payload["message"]

    # Naming one is all it takes; the refusal is about the silent choice.
    code, named, _ = run_cli("experiment", "readout", "e1", "--variant", "var-a", cwd=project)
    assert code == Exit.OK
    assert named["variant_run"] == "var-a"


def test_runs_can_be_filtered_by_experiment(project, run_cli):
    from langchef.workspace import runs as runs_mod
    from langchef.workspace.paths import find

    run_cli(
        "experiment",
        "design",
        "--intent",
        "x",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)
    run_cli(
        "judge", "run", "--arm", "variant", "--run-id", "linked", "--experiment", "e1", cwd=project
    )
    run_cli("judge", "run", "--arm", "variant", "--run-id", "unlinked", cwd=project)

    workspace = find(project)
    linked = runs_mod.for_experiment(workspace, experiment_id="e1")
    assert [r.run_id for r in linked] == ["linked"]
    assert len(runs_mod.for_experiment(workspace, arm="variant")) == 2


def test_check_reports_absence_of_runs_as_violations(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "is the variant better",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)

    res = run_cli("experiment", "check", "e1", cwd=project)
    assert res.code == Exit.OK
    assert not res.payload["ok"]
    assert "the arm was never scored" in res.payload["violations"]
    assert "the run matches the pre-registration" not in res.err


def test_check_says_matches_when_both_runs_exist_and_match(project, run_cli):
    run_cli(
        "experiment",
        "design",
        "--intent",
        "is the variant better",
        "--variant-arm",
        "variant",
        "--id",
        "e1",
        cwd=project,
    )
    run_cli("experiment", "approve", "e1", cwd=project)
    assert (
        run_cli(
            "judge", "run", "--arm", "variant", "--run-id", "var", "--experiment", "e1", cwd=project
        ).code
        == 0
    )

    res = run_cli("experiment", "check", "e1", cwd=project)
    assert res.code == Exit.OK
    assert res.payload["ok"]
    assert not res.payload["violations"]
    assert "the run matches the pre-registration" in res.err


# --- #68: sizing a continuous outcome ---------------------------------------


def test_the_continuous_limit_is_driven_by_the_spread_of_the_differences():
    """Not by either arm's own spread, which is the mistake pairing exists to avoid.

    Two arms can both vary enormously while the difference between them is
    nearly constant. Read unpaired, that experiment looks hopeless; read paired,
    it is extremely sensitive. A sizing rule that used an arm's spread would
    tell a retrieval team to collect thousands of queries they do not need.
    """
    tight = design.minimum_detectable_effect_continuous(90, sd_difference=0.02)
    loose = design.minimum_detectable_effect_continuous(90, sd_difference=0.20)

    assert tight < loose
    # Linear in the spread: ten times the spread, ten times the limit.
    assert loose == pytest.approx(tight * 10)


def test_the_continuous_limit_is_a_known_answer():
    """Checked against the closed form written out independently.

    (z_alpha + z_beta) * sd / sqrt(n). Recomputed here from scipy rather than
    reusing the module's own `_z`, so a sign or tail error in that helper cannot
    hide behind agreeing with itself.
    """
    from scipy.stats import norm

    n, sd, level, power = 120, 0.15, 0.95, 0.8
    z_alpha = norm.ppf(1 - (1 - level) / 2)
    z_beta = norm.ppf(power)
    expected = (z_alpha + z_beta) * sd / (n**0.5)

    assert design.minimum_detectable_effect_continuous(n, sd, level, power) == pytest.approx(
        expected
    )


def test_the_promised_power_is_actually_delivered():
    """The claim the number makes, tested as a rate rather than as algebra.

    `mde` says: at this n, an effect this size is caught 80% of the time. That is
    a falsifiable statement about repeated experiments, so this simulates them.
    Formula-vs-formula tests cannot catch a limit that is simply too optimistic;
    this can, and it is the check LangChef asks of its own users.
    """
    rng = np.random.default_rng(68)
    n, sd, power = 200, 0.10, 0.8
    effect = design.minimum_detectable_effect_continuous(n, sd, power=power)

    detected = 0
    trials = 600
    for _ in range(trials):
        diffs = rng.normal(effect, sd, size=n)
        # The paired interval a reader would act on: whole interval above zero.
        se = diffs.std(ddof=1) / np.sqrt(n)
        if diffs.mean() - 1.96 * se > 0:
            detected += 1

    achieved = detected / trials
    # Nominal 80%. Monte Carlo error at 600 trials is about 1.6pp, so this is a
    # real check rather than a wide-open one.
    assert 0.76 < achieved < 0.86, f"achieved power {achieved:.1%} against a nominal {power:.0%}"


def test_required_n_inverts_the_limit():
    """The two must agree, or the waiter proposes an n its own readout disowns."""
    sd, effect = 0.12, 0.03
    n = design.required_n_continuous(effect, sd)

    assert design.minimum_detectable_effect_continuous(n, sd) <= effect
    assert design.minimum_detectable_effect_continuous(n - 1, sd) > effect


def test_a_design_records_which_arithmetic_sized_it():
    """A continuous limit and a discordant one both print as a percentage.

    A reader who cannot tell them apart will compare two numbers that were never
    comparable, which is the failure `pin` exists to prevent elsewhere.
    """
    binary = design.propose("s", "is it better?", 90, "base", "var", target_effect=0.05)[0]
    continuous = design.propose(
        "s",
        "is it better?",
        90,
        "base",
        "var",
        target_effect=0.05,
        outcome="continuous",
        sd_difference=0.1,
    )[0]

    assert binary.outcome == "binary"
    assert continuous.outcome == "continuous"
    assert binary.mde != continuous.mde
    assert "sd of paired differences" in continuous.discordance_source


def test_design_refuses_an_outcome_it_cannot_size():
    """A plausible sample size is worse than no answer.

    The whole promise of the waiter is that somebody who is not a statistician
    can trust the proposal it hands them. Guessing at a shape it has no rule for
    would break that quietly, which is the worst way to break it.
    """
    with pytest.raises(design.DesignError) as caught:
        design.propose("s", "?", 90, "base", "var", outcome="ordinal")
    assert "ordinal" in str(caught.value)
    assert "will not guess" in str(caught.value)


def test_a_continuous_design_refuses_without_the_spread():
    """There is nothing to compute, and a default would be a number nobody chose."""
    with pytest.raises(design.DesignError) as caught:
        design.propose("s", "?", 90, "base", "var", outcome="continuous")
    assert "standard deviation" in str(caught.value)

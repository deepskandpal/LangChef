"""``langchef power``: arithmetic without ceremony.

The command owns no formula. These tests exist mostly to prove that: what it
prints has to be what ``core/design.py`` computes, and what ``experiment design``
would have said, or the two answers drift and a person gets a different number
depending on which door they came through.
"""

from __future__ import annotations

import json

import pytest

from langchef.core import design
from langchef.core.exits import Exit


def test_power_needs_no_workspace(run_cli, tmp_path):
    """The whole point. Requiring a workspace to do arithmetic is the ceremony
    this command exists to remove, and `tmp_path` here is deliberately empty."""
    result = run_cli("power", "--n", "90", cwd=tmp_path)

    assert result.code == Exit.OK
    assert result.payload["n"] == 90
    assert result.payload["mde"] > 0


def test_it_reports_the_same_limit_as_the_designer(run_cli, tmp_path):
    """One formula, two doors.

    If this command computed its own detection limit, the two would drift and a
    person would get a different answer depending on whether they asked before
    or during a design. The issue asked for no second implementation; this is
    what enforces it.
    """
    result = run_cli("power", "--n", "90", cwd=tmp_path)

    rate, _ = design.estimate_discordance(None, None)
    expected = design.minimum_detectable_effect(90, rate)

    assert result.payload["mde"] == pytest.approx(round(expected, 6))


def test_evidence_beats_the_default(run_cli, tmp_path):
    """A rate this workspace actually observed is a better prior than our guess.

    And it must be visible: `basis` names where the number came from, because a
    detection limit computed from an assumed flip rate and one computed from a
    measured rate are different claims that print identically.
    """
    assumed = run_cli("power", "--n", "90", cwd=tmp_path)
    observed = run_cli("power", "--n", "90", "--discordant", "18", "--prior-n", "90", cwd=tmp_path)

    assert "assumed default" in assumed.payload["basis"]
    assert "18/90" in observed.payload["basis"]
    assert observed.payload["mde"] != assumed.payload["mde"]


def test_a_continuous_score_is_sized_as_one(run_cli, tmp_path):
    """Supplying --sd selects the continuous arithmetic (#68, DECISIONS #12).

    A continuous limit and a discordant one both print as a percentage, so the
    payload names which was used. Without that a reader compares two numbers
    that were never comparable.
    """
    result = run_cli("power", "--n", "200", "--sd", "0.10", cwd=tmp_path)

    assert result.payload["outcome"] == "continuous"
    assert result.payload["mde"] == pytest.approx(
        round(design.minimum_detectable_effect_continuous(200, 0.10), 6)
    )
    assert "sd of paired differences" in result.payload["basis"]


def test_a_shortfall_is_a_number_not_a_shrug(run_cli, tmp_path):
    """ "You need 628 and have 90" is an answer. "Not enough" is not.

    The shortfall and the required n are on stdout rather than only in prose,
    because an agent reads stdout and this is the number it would otherwise have
    to derive.
    """
    result = run_cli("power", "--n", "90", "--effect", "0.05", cwd=tmp_path)

    assert result.payload["required_n"] == design.required_n(
        0.05, design.estimate_discordance(None, None)[0]
    )
    assert result.payload["shortfall"] == result.payload["required_n"] - 90
    assert result.payload["runnable_now"] is False


def test_a_horizon_is_only_offered_when_a_rate_is_known(run_cli, tmp_path):
    """A horizon invented from a default collection rate is a date in a plan.

    So it is None unless the caller said how fast examples arrive.
    """
    without = run_cli("power", "--n", "90", "--effect", "0.05", cwd=tmp_path)
    with_rate = run_cli("power", "--n", "90", "--effect", "0.05", "--per-week", "40", cwd=tmp_path)

    assert without.payload["horizon_weeks"] is None
    assert with_rate.payload["horizon_weeks"] == pytest.approx(
        round(with_rate.payload["shortfall"] / 40, 1)
    )


def test_a_reachable_target_says_so(run_cli, tmp_path):
    """The happy path has to be legible too, or nobody trusts the unhappy one."""
    result = run_cli("power", "--n", "5000", "--effect", "0.05", cwd=tmp_path)

    assert result.payload["runnable_now"] is True
    assert result.payload["shortfall"] == 0


@pytest.mark.parametrize(
    "args, reason",
    [
        (("--n", "0"), "nothing to size"),
        (("--n", "90", "--effect", "0"), "an effect of zero is not a question"),
        (("--n", "90", "--sd", "-1"), "a negative spread is not a spread"),
    ],
)
def test_nonsense_is_refused_rather_than_computed(run_cli, tmp_path, args, reason):
    """Each of these would otherwise produce a number, and a number gets quoted."""
    result = run_cli("power", *args, cwd=tmp_path)
    assert result.code == Exit.ERROR, reason


def test_stdout_stays_pure_json(run_cli, tmp_path):
    """The contract has no --format flag and this command must not become one."""
    result = run_cli("power", "--n", "90", cwd=tmp_path)

    assert json.loads(result.out)["n"] == 90
    assert result.err  # the prose went to stderr, where it belongs

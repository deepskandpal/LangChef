"""M4.5 — the arithmetic behind a proposed experiment."""

import pytest

from langchef.core.agreement import Interval
from langchef.core.compare import minimum_detectable_effect as mde_after
from langchef.core.design import (
    DesignError,
    estimate_cost,
    estimate_discordance,
    minimum_detectable_effect,
    non_inferiority_verdict,
    propose,
    required_n,
)


def test_design_time_and_readout_time_mde_agree():
    """Planning and reporting must use the same formula or the plan is a lie.

    ``compare`` reports the detection limit from the flip rate it observed;
    ``design`` predicts it from the flip rate it assumed. Feed the same rate to
    both and they have to land in the same place.
    """
    n, discordant = 200, 40
    predicted = minimum_detectable_effect(n, discordant / n)
    observed = mde_after(n, discordant)
    # compare() takes the upper interval bound of the rate, so it is the more
    # conservative of the two; they should still be within a few points.
    assert predicted == pytest.approx(observed, rel=0.25)


def test_required_n_inverts_the_detection_limit():
    for effect in (0.02, 0.05, 0.10):
        n = required_n(effect, discordance=0.2)
        assert minimum_detectable_effect(n, 0.2) == pytest.approx(effect, rel=0.02)


def test_detecting_a_smaller_effect_costs_quadratically():
    """Halving the effect you want to see needs roughly four times the goldens."""
    assert required_n(0.05, 0.2) / required_n(0.10, 0.2) == pytest.approx(4.0, rel=0.02)


def test_a_zero_or_negative_target_is_refused():
    with pytest.raises(DesignError, match="greater than zero"):
        required_n(0.0, 0.2)


def test_evidence_beats_the_default_discordance():
    assumed, why = estimate_discordance(None, None)
    assert assumed == 0.2 and "assumed" in why

    observed, why = estimate_discordance(prior_discordant=10, prior_n=200)
    assert "prior run" in why
    # The upper bound of the observed rate, not the point estimate: under-
    # estimating the flip rate under-powers the design.
    assert 0.05 < observed < 0.12


def test_cost_admits_when_it_cannot_price_a_call():
    free = estimate_cost(n=100, cached=40, price_per_call_usd=None)
    assert free.judge_calls == 60
    assert free.usd is None
    assert "no price configured" in free.price_note

    priced = estimate_cost(n=100, cached=40, price_per_call_usd=0.01)
    assert priced.usd == pytest.approx(0.60)


def test_escalated_examples_are_charged_twice():
    assert estimate_cost(n=100, escalation_rate=0.0).judge_calls == 100
    assert estimate_cost(n=100, escalation_rate=0.25).judge_calls == 125


def test_non_inferiority_needs_its_margin_up_front():
    with pytest.raises(DesignError, match="needs --margin"):
        propose(
            suite="s",
            intent="cheaper model",
            n_available=90,
            baseline_arm="baseline",
            variant_arm="cheap",
            kind="non_inferiority",
        )


def test_the_three_non_inferiority_outcomes():
    # Whole interval clears the margin.
    assert non_inferiority_verdict(Interval(-0.01, 0.03), margin=0.03) == "held"
    # Whole interval is past it.
    assert non_inferiority_verdict(Interval(-0.28, -0.12), margin=0.03) == "failed"
    # Straddles it — the run cannot tell, which is not permission to ship.
    assert non_inferiority_verdict(Interval(-0.05, 0.02), margin=0.03) == "unresolved"


def test_one_candidate_when_the_goldens_can_resolve_the_effect():
    designs = propose(
        suite="s",
        intent="big change",
        n_available=4000,
        baseline_arm="baseline",
        variant_arm="v",
        target_effect=0.10,
    )
    assert [d.name for d in designs] == ["as-it-stands"]
    assert designs[0].mde < 0.10


def test_a_second_candidate_appears_when_they_cannot():
    designs = propose(
        suite="s",
        intent="small change",
        n_available=90,
        baseline_arm="baseline",
        variant_arm="v",
        target_effect=0.03,
    )
    assert [d.name for d in designs] == ["as-it-stands", "powered"]
    at_hand, powered = designs
    assert at_hand.mde > 0.03
    assert powered.n > at_hand.n
    assert powered.mde == pytest.approx(0.03, rel=0.05)
    assert any("cannot resolve" in c for c in at_hand.caveats)
    assert any("more golden" in c for c in powered.caveats)


def test_the_design_says_what_it_assumed():
    design = propose(
        suite="s",
        intent="x",
        n_available=90,
        baseline_arm="b",
        variant_arm="v",
        discordance=0.31,
        discordance_source="observed in a prior run (28/90)",
    )[0]
    payload = design.to_dict()
    assert payload["discordance_assumed"] == 0.31
    assert "prior run" in payload["discordance_source"]
    assert "No interim looks" in payload["stopping_rule"]


def test_an_empty_suite_cannot_be_designed_over():
    with pytest.raises(DesignError, match="no goldens"):
        propose(suite="s", intent="x", n_available=0, baseline_arm="b", variant_arm="v")


def test_unknown_kinds_are_refused():
    with pytest.raises(DesignError, match="unknown experiment kind"):
        propose(
            suite="s", intent="x", n_available=10, baseline_arm="b", variant_arm="v", kind="vibes"
        )

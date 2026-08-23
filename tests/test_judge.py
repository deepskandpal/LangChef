"""M2 — rubrics, the provider shim, the cache, and two-tier judging."""

import json
from dataclasses import dataclass

import pytest

from langchef.judge.cache import Cache, judgement_key, prompt_key
from langchef.judge.example import Example
from langchef.judge.providers import (
    ContainmentProvider,
    Judgement,
    ProviderError,
    ReplayProvider,
    build_prompt,
    parse_reply,
    resolve,
)
from langchef.judge.rubric import RubricError, parse
from langchef.judge.runner import Pin, PinMismatch, check_pin, run

RUBRIC_TEXT = """# Answer quality

### Correctness

The answer states the fact asked for.

### Groundedness

Every claim is supported by the retrieved context.

### Directness

The answer answers.
"""

RUBRIC = parse(RUBRIC_TEXT, "answer-quality")


def example(answer, expected="net thirty days", context=("Payment terms are net thirty days.",)):
    return Example(
        example_id="ex-1",
        question="Tell me the payment terms.",
        answer=answer,
        context=context,
        expected=expected,
    )


# --- rubrics -----------------------------------------------------------------


def test_criteria_are_the_headings():
    assert RUBRIC.criteria == ("Correctness", "Groundedness", "Directness")


def test_a_rubric_without_criteria_is_refused():
    with pytest.raises(RubricError, match="no criteria"):
        parse("# Title\n\nSome prose but no headings.\n", "bad")
    with pytest.raises(RubricError, match="empty"):
        parse("   ", "bad")


def test_editing_a_rubric_changes_its_hash():
    """The mechanism behind the approval gate and the cache key."""
    edited = parse(RUBRIC_TEXT + "\nOne more sentence.\n", "answer-quality")
    assert edited.digest != RUBRIC.digest
    assert edited.ref.startswith("answer-quality@")


# --- the deterministic judge -------------------------------------------------


def test_a_correct_grounded_answer_passes():
    verdict = ContainmentProvider().judge(example("Payment terms are net thirty days."), RUBRIC)
    assert verdict.verdict == "pass"
    assert verdict.criterion is None


def test_a_wrong_answer_fails_on_correctness():
    verdict = ContainmentProvider().judge(example("Payment terms are due on receipt."), RUBRIC)
    assert verdict.verdict == "fail"
    assert verdict.criterion == "Correctness"


def test_a_hedge_fails_on_directness():
    verdict = ContainmentProvider().judge(example("I don't know."), RUBRIC)
    assert verdict.verdict == "fail"
    assert verdict.criterion == "Directness"


def test_an_ungrounded_answer_fails_even_when_it_is_right():
    """A lucky guess on a retrieval system is still a defect."""
    verdict = ContainmentProvider().judge(
        example("Net thirty days, invoiced monthly by our Leeds office.", context=("Unrelated.",)),
        RUBRIC,
    )
    assert verdict.verdict == "fail"
    assert verdict.criterion in ("Groundedness", "Correctness")


def test_the_judge_reports_which_criteria_it_can_assess():
    covered = ContainmentProvider().criteria_covered(RUBRIC)
    assert set(covered) == {"Correctness", "Groundedness", "Directness"}
    narrow = parse("### Tone\n\nBe warm.\n", "tone")
    assert ContainmentProvider().criteria_covered(narrow) == []


# --- replies and cassettes ---------------------------------------------------


def test_a_model_reply_is_parsed_including_fenced_json():
    body = '{"verdict": "fail", "criterion": "Correctness", "confidence": 0.9, "rationale": "no"}'
    for reply in (body, f"```json\n{body}\n```"):
        parsed = parse_reply(reply, "ex-1", "some/model")
        assert parsed.verdict == "fail"
        assert parsed.criterion == "Correctness"
        assert parsed.confidence == pytest.approx(0.9)


def test_an_unreadable_or_invalid_reply_is_an_error_not_a_guess():
    with pytest.raises(ProviderError, match="did not return JSON"):
        parse_reply("I think it's fine, honestly.", "ex-1", "some/model")
    with pytest.raises(ProviderError, match="expected 'pass' or 'fail'"):
        parse_reply('{"verdict": "maybe"}', "ex-1", "some/model")


def test_replay_plays_back_and_refuses_to_invent(tmp_path):
    subject = example("Payment terms are net thirty days.")
    prompt = build_prompt(subject, RUBRIC)
    cassettes = tmp_path / "cassettes.json"
    cassettes.write_text(
        json.dumps(
            {
                prompt_key(prompt, "some/model"): json.dumps(
                    {"verdict": "pass", "criterion": None, "confidence": 1.0, "rationale": "ok"}
                )
            }
        )
    )
    provider = ReplayProvider(cassettes=cassettes)
    assert provider.judge(subject, RUBRIC, "some/model").verdict == "pass"

    with pytest.raises(ProviderError, match="no cassette"):
        provider.judge(example("Something else entirely."), RUBRIC, "some/model")


def test_unknown_providers_are_named_in_the_error():
    with pytest.raises(ProviderError, match="unknown provider"):
        resolve("gpt-vibes")


# --- the cache ---------------------------------------------------------------


def test_the_cache_misses_then_hits(tmp_path):
    cache = Cache(tmp_path / "j.jsonl")
    subject = example("Payment terms are net thirty days.")
    key = judgement_key(subject, RUBRIC, "m", "cheap")
    assert cache.get(key) is None

    verdict = ContainmentProvider().judge(subject, RUBRIC)
    cache.put(key, verdict, "cheap", RUBRIC.ref)

    reopened = Cache(tmp_path / "j.jsonl")
    assert reopened.get(key).verdict == verdict.verdict
    assert reopened.size == 1


def test_the_key_moves_with_anything_that_could_change_the_verdict():
    subject = example("Payment terms are net thirty days.")
    base = judgement_key(subject, RUBRIC, "m", "cheap")
    edited_rubric = parse(RUBRIC_TEXT + "\nAlso be brief.\n", "answer-quality")

    assert judgement_key(subject, edited_rubric, "m", "cheap") != base
    assert judgement_key(subject, RUBRIC, "other", "cheap") != base
    assert judgement_key(subject, RUBRIC, "m", "strong") != base

    from dataclasses import replace as dc_replace

    assert judgement_key(dc_replace(subject, answer="different"), RUBRIC, "m", "cheap") != base
    # Slices are grouping metadata, not evidence: adding one must not miss.
    assert judgement_key(dc_replace(subject, slices={"topic": "x"}), RUBRIC, "m", "cheap") == base


# --- two tiers and pins ------------------------------------------------------


@dataclass
class Unsure:
    """A provider whose cheap tier is never confident."""

    name: str = "unsure"
    calls: list = None

    def __post_init__(self):
        self.calls = []

    def judge(self, ex, rubric, model):
        self.calls.append(model)
        confident = model == "strong"
        return Judgement(
            example_id=ex.example_id,
            verdict="pass" if confident else "fail",
            confidence=0.95 if confident else 0.1,
            criterion=None,
            rationale="",
            model=model,
        )


def test_only_unsure_examples_reach_the_strong_model(tmp_path):
    batch = [example("a"), example("b")]
    batch = [Example(example_id=f"ex-{i}", question="q", answer="a") for i in range(3)]
    provider = Unsure()
    result = run(
        batch, RUBRIC, provider, "cheap", Cache(tmp_path / "c.jsonl"), strong_model="strong"
    )
    assert result.stats["escalated"] == 3
    assert provider.calls.count("strong") == 3
    assert result.verdicts() == ["pass", "pass", "pass"]  # the strong verdict wins


def test_without_a_strong_model_nothing_escalates(tmp_path):
    batch = [Example(example_id="ex-0", question="q", answer="a")]
    provider = Unsure()
    result = run(batch, RUBRIC, provider, "cheap", Cache(tmp_path / "c.jsonl"))
    assert result.stats["escalated"] == 0
    assert provider.calls == ["cheap"]


def test_a_second_run_costs_nothing(tmp_path):
    batch = [Example(example_id=f"ex-{i}", question="q", answer="a") for i in range(5)]
    path = tmp_path / "c.jsonl"
    run(batch, RUBRIC, ContainmentProvider(), "m", Cache(path))
    again = run(batch, RUBRIC, ContainmentProvider(), "m", Cache(path))
    assert again.stats["provider_calls"] == 0
    assert again.stats["cache_hits"] == 5


def test_a_moved_pin_names_what_moved():
    left = Pin(rubric="r@1", provider="containment", cheap_model="a")
    right = Pin(rubric="r@2", provider="containment", cheap_model="b")
    check_pin(left, left)
    with pytest.raises(PinMismatch) as caught:
        check_pin(left, right)
    assert set(caught.value.moved) == {"rubric", "cheap_model"}
    assert "r@1" in str(caught.value)

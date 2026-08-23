"""The one place a judgement is produced. DECISIONS.md #6.

Customers bring their own keys across providers, so breadth matters; litellm
churns, so containment matters more. No other module imports a provider SDK,
and litellm is an optional extra — the CLI, its statistics and the whole
dogfood run work with no provider package installed at all.

Three backends, and the difference between them is where the verdict comes from:

``containment``
    A deterministic non-LLM judge: does the answer carry the expected fact, is
    it grounded in the retrieved context, does it hedge. This is a real
    technique, not a placeholder — exact-match and overlap judges are what most
    teams actually run first. It is also the honest starting point for
    calibration, because it fails in ways a person can predict: paraphrase and
    synonymy. Costs nothing, needs no key, and is byte-identical on every
    machine, which is what makes it the default for the dogfood and the tests.

``replay``
    Plays back judgements recorded from a real model, keyed by prompt hash. A
    test can exercise the exact bytes a model returned without a key or a
    network, and a missing cassette is an error rather than a silent live call.

``litellm``
    The real thing, any provider litellm speaks. Lazily imported.
"""

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from langchef.core.agreement import Verdict
from langchef.judge.example import Example
from langchef.judge.rubric import Rubric

HEDGES = (
    "i don't know",
    "i do not know",
    "i'm not sure",
    "i am not sure",
    "cannot determine",
    "can't determine",
    "no information",
    "unable to answer",
    "as an ai",
)
WORD = re.compile(r"[a-z0-9']+")
STOPWORDS = frozenset(
    # Content words carry the judgement; these would inflate every overlap score.
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
    }
)
GROUNDED_THRESHOLD = 0.75
CONTAINMENT_THRESHOLD = 0.6

# Criterion names are matched to checks by substring, in this order. A criterion
# that matches nothing is skipped rather than guessed at, and `criteria_covered`
# reports the gap — a judge quietly ignoring half a rubric while still returning
# a verdict is exactly what calibration is meant to expose.
#
# Changing any of this changes what a verdict means, so it also has to change the
# version in the model string below: the model is part of the cache key, and a
# judge that reasons differently under the same name would serve stale verdicts.
HEDGE_KEYS = ("hedg", "refus", "abstain", "direct")
GROUNDED_KEYS = ("ground", "faithful", "hallucin")
CORRECT_KEYS = ("correct", "accur", "answer")
VERSION = "containment/v2"


class ProviderError(RuntimeError):
    """A backend could not produce a judgement."""


@dataclass(frozen=True)
class Judgement:
    """One scored example, before it is paired with anything."""

    example_id: str
    verdict: Verdict
    confidence: float
    criterion: str | None
    rationale: str
    model: str

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "criterion": self.criterion,
            "rationale": self.rationale,
            "model": self.model,
        }


class Provider(Protocol):
    """What the runner needs from a backend."""

    name: str

    def judge(self, example: Example, rubric: Rubric, model: str) -> Judgement: ...


def _words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOPWORDS}


def _overlap(needle: set[str], haystack: set[str]) -> float:
    """Share of ``needle`` present in ``haystack``. 1.0 when nothing is needed."""
    return len(needle & haystack) / len(needle) if needle else 1.0


@dataclass
class ContainmentProvider:
    """A deterministic judge built from token overlap.

    Each rubric criterion is matched to a check by name. A criterion this judge
    has no check for is skipped rather than guessed at, and ``criteria_covered``
    reports what it could actually assess — a judge quietly ignoring half a
    rubric while reporting a verdict is precisely the failure calibration is
    supposed to expose.
    """

    name: str = "containment"

    def judge(self, example: Example, rubric: Rubric, model: str = VERSION) -> Judgement:
        answer = _words(example.answer)
        context = _words(" ".join(example.context))
        expected = _words(example.expected or "")
        lowered = example.answer.lower().strip()

        # A declined answer is a Directness failure and nothing else. Correctness
        # and Groundedness are vacuous on an answer that was never given, so
        # citing either of them would send a reader to fix the wrong thing.
        hedged = any(phrase in lowered for phrase in HEDGES) or not lowered
        hedge_criterion = next(
            (c for c in rubric.criteria if any(k in c.lower() for k in HEDGE_KEYS)), None
        )
        if hedged and hedge_criterion:
            return Judgement(
                example_id=example.example_id,
                verdict="fail",
                confidence=1.0,
                criterion=hedge_criterion,
                rationale="the answer declines to answer",
                model=model,
            )

        checks: list[tuple[str, bool, float, str]] = []
        for criterion in rubric.criteria:
            key = criterion.lower()
            if any(k in key for k in HEDGE_KEYS):
                checks.append((criterion, not hedged, 0.0 if hedged else 1.0, "answered directly"))
            elif any(k in key for k in GROUNDED_KEYS):
                score = _overlap(answer - expected, context) if context else 1.0
                checks.append(
                    (
                        criterion,
                        score >= GROUNDED_THRESHOLD,
                        score,
                        f"{score:.0%} of the answer's content words appear in "
                        "the retrieved context",
                    )
                )
            elif any(k in key for k in CORRECT_KEYS):
                score = _overlap(expected, answer)
                checks.append(
                    (
                        criterion,
                        score >= CONTAINMENT_THRESHOLD,
                        score,
                        f"{score:.0%} of the expected answer's content words are present",
                    )
                )

        failed = [c for c in checks if not c[1]]
        if failed:
            criterion, _, score, why = min(failed, key=lambda c: c[2])
            return Judgement(
                example_id=example.example_id,
                verdict="fail",
                confidence=float(min(1.0, 1.0 - score)),
                criterion=criterion,
                rationale=why,
                model=model,
            )
        margin = min((c[2] for c in checks), default=1.0)
        return Judgement(
            example_id=example.example_id,
            verdict="pass",
            confidence=float(margin),
            criterion=None,
            rationale="every checked criterion held",
            model=model,
        )

    def criteria_covered(self, rubric: Rubric) -> list[str]:
        """Which of a rubric's criteria this judge can actually assess."""
        keys = HEDGE_KEYS + GROUNDED_KEYS + CORRECT_KEYS
        return [c for c in rubric.criteria if any(k in c.lower() for k in keys)]


PROMPT = """You are grading one answer against a rubric. Reply with JSON only.

RUBRIC ({rubric_ref})
{rubric_text}

QUESTION
{question}

RETRIEVED CONTEXT
{context}

ANSWER
{answer}

Reply with exactly this JSON object and nothing else:
{{"verdict": "pass" | "fail", "criterion": "<the ### heading you are citing, or null>", "confidence": <0.0-1.0>, "rationale": "<one sentence>"}}
"""  # noqa: E501 - the prompt is sent verbatim and is the cassette key; wrapping changes both


def build_prompt(example: Example, rubric: Rubric) -> str:
    """The exact text sent to a model. Also the cassette key, so it is pure."""
    return PROMPT.format(
        rubric_ref=rubric.ref,
        rubric_text=rubric.text.strip(),
        question=example.question,
        context="\n".join(f"- {c}" for c in example.context) or "(none retrieved)",
        answer=example.answer,
    )


def parse_reply(reply: str, example_id: str, model: str) -> Judgement:
    """Turn a model's JSON into a judgement, or say why it could not be read."""
    text = reply.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"{model} did not return JSON: {reply[:200]!r}") from exc

    verdict = str(raw.get("verdict", "")).lower().strip()
    if verdict not in ("pass", "fail"):
        raise ProviderError(f"{model} returned verdict {verdict!r}, expected 'pass' or 'fail'")
    try:
        confidence = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    criterion = raw.get("criterion")
    return Judgement(
        example_id=example_id,
        verdict=verdict,  # type: ignore[arg-type]
        confidence=max(0.0, min(1.0, confidence)),
        criterion=str(criterion) if criterion else None,
        rationale=str(raw.get("rationale", "")).strip(),
        model=model,
    )


@dataclass
class ReplayProvider:
    """Plays back recorded model replies. A miss is an error, never a live call."""

    cassettes: Path
    name: str = "replay"
    recorded: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cassettes.is_file():
            self.recorded = json.loads(self.cassettes.read_text(encoding="utf-8"))

    def judge(self, example: Example, rubric: Rubric, model: str) -> Judgement:
        from langchef.judge.cache import prompt_key

        key = prompt_key(build_prompt(example, rubric), model)
        if key not in self.recorded:
            raise ProviderError(
                f"no cassette for {example.example_id} under {model} (key {key}). "
                f"Record one with LANGCHEF_RECORD=1, or run with --provider containment."
            )
        return parse_reply(self.recorded[key], example.example_id, model)


@dataclass
class LiteLLMProvider:
    """Any provider litellm speaks. Imported lazily so the extra stays optional."""

    name: str = "litellm"
    temperature: float = 0.0
    record_to: Path | None = None

    def judge(self, example: Example, rubric: Rubric, model: str) -> Judgement:
        try:
            import litellm
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on the extra
            raise ProviderError(
                "litellm is not installed. Either `uv sync --extra providers`, "
                "or use --provider containment, which needs no model at all."
            ) from exc

        prompt = build_prompt(example, rubric)
        try:  # pragma: no cover - needs a network and a key
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            reply = response["choices"][0]["message"]["content"]
        except Exception as exc:  # pragma: no cover - provider failures are opaque
            raise ProviderError(f"{model}: {exc}") from exc

        if self.record_to is not None:  # pragma: no cover - recording needs a key
            self._record(prompt, model, reply)
        return parse_reply(reply, example.example_id, model)

    def _record(self, prompt: str, model: str, reply: str) -> None:  # pragma: no cover
        from langchef.judge.cache import prompt_key

        self.record_to.parent.mkdir(parents=True, exist_ok=True)
        existing = (
            json.loads(self.record_to.read_text(encoding="utf-8"))
            if self.record_to.is_file()
            else {}
        )
        existing[prompt_key(prompt, model)] = reply
        self.record_to.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")


def resolve(name: str, cassettes: Path | None = None) -> Provider:
    """Pick a backend by name."""
    if name == "containment":
        return ContainmentProvider()
    if name == "replay":
        if cassettes is None:
            raise ProviderError("the replay provider needs a cassette file")
        return ReplayProvider(cassettes=cassettes)
    if name == "litellm":
        record = os.environ.get("LANGCHEF_RECORD_TO")
        return LiteLLMProvider(record_to=Path(record) if record else None)
    raise ProviderError(f"unknown provider {name!r}: expected containment, replay or litellm")


def names() -> tuple[str, ...]:
    return ("containment", "replay", "litellm")


def judge_all(
    provider: Provider, examples: Iterable[Example], rubric: Rubric, model: str
) -> list[Judgement]:
    """Score a batch. The runner adds caching and tiering on top of this."""
    return [provider.judge(example, rubric, model) for example in examples]

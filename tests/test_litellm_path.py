"""Issue #31 — the litellm path, executed.

``LiteLLMProvider`` is the backend every real user runs and the only one CI can
never run: there is no key on the build machine, and
``scripts/assert_no_credentials.py`` asserts there never will be, before
anything else in ``verify.sh``. So a path that carried three ``pragma: no
cover`` markers had never run once. A code path that has never executed is not a
feature, it is a hypothesis.

**The credential is not what is faked here. The socket is.** litellm hands a
module-level ``litellm.client_session`` straight to the provider SDK as its HTTP
client, so an ``httpx.MockTransport`` installed there replaces exactly one
thing — the network — and leaves every layer above it running for real:

* the request litellm assembles from our messages, model and temperature,
* the ``Authorization`` header the SDK attaches,
* litellm's parsing of the wire bytes into a ``ModelResponse``,
* the SDK's own retry loop on a 429 or a 500,
* the exception types litellm raises, and
* every line of ``LiteLLMProvider.judge``.

Mocking ``litellm.completion`` itself would prove none of that. The assertions
below are on what came out of *our* code after real litellm code carried real
recorded bytes through it.

The bytes live in ``tests/cassettes/openai-chat-completions.json``. They are
shaped exactly as the API returns them but were written by hand, not captured
from a live model — issue #31's "record one session against a real model" still
wants a person with a key and a dollar. What is settled here is that the path
works at all.

litellm is an optional extra, so this whole module skips when it is absent.
"""

import json
import sys
from pathlib import Path

import pytest

litellm = pytest.importorskip("litellm", reason="the providers extra is not installed")
httpx = pytest.importorskip("httpx", reason="the providers extra is not installed")

from langchef.core.credentials import present  # noqa: E402
from langchef.judge.cache import Cache, prompt_key  # noqa: E402
from langchef.judge.example import Example  # noqa: E402
from langchef.judge.providers import (  # noqa: E402
    LiteLLMProvider,
    ProviderError,
    ReplayProvider,
    build_prompt,
    reply_text,
    resolve,
)
from langchef.judge.rubric import parse  # noqa: E402
from langchef.judge.runner import run  # noqa: E402

CASSETTES = Path(__file__).resolve().parent / "cassettes"
WIRE = json.loads((CASSETTES / "openai-chat-completions.json").read_text(encoding="utf-8"))
INTERACTIONS = WIRE["interactions"]
REPLAY_CASSETTE = CASSETTES / "answer-quality.replay.json"

MODEL = WIRE["model"]
# A literal in a test file, not a credential. The SDK builds an Authorization
# header out of whatever it is given and the MockTransport throws the request
# away; `scripts/assert_no_credentials.py` is unaffected, and
# `test_no_provider_credential_is_present_or_needed` proves the environment
# holds nothing real.
NOT_A_KEY = "langchef-test-transport-only"

RUBRIC_TEXT = """# Answer quality

### Correctness

The answer states the fact asked for.

### Groundedness

Every claim is supported by the retrieved context.

### Directness

The answer answers.
"""
RUBRIC = parse(RUBRIC_TEXT, "answer-quality")
EXAMPLE = Example(
    example_id="ex-1",
    question="Tell me the payment terms.",
    answer="Payment terms are net thirty days.",
    context=("Payment terms are net thirty days.",),
    expected="net thirty days",
)


class Wire:
    """The socket, replaced: recorded responses out, real requests in.

    ``plays`` queues one response per call and makes an unexpected extra call a
    failure. ``always`` answers every call the same way, which is what a retry
    scenario needs — the SDK's retry loop is the thing under test there, so the
    count of requests is an assertion rather than a fixture parameter.
    """

    def __init__(self) -> None:
        self.queued: list[str] = []
        self.repeating: str | None = None
        self.requests: list[dict] = []

    def reset(self) -> None:
        self.queued.clear()
        self.repeating = None
        self.requests.clear()

    def plays(self, *names: str) -> None:
        self.queued.extend(names)

    def always(self, name: str) -> None:
        self.repeating = name

    def handle(self, request: "httpx.Request") -> "httpx.Response":
        self.requests.append(json.loads(request.content.decode("utf-8")))
        name = self.queued.pop(0) if self.queued else self.repeating
        if name is None:
            raise AssertionError(f"the shim made an unqueued call to {request.url}")
        recorded = INTERACTIONS[name]
        return httpx.Response(recorded["status"], json=recorded["body"])


_WIRE = Wire()


@pytest.fixture(scope="session", autouse=True)
def _transport():
    """Install the fake socket once, for the whole session.

    Once per session rather than once per test on purpose: litellm caches the
    SDK client it builds, and that client captures ``client_session`` at
    construction, so a replacement installed later would be silently ignored and
    every later test would replay the first test's responses. One client, whose
    handler indirects through a mutable ``Wire``, is the only arrangement that
    actually isolates the tests.
    """
    was_session, was_key = litellm.client_session, litellm.api_key
    litellm.client_session = httpx.Client(transport=httpx.MockTransport(_WIRE.handle))
    litellm.api_key = NOT_A_KEY
    yield
    litellm.client_session, litellm.api_key = was_session, was_key


@pytest.fixture
def wire() -> Wire:
    _WIRE.reset()
    return _WIRE


# --- what our code puts on the wire ------------------------------------------


def test_no_provider_credential_is_present_or_needed(wire):
    """The point of the whole exercise: this runs with an empty environment."""
    assert present() == [], "these tests must not be able to spend money"
    wire.plays("grades-pass")
    assert LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL).verdict == "pass"


def test_the_request_that_reaches_the_wire_is_the_prompt_we_built(wire):
    """Request construction, asserted on the bytes rather than on a mock's args."""
    wire.plays("grades-pass")
    LiteLLMProvider(temperature=0.0).judge(EXAMPLE, RUBRIC, MODEL)

    assert len(wire.requests) == 1
    sent = wire.requests[0]
    assert sent["model"] == MODEL
    assert sent["temperature"] == 0.0
    assert sent["messages"] == [{"role": "user", "content": build_prompt(EXAMPLE, RUBRIC)}]
    # The prompt is the cassette key, so it has to be the prompt verbatim.
    assert RUBRIC.ref in sent["messages"][0]["content"]
    assert EXAMPLE.answer in sent["messages"][0]["content"]


def test_the_temperature_is_ours_not_the_default(wire):
    wire.plays("grades-pass")
    LiteLLMProvider(temperature=0.4).judge(EXAMPLE, RUBRIC, MODEL)
    assert wire.requests[0]["temperature"] == 0.4


# --- what our code makes of what comes back ----------------------------------


def test_a_recorded_reply_becomes_a_judgement(wire):
    wire.plays("grades-pass")
    judgement = LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)

    assert judgement.example_id == "ex-1"
    assert judgement.verdict == "pass"
    assert judgement.confidence == pytest.approx(0.88)
    assert judgement.criterion is None
    assert "retrieved context" in judgement.rationale
    # The pin records the model that was asked, not the dated snapshot that answered.
    assert judgement.model == MODEL


def test_a_fenced_reply_from_the_wire_is_parsed(wire):
    wire.plays("grades-fail-fenced")
    judgement = LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)
    assert judgement.verdict == "fail"
    assert judgement.criterion == "Groundedness"
    assert judgement.confidence == pytest.approx(0.71)


def test_prose_instead_of_json_is_refused(wire):
    wire.plays("prose-not-json")
    with pytest.raises(ProviderError, match="did not return JSON"):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)


def test_json_that_is_not_an_object_is_refused(wire):
    """A bare ``"pass"`` is valid JSON. It used to raise AttributeError."""
    wire.plays("json-but-not-an-object")
    with pytest.raises(ProviderError, match="JSON str, not an object"):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)


def test_a_reply_with_no_text_is_refused_rather_than_crashing(wire):
    """A content filter stops a model with ``content: null``, which is ordinary.

    Before this path ran it raised ``AttributeError: 'NoneType' object has no
    attribute 'strip'`` out of the shim. The CLI catches ``ProviderError`` and
    nothing else, so that came out as a traceback with no JSON on stdout — an
    exit the contract does not describe.
    """
    wire.plays("stops-without-text")
    with pytest.raises(ProviderError, match="no text to grade"):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)


def test_a_message_with_no_content_field_is_refused(wire):
    wire.plays("message-without-content")
    with pytest.raises(ProviderError, match="no text to grade"):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)


def test_a_response_without_choices_fails_rather_than_degrading(wire):
    """The schema-change assertion issue #31 asks for, made at the wire."""
    wire.plays("no-choices")
    with pytest.raises(ProviderError, match=MODEL):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)


def test_reply_text_names_the_schema_that_moved():
    """The same guard, reached directly, where litellm would refuse the body first."""
    with pytest.raises(ProviderError, match="cannot read"):
        reply_text({"choices": []}, MODEL)
    with pytest.raises(ProviderError, match="cannot read"):
        reply_text({"choices": [{"finish_reason": "stop"}]}, MODEL)
    with pytest.raises(ProviderError, match="finish_reason='length'"):
        reply_text({"choices": [{"finish_reason": "length", "message": {"content": None}}]}, MODEL)


# --- failures, and what the SDK does about them ------------------------------


def test_a_rate_limit_is_retried_and_then_reported(wire):
    """The SDK's retry loop is real code and it runs here."""
    wire.always("rate-limited")
    with pytest.raises(ProviderError, match="RateLimitError") as caught:
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)
    assert str(caught.value).startswith(f"{MODEL}: ")
    assert len(wire.requests) > 1, "a rate limit should be retried before it is given up on"


def test_a_server_error_is_retried_and_then_reported(wire):
    wire.always("server-error")
    with pytest.raises(ProviderError, match=MODEL):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)
    assert len(wire.requests) > 1


def test_a_bad_request_is_not_retried(wire):
    """Retrying a 400 spends money to be told the same thing again."""
    wire.plays("bad-request")
    with pytest.raises(ProviderError, match="BadRequestError"):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)
    assert len(wire.requests) == 1


def test_a_missing_litellm_says_how_to_install_it(monkeypatch):
    """The optional-extra branch, which also had never executed."""

    class Blocked:
        def find_spec(self, name, path=None, target=None):
            if name == "litellm" or name.startswith("litellm."):
                raise ModuleNotFoundError(f"No module named {name!r}", name=name)
            return None

    monkeypatch.delitem(sys.modules, "litellm", raising=False)
    monkeypatch.setattr(sys, "meta_path", [Blocked(), *sys.meta_path])
    with pytest.raises(ProviderError, match="litellm is not installed"):
        LiteLLMProvider().judge(EXAMPLE, RUBRIC, MODEL)


# --- record once, replay forever ---------------------------------------------


def test_recording_then_replaying_gives_the_identical_verdict(wire, tmp_path, monkeypatch):
    """The workflow the whole cassette design exists for, end to end."""
    destination = tmp_path / "nested" / "cassettes.json"
    monkeypatch.setenv("LANGCHEF_RECORD_TO", str(destination))
    provider = resolve("litellm")
    assert isinstance(provider, LiteLLMProvider)

    wire.plays("grades-pass")
    live = provider.judge(EXAMPLE, RUBRIC, MODEL)

    recorded = json.loads(destination.read_text(encoding="utf-8"))
    assert list(recorded) == [prompt_key(build_prompt(EXAMPLE, RUBRIC), MODEL)]

    replayed = ReplayProvider(cassettes=destination).judge(EXAMPLE, RUBRIC, MODEL)
    assert replayed.to_dict() == live.to_dict()
    assert len(wire.requests) == 1, "replay must not reach the wire"


def test_the_committed_cassette_still_matches_the_prompt_we_send():
    """A silent edit to ``PROMPT`` would strand every recording ever made.

    The cassette key is the exact bytes sent, so this fails loudly on the day
    somebody rewords the prompt — which is the point: a rewording changes what
    was asked, and a recording of the answer to a different question is not
    evidence.
    """
    recorded = json.loads(REPLAY_CASSETTE.read_text(encoding="utf-8"))
    key = prompt_key(build_prompt(EXAMPLE, RUBRIC), MODEL)
    assert key in recorded, (
        f"{REPLAY_CASSETTE.name} has no reply under {key}. The prompt or the model "
        f"moved; re-record with LANGCHEF_RECORD_TO={REPLAY_CASSETTE}."
    )
    judgement = ReplayProvider(cassettes=REPLAY_CASSETTE).judge(EXAMPLE, RUBRIC, MODEL)
    assert judgement.verdict == "pass"
    assert judgement.confidence == pytest.approx(0.88)


def test_the_committed_cassette_carries_no_credential():
    """It is in a public repository. Say so with an assertion, not a comment."""
    for path in sorted(CASSETTES.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        assert "sk-" not in text, f"{path.name} looks like it carries an API key"
        assert "Authorization" not in text
        assert "api_key" not in text


# --- and the same path, driven by the runner ---------------------------------


def test_the_runner_drives_the_litellm_path_and_then_stops_paying(wire, tmp_path):
    """Everything between the CLI and the socket, on the real backend.

    ``judge_cmd`` adds only argument parsing to this: the runner, the cache and
    the shim are all here, and the second run proves a cached judgement never
    reaches a provider.
    """
    batch = [
        EXAMPLE,
        Example(
            example_id="ex-2",
            question="Tell me the payment terms.",
            answer="Net thirty days, invoiced monthly by our Leeds office.",
            context=("Payment terms are net thirty days.",),
            expected="net thirty days",
        ),
    ]
    cache_path = tmp_path / "judgements.jsonl"

    wire.plays("grades-pass", "grades-fail-fenced")
    first = run(batch, RUBRIC, LiteLLMProvider(), MODEL, Cache(cache_path))
    assert first.verdicts() == ["pass", "fail"]
    assert first.stats["provider_calls"] == 2
    assert first.pin.provider == "litellm"
    assert first.pin.cheap_model == MODEL
    assert len(wire.requests) == 2

    again = run(batch, RUBRIC, LiteLLMProvider(), MODEL, Cache(cache_path))
    assert again.stats["provider_calls"] == 0
    assert again.stats["cache_hits"] == 2
    assert len(wire.requests) == 2, "a cache hit must not reach the wire"

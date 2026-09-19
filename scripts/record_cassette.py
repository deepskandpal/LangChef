#!/usr/bin/env python3
"""Record one real judging session and write a scrubbed cassette.

Issue #31's one remaining step, and the only one in this repository that needs a
person: a key, and about a dollar. Everything else about the litellm path is
already exercised in CI against recorded bytes.

    export OPENAI_API_KEY=sk-...
    uv run python scripts/record_cassette.py --model gpt-4o-mini --examples 6

What it does, in order:

1. Refuses unless a provider credential is present. This is the one script here
   that inverts ``scripts/assert_no_credentials.py``, and it says so.
2. Prints the model, the number of calls and an estimated cost, then stops and
   asks. Nothing is spent before a person types yes.
3. Runs the real ``LiteLLMProvider`` over a handful of dogfood examples.
4. Captures the wire exchange, scrubs it, and **audits the finished bytes
   against the live credential values** before writing anything.
5. Refuses to write a file the audit flags, and says which check failed.

It writes **two** cassettes, because two different things replay them:

``answer-quality.recorded.json``
    ``{prompt_key: reply_text}``, which is what ``ReplayProvider`` reads. Enough
    to re-run a judgement offline, and nothing more: it begins after
    ``reply_text`` has already pulled the string out of the response.

``openai-chat-completions.recorded.json``
    Whole HTTP responses, in the shape ``tests/test_litellm_path.py`` serves
    through its ``httpx.MockTransport``. This is the one that matters, because a
    hand-written body cannot notice that the provider's response shape moved,
    and noticing that is the only reason the fixture exists.

A live recording can only supply the **success** shapes. The error scenarios in
the hand-written fixture (a 429, a 500, a reply with no choices) stay
hand-written by necessity: you cannot buy a rate limit for a dollar.

The audit is the part that matters. Scrubbing is a transformation and can be
wrong; the audit reads the bytes that are about to be committed, knows the
actual secret values, and is the last thing between a key and a public
repository.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchef.core.credentials import VARS, present  # noqa: E402
from langchef.judge import scrub  # noqa: E402

#: Rough per-call cost in US dollars for the models worth recording against.
#: Deliberately an over-estimate: a person deciding whether to spend should be
#: told the larger number.
COST_PER_CALL: dict[str, float] = {
    "gpt-4o-mini": 0.0004,
    "gpt-4.1-mini": 0.0004,
    "claude-haiku-4-5-20251001": 0.0008,
}
DEFAULT_COST = 0.002


def _examples(count: int):
    """A few dogfood questions, answered by the baseline app.

    The dogfood is the right source: the examples are already public, already in
    the repository, and carry no customer text. Recording against anything a
    user owns would put their content in a public fixture.
    """
    from dogfood.app import BASELINE
    from dogfood.app import run as run_app
    from dogfood.corpus import questions

    from langchef.judge.example import Example

    rows = run_app(BASELINE, questions()[:count])
    return [
        Example.from_dict({k: v for k, v in row.items() if not k.startswith("_")}) for row in rows
    ]


def _confirm(model: str, calls: int, assume_yes: bool) -> bool:
    estimate = calls * COST_PER_CALL.get(model, DEFAULT_COST)
    print(f"model:     {model}", file=sys.stderr)
    print(f"calls:     {calls}", file=sys.stderr)
    print(f"estimate:  ${estimate:.4f} (over-estimate)", file=sys.stderr)
    if assume_yes:
        return True
    return input("spend it? [y/N] ").strip().lower() in {"y", "yes"}


def _tee(httpx, scrub_mod, inner=None):
    """The real socket, with a copy taken.

    ``LiteLLMProvider._record`` keeps the assistant's *text*. That is all
    ``ReplayProvider`` needs, and it is not what the wire fixture needs: by the
    time the text exists, ``reply_text`` has already read the response shape and
    thrown the rest away. A fixture built from text can never fail because the
    provider moved a field.

    litellm hands ``litellm.client_session`` to the provider SDK as its HTTP
    client, so wrapping the transport underneath it captures the exchange
    without touching a line of the provider. Headers go through the scrubber's
    allowlist on the way in, which is where ``openai-organization`` (an account
    id, and forbidden in these fixtures) gets dropped.

    ``inner`` defaults to a real ``HTTPTransport`` and is injectable only so the
    capture can be tested offline; see
    ``tests/test_litellm_path.py::test_the_tee_captures_the_exchange_it_passes_through``.
    """

    class Tee(httpx.BaseTransport):
        def __init__(self) -> None:
            # ``inner`` is injectable so that the capture logic itself can be
            # tested without a key and without a socket. Recording is the one
            # thing here that needs a person, and a *recorder* that had never
            # executed would be the same bug as the one issue #31 is closing.
            self.inner = inner if inner is not None else httpx.HTTPTransport()
            self.captured: list[dict] = []

        def handle_request(self, request):
            response = self.inner.handle_request(request)
            body = response.read()
            response.close()
            try:
                decoded = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Not JSON, so it is no use as a fixture. Record the status so a
                # reader can see it happened rather than silently dropping it.
                decoded = None
            self.captured.append(
                {
                    "status": response.status_code,
                    "body": decoded,
                    "headers": scrub_mod.headers(dict(response.headers)),
                }
            )
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                content=body,
                request=request,
            )

    return Tee()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--examples", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "tests" / "cassettes" / "answer-quality.recorded.json",
    )
    parser.add_argument(
        "--wire-out",
        type=Path,
        default=ROOT / "tests" / "cassettes" / "openai-chat-completions.recorded.json",
        help="whole HTTP responses, in the shape tests/test_litellm_path.py serves",
    )
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    found = present()
    if not found:
        print(
            "FAIL: no provider credential in this environment, so there is nothing "
            f"to record against. Set one of: {', '.join(VARS)}",
            file=sys.stderr,
        )
        return 1
    print(f"credential(s) present: {', '.join(found)}", file=sys.stderr)

    if not _confirm(args.model, args.examples, args.yes):
        print("nothing recorded", file=sys.stderr)
        return 2

    from langchef.judge.providers import LiteLLMProvider, ProviderError
    from langchef.judge.rubric import parse
    from langchef.workspace.scaffold import RUBRIC

    try:
        import httpx
        import litellm
    except ModuleNotFoundError:
        print(
            "FAIL: the providers extra is not installed. `uv sync --extra providers`",
            file=sys.stderr,
        )
        return 1

    rubric = parse(RUBRIC, "answer-quality")
    staging = args.out.with_suffix(".raw.json")
    provider = LiteLLMProvider(record_to=staging)

    # Before the first call, not after: litellm caches the SDK client it builds
    # and that client captures ``client_session`` at construction, so a
    # transport installed later is silently ignored.
    tee = _tee(httpx, scrub)
    was_session = litellm.client_session
    litellm.client_session = httpx.Client(transport=tee, timeout=60.0)
    try:
        for example in _examples(args.examples):
            provider.judge(example, rubric, model=args.model)
    except ProviderError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        litellm.client_session = was_session

    if not staging.is_file():
        print("FAIL: the provider recorded nothing", file=sys.stderr)
        return 1

    recorded = json.loads(staging.read_text(encoding="utf-8"))
    cleaned = scrub.payload(recorded)
    blob = json.dumps(cleaned, indent=2, sort_keys=True, ensure_ascii=False)

    wire = {
        "provenance": (
            f"Captured from a live {args.model} on "
            f"{datetime.date.today().isoformat()} by scripts/record_cassette.py, "
            "scrubbed and audited before writing. These are the success shapes "
            "only. A live run cannot produce a 429, a 500 or a response with no "
            "choices, so those stay hand-written in "
            "openai-chat-completions.json; what this file settles is that the "
            "hand-written success bodies match what the provider actually sends."
        ),
        "model": args.model,
        "interactions": {
            f"live-{index:02d}": scrub.payload(interaction)
            for index, interaction in enumerate(tee.captured, start=1)
        },
    }
    wire_blob = json.dumps(wire, indent=2, sort_keys=True, ensure_ascii=False)

    secrets = [value for name in VARS if (value := os.environ.get(name))]
    problems = scrub.audit(blob, secrets) + scrub.audit(wire_blob, secrets)
    if problems:
        staging.unlink(missing_ok=True)
        print("FAIL: refusing to write this cassette:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if not tee.captured:
        print(
            "FAIL: no HTTP exchange was captured, so the transport was not the "
            "one litellm used. Nothing written.",
            file=sys.stderr,
        )
        staging.unlink(missing_ok=True)
        return 1

    args.out.write_text(blob + "\n", encoding="utf-8")
    args.wire_out.parent.mkdir(parents=True, exist_ok=True)
    args.wire_out.write_text(wire_blob + "\n", encoding="utf-8")
    staging.unlink(missing_ok=True)
    print(f"ok: {len(cleaned)} reply/replies -> {args.out}", file=sys.stderr)
    print(f"ok: {len(tee.captured)} HTTP exchange(s) -> {args.wire_out}", file=sys.stderr)
    print(
        "Next: commit both. tests/test_litellm_path.py picks the wire file up "
        "automatically and checks every recorded success against the code that "
        "reads it; it skips when the file is absent.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

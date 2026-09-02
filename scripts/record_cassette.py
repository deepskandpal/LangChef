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

The audit is the part that matters. Scrubbing is a transformation and can be
wrong; the audit reads the bytes that are about to be committed, knows the
actual secret values, and is the last thing between a key and a public
repository.
"""

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--examples", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "tests" / "cassettes" / "answer-quality.recorded.json",
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

    rubric = parse(RUBRIC, "answer-quality")
    staging = args.out.with_suffix(".raw.json")
    provider = LiteLLMProvider(record_to=staging)

    try:
        for example in _examples(args.examples):
            provider.judge(example, rubric, model=args.model)
    except ProviderError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if not staging.is_file():
        print("FAIL: the provider recorded nothing", file=sys.stderr)
        return 1

    recorded = json.loads(staging.read_text(encoding="utf-8"))
    cleaned = scrub.payload(recorded)
    blob = json.dumps(cleaned, indent=2, sort_keys=True, ensure_ascii=False)

    secrets = [value for name in VARS if (value := os.environ.get(name))]
    problems = scrub.audit(blob, secrets)
    if problems:
        staging.unlink(missing_ok=True)
        print("FAIL: refusing to write this cassette:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    args.out.write_text(blob + "\n", encoding="utf-8")
    staging.unlink(missing_ok=True)
    print(f"ok: {len(cleaned)} interaction(s) -> {args.out}", file=sys.stderr)
    print(
        'Next: point a workspace at it with provider = "replay" and '
        "cassettes = the path above, then commit it.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

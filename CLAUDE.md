# CLAUDE.md

Instructions for Claude Code sessions in this repository. The full working
agreement is [`AGENTS.md`](AGENTS.md) and it applies here unchanged. This file
carries only what a session must not get wrong.

## Nothing reaches `main` without a pull request

**Every piece of issue work goes on a branch and through a pull request that at
least one maintainer reviews.** No direct commits to `main`, including the
maintainer's own. *(DECISIONS #14)*

```sh
git switch -c <issue-number>-short-slug
./scripts/verify.sh                 # all 10 steps, green, before you push
git push -u origin <issue-number>-short-slug
gh pr create --fill
```

If you are asked to fix something and you find yourself committing on `main`,
you have already made the mistake. Branch first.

The reason is the failure mode this product exists to prevent: a plausible wrong
number does not crash and does not fail a test nobody wrote. Every defect caught
late in this repository was caught by a person reading the change. Review is the
control that works, so it applies to everyone.

## How work is picked up

Prioritise across `lifecycle:spec` (needs a decision), `lifecycle:ready` (can
start cold) and `lifecycle:blocked` (waiting, and the body says on what). Ready
work is dispatched to several agents at once, one issue each, and **no two agents
on the same `area:` label** since those map to directories and exist as collision
boundaries. Every agent opens its own pull request.

`lifecycle:spec` means not ready. Settle the decision on the issue first; writing
the code and the decision afterwards is how a threshold ends up hidden in a
function instead of declared in a pre-registration.

## Outward actions are the maintainer's

Do not post comments, move labels, merge, or close issues unless asked in that
session. Draft and surface instead. Opening a pull request against an issue you
were asked to work on is the exception, because that is how work is delivered.

## The constraints that are not negotiable in a pull request

These are in `AGENTS.md` with their reasoning and their `DECISIONS.md` entries.
The short list, because breaking one is silent:

- JSON to stdout, prose to stderr. No `--format` flag.
- Exit codes are the gate: `0` ok, `1` error, `2` refused, `3` abstained, `4`
  budget exhausted, `5` pin mismatch. **Never weaken a refusal to pass a test.**
- Only `src/langchef/judge/providers.py` imports a provider SDK, and `core/`
  imports nothing from `judge/`, `connect/` or `packs/`.
- A statistic without a known-answer test against an independent implementation
  does not ship.
- Bump `VERSION` in `providers.py` when a scoring check changes.
- `docs/*.html` and `docs/AGENT-CONTRACT.md` are generated. Edit
  `scripts/build_docs.py` or `src/langchef/core/contract.py` and regenerate.

# Working agreement

For agents, and for people working like one. Read this before touching anything.

The repository is designed so that several agents can work at once without
standing on each other. That property is not free — it comes from the rules
below, and it disappears the moment one of them is skipped.

---

## The one rule everything else serves

**The CLI produces every number. The agent decides what to look at and what it
means.** Model spend goes on judgement and synthesis, never on arithmetic. A run
that costs $0.40 in judge calls should cost nothing in reasoning tokens to add
up.

If you find yourself computing a statistic in prose, stop: it belongs in
`core/`, with a test.

---

## Nothing reaches `main` without a pull request

**Every piece of work goes on a branch and through a pull request that at least
one maintainer reviews. There are no direct commits to `main`, and that includes
the maintainer's own.** *(DECISIONS #14)*

```sh
git switch -c 28-per-criterion-compare   # <issue-number>-short-slug
./scripts/verify.sh                      # all 10 steps, green
git push -u origin 28-per-criterion-compare
gh pr create --fill                      # then fill the template honestly
```

The failure mode this repository exists to prevent is a plausible wrong number.
It does not crash and it does not fail a test nobody wrote. Every defect caught
late here was caught by somebody reading the change, not by CI, so review is the
control that actually works and it applies to everyone.

This matters more, not less, when several agents are working at once. Volume is
exactly the condition under which a number that looks right gets waved through.

---

## Picking up work

[The board](https://github.com/users/deepskandpal/projects/5) carries the same information as sortable fields —
Priority, Area, Size, Ownership, Lifecycle — if you would rather filter than query.
Items with no Ownership set are the four epics, which are not picked up directly.

```sh
# Everything an agent can finish alone, most urgent first
gh issue list --label "agent:ready" --label "lifecycle:ready" --sort created --state open

# What is blocked, and on what
gh issue list --label "lifecycle:blocked"

# What needs a person — do not attempt these
gh issue list --label "agent:needs-human"
```

Every issue is written to be picked up cold: **What**, **Why it matters**,
**Start at** (the file to open first), and **Done when**. If an issue you are
given does not have those, add them before writing code — that is the work, not
overhead.

An issue labelled `lifecycle:spec` is **not ready**. It needs a decision or a
design first, and the decision is usually named in the body. Doing the code
first and the decision afterwards is how a threshold ends up hidden in a
function instead of declared in a pre-registration.

Work is prioritised on weekdays across the three lifecycle states that carry it:
`lifecycle:spec` for what needs deciding, `lifecycle:ready` for what can start
cold, and `lifecycle:blocked` for what is waiting and on what. The ready set is
then dispatched to several agents at once. One issue per agent, no two agents on
the same `area:` label, and every one of them opens a pull request.

## Claiming it

1. Comment on the issue saying you are starting.
2. Branch: `<issue-number>-short-slug`, e.g. `28-per-criterion-compare`.

That is all of it. **You do not move the label yourself**, and if you do not have
write access you could not anyway. A workflow reads the comment and moves the
issue to `lifecycle:doing` for you, then says so on the issue.

**Any comment from a person on a `lifecycle:ready` issue claims it**, whatever it
says. If you only meant to ask a question, say so and a maintainer will move it
back. That is deliberately blunt, and it is the second version of this rule.

The first version asked contributors to set `lifecycle:doing` themselves, which
outside contributors cannot do; #25 looked free for three hours after it was
claimed and two people wrote the same fix. The second version matched claim
phrasings with a regex; on 28 August somebody wrote "I'd love to" where it
expected "I'd like to", #64 sat `lifecycle:ready` for thirteen hours with a PR
already open against it, and it happened again.

A missed claim is silent and looks exactly like no claim. A false claim costs one
label and a reply. So there is no phrase list.

**Two agents must not hold issues carrying the same `area:` label at the same
time.** The area labels map to directories and exist precisely to be collision
boundaries:

| Label | Owns |
|---|---|
| `area:core` | `src/langchef/core/` — statistics, no I/O, no network |
| `area:judge` | `src/langchef/judge/` — runner, cache, the provider shim |
| `area:workspace` | `src/langchef/workspace/` — formats, runs, ledger |
| `area:cli` | `src/langchef/cli/` — thin typer commands, no logic |
| `area:connect` | `src/langchef/connect/` — readers and remote stores |
| `area:packs` | `packs/` and the pack loader — the moat, kept separable |
| `area:adapters` | `adapters/` — harness packaging, deliberately trivial |
| `area:dogfood` | `dogfood/` — the app with planted regressions |
| `area:docs` | `scripts/build_docs.py` and the prose |
| `area:ci` | `.github/`, `scripts/verify.sh`, toolchain |

An issue that genuinely needs two areas is usually two issues.

---

## Say what wrote it

If an agent prepared the change, say so. One line in the claim or the pull request
description is enough.

This is a disclosure norm, not a permission gate. Nothing here is closed to agents:
this repository has an `agent:ready` label, a machine-readable working agreement,
and a product thesis that evaluation belongs inside the harness a team already
runs. Refusing agent contributions would contradict the thing being built.

The reason to ask is that it changes how a change is read, not whether it is
accepted. The most valuable contribution this project has received was an agent
that found a statistical flaw in `core/sampling.py`, stopped, and opened no pull
request at all. The least valuable was a change to `src/` with no tests. Neither
outcome was predicted by whether a person or a model wrote it, and both were
predicted by whether the contributor engaged with the issue first.

## How much review a change needs, by what it can break

The `area:` labels are already collision boundaries. They are also the honest
measure of blast radius, so they set the bar.

| Area | Bar |
|---|---|
| `area:docs`, `area:dogfood`, `area:adapters` | open. Low risk, easy to revert |
| `area:cli`, `area:workspace`, `area:judge` | normal. Tests expected, `verify.sh` green |
| **`area:core`** | **agree the approach on the issue before writing code** |
| `DECISIONS.md`, the agent contract, `packs/` | a decision issue first, never a direct pull request |

`area:core` is the statistics. A wrong answer there is invisible: it does not
crash, it does not fail a test that nobody wrote, and it produces numbers that
look exactly like the right numbers. That is the entire failure mode this
product exists to prevent, so it is the one place where discussion comes before
a diff. [#60](https://github.com/deepskandpal/LangChef/issues/60) exists because
a contributor did precisely this without being asked.

## The lifecycle

```
spec ──> ready ──> doing ──> review ──> closed
  │                            │
  └──> (a dated entry          └──> blocked ──┐
        in DECISIONS.md)            ▲         │
                                    └─────────┘
```

- **`lifecycle:spec`** — a decision or a design is missing. Settle it first.
- **`lifecycle:ready`** — specified well enough to start cold.
- **`lifecycle:doing`** — someone is on it. Check before starting.
- **`lifecycle:review`** — a PR exists and needs verification.
- **`lifecycle:blocked`** — waiting on another issue, or on a person.
- **`lifecycle:done`** — shipped and verified. Set it, then close.

Epics (`epic`) are containers. The work is in their children; do not implement
an epic directly.

---

## Constraints you cannot negotiate alone

These are load-bearing. Each traces to a dated entry in
[`DECISIONS.md`](DECISIONS.md), and changing one means adding a new dated entry
there — not editing code until the tests agree.

**Text is the record.** TOML config, JSONL goldens and labels, Markdown rubrics,
JSON baselines. Parquet only for bulk per-example scores. DuckDB is a query
engine over those files and **never the store**. The entire trust story is that
a person can review a workspace in a pull request, and a database file in git is
a black box. A derived index is fine if deleting it loses nothing but time.
*(#4)*

**JSON to stdout, prose to stderr. There is no `--format` flag.** `--help` is
the single exception, because it is written for people. The agent parses stdout,
the human reads stderr, and neither is an afterthought bolted onto the other.
*(#3)*

**Exit codes are the gate mechanism, not advice.** `0` ok · `1` error · `2`
refused, an approval gate is unmet · `3` abstained · `4` budget exhausted · `5`
pin mismatch. An agent cannot argue with a non-zero exit — which is the only
reason the gates are real. **Never weaken a refusal to make a test pass.** If a
gate is in the way, the design is wrong or the gate is; say so on the issue.

**One file imports a provider SDK.** `src/langchef/judge/providers.py`, and
nothing else, ever. `tests/test_boundaries.py` enforces it, and `core/` imports
nothing from `judge/`, `connect/` or `packs/`. This is what makes every number
in the product testable with no API key and no network. *(#5, #6)*

**No number without a run artifact.** Any figure in a memo must trace to a file
under `runs/`. CI fails the dogfood memos when one appears that does not.

**A statistic without a known-answer test does not ship.** Check it against an
independent implementation or a closed form. scikit-learn is available for this
and is a *test-only* dependency — importing it from `core/` breaks the boundary
test, which is deliberate. *(#7)*

**Recording a cassette needs a person, and one command.** `LiteLLMProvider` is
the backend every real user runs and the one CI can never run, because
`scripts/assert_no_credentials.py` asserts a key is absent before anything else.
`scripts/record_cassette.py` is the single place that inverts that: it refuses
without a credential, states the cost and waits, scrubs what it captured, and
**audits the finished bytes against the live secret values before writing**. It
refuses to write a file the audit flags. Nothing else in this repository should
ever read a key.

**Bump `VERSION` in `providers.py` when a scoring check changes.** The model pin
is part of the judgement cache key, so editing a check without bumping it
silently serves stale judgements. Nothing catches this yet — that is
[#32](https://github.com/deepskandpal/LangChef/issues/32).

---

## Generated files

Never hand-edit these. Regenerate them:

```sh
uv run python scripts/build_docs.py      # docs/*.html
uv run python scripts/render_contract.py # docs/AGENT-CONTRACT.md
```

`verify.sh` runs both in `--check` mode, so a stale contract or a stale site
fails CI rather than shipping. `src/langchef/core/contract.py` is the authority
for what a command does and whether it exists — change a command's status
there, not in the prose.

---

## How this is tested

Five kinds, and the rule for each. These are not guidelines — a change that
cannot satisfy the relevant row does not ship.

| Kind | What it covers | The rule |
|---|---|---|
| **Known-answer** | Every statistic — κ, confusion metrics, bootstrap intervals, power, detection limits | Checked against an independent implementation or a closed form. **A statistic without one does not ship.** scikit-learn is available for this and is test-only. |
| **Property** | Invariants: label permutation, monotonicity of agreement, interval coverage | Coverage must sit at the nominal rate across many simulated draws, not on one example. |
| **Simulation** | The planted regressions in `dogfood/` | Detection rate at a fixed false-alarm budget, tracked as a first-class metric of the product — not a smoke test. |
| **Cassette** | Judge calls | Recorded once, replayed forever. CI runs with **no API key present and asserts its absence**, so no test can ever spend money. |
| **Lint** | Memos and module boundaries | No number without a run artifact. `core/` imports nothing from `judge/`, `connect/` or `packs/`. |

**The failure mode all five exist to catch is a plausible wrong number.** A crash
announces itself. A statistic that is off by a factor of two produces output that
looks exactly like correct output, survives review, and is believed.

---

## What runs on your pull request

Two automatic checks, both of which only leave a comment. Neither fails the build,
because a bot that blocks a good contribution costs more than one a maintainer can
ignore.

- **Already-held.** If the issue you close is `lifecycle:doing` and somebody else
  claimed it first, the pull request says so. Three separate people implemented
  [#25](https://github.com/deepskandpal/LangChef/issues/25) on 27 August before
  this existed.
- **`src/` without `tests/`.** Most issues name the tests they expect. If the
  change is genuinely untestable, say so in the description.

`main` requires both CI legs to pass before anything merges, and it takes no
direct commits from anyone. Branch, push, open a pull request.

## Before opening a pull request

```sh
./scripts/verify.sh        # all 10 steps
```

Step 1 asserts that **no provider credentials are present**, so no test can ever
spend money. If it fails, unset the key rather than skipping the step.

Then fill in the PR template honestly, including the last section. A stated gap
is worth more than a tidy diff.

---

## When you are wrong

Two of the defects already closed here were caught by review, not by tests: a
minimum detectable effect computed with an unpaired formula on paired data
(reporting 15.6% where the truth was 6.0%), and a readout that silently picked
whichever run happened to be newest. Both looked fine and produced plausible
numbers.

Plausible numbers are the failure mode of this entire category of tool. When a
result looks reasonable, that is not evidence. Check the arithmetic against a
case where you know the answer.

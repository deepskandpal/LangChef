# LangChef

**You changed the model, the retriever, or the fine-tune. Is the app better or
worse?**

Most teams shipping an LLM feature cannot answer that with a straight face.
LangChef is a command-line tool that answers it properly — and, just as often,
tells you honestly that your test set was never big enough to tell.

It is built for the engineer who maintains a retrieval app, a classifier or an
agent, has no evaluation background, and has no evaluation team to ask. Your
provider retires the model you shipped on; you swap an embedding model; you
distil to a fine-tuned small model to cut the bill. Same question every time.
You label about forty examples once, and from then on it tells you whether your
judge can be trusted, and whether each change was a real regression, a real
improvement, or noise.

**Documentation: <https://deepskandpal.github.io/LangChef/>** — start with
[your first evaluation](https://deepskandpal.github.io/LangChef/start.html).

### The three mistakes it exists to prevent

**Trusting a grader nobody graded.** Your judge marks 95% of answers good. If
only 5% of your answers are genuinely bad, a judge that marks *everything* good
scores 95% too — and from that number alone you cannot tell them apart.

**Reading meaning into a three-point swing.** 83% to 80% on ninety examples is
well inside what randomness produces. Nothing in a spreadsheet says so.

**Comparing two runs measured differently.** Edit the grading prompt between
runs and the two numbers were never measuring the same thing — but they still
line up on a chart.

**Averaging retrieval and generation into one number.** When quality drops after
an embedding swap, one pass rate cannot tell you whether the generator got worse
or is being handed worse context. Those have different fixes.

Every product in this market is capable and most of them are cheap. They also
all assume a human eval engineer exists to design the rubrics, interpret the
numbers and maintain the suites. Below a certain size that person does not
exist, which is why only about a third of teams running AI in production
evaluate it online at all. LangChef is the missing person, not another
dashboard.

---

## Status — M4, a working loop end to end

The whole loop runs: score a suite, choose what a person should label, take
their labels back, report how far the judge can be trusted, compare two arms,
and write the memo. **No API key, no network, no model** — the default judge is
deterministic, so a fresh clone runs the entire flow on any machine.

**Works today**

- `init`, `approve rubric`, `judge run`, `label plan`, `label import`,
  `calibrate report`, `baseline set | show`, `compare`, `memo render`,
  `ledger append | query`, plus `doctor`, `contract`, `packs list`
- Calibration statistics — Cohen's kappa with an interval, TPR/TNR/PPV/NPV with
  Wilson intervals, MCC, and a disagreement taxonomy that only flags a slice
  when its interval clears the base rate
- Paired experiment comparison — exact McNemar, bootstrap interval, and a
  minimum detectable effect on every inconclusive result
- A judgement cache keyed on content, rubric hash and model pin, so a rerun is
  free; two-tier judging, with a strong model re-scoring only the unsure cases
- Gate one, enforced: an unapproved or edited rubric exits 2, and a comparison
  across moved pins exits 5
- A [dogfood](dogfood/) app with three planted regressions and a self-test that
  asserts the harness finds two of them and honestly reports that it cannot
  resolve the third

**Not built yet** — production connectors and sampling, scheduling and
unattended operation, eval suites and triage, experiment pre-registration. See
the roadmap below and [`docs/AGENT-CONTRACT.md`](docs/AGENT-CONTRACT.md) for
where each command lands.

---

## Install

[uv](https://docs.astral.sh/uv/) is the only prerequisite. It fetches the
interpreter itself, so no system Python is involved and nothing is installed
globally.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh      # if you don't have it yet
```

```sh
git clone https://github.com/deepskandpal/LangChef.git langchef
cd langchef
uv sync                                     # Python 3.12 + dependencies
uv run langchef doctor
```

A green `doctor` means the interpreter is the pinned one, an expertise pack
resolves, and no provider credential is sitting in your environment.

Nothing is on PyPI yet — see [`docs/RESERVE-NAMES.md`](docs/RESERVE-NAMES.md).

To try the whole thing on an app whose failures are already known, run the
[dogfood](dogfood/):

```sh
uv run python -m dogfood.build
uv run pytest tests/test_dogfood.py -v
```

---

## Verify the build

One command runs every check, and it is the same script CI runs — there is no
second list to drift:

```console
$ ./scripts/verify.sh
1. no provider credentials present        PASS
2. pinned interpreter (3.12)              PASS
3. dependencies match the lock            PASS
4. lint                                   PASS
5. format                                 PASS
6. agent contract in sync                 PASS
7. documentation site in sync             PASS
8. tests                                  PASS
9. distribution builds                    PASS
10. wheel runs from a clean env           PASS

10 passed, 0 failed
```

Step 1 comes first on purpose: the suite exercises the deterministic core and
replays recorded judge responses, so a provider key in the environment means a
test could quietly start spending money. Any failure prints the last 25 lines
of that step and exits non-zero.

---

## What it looks like

```console
$ langchef calibrate report       # stderr — written for you
calibration for support-baseline on 40 labelled example(s)
  kappa      0.68  0.44..0.92
  TPR        80.0%  (12/15)
  FPR        12.0%
  disagreed  6 ({'false_alarm': 3, 'miss': 3})

$ langchef compare --variant support-stale-index
support-baseline -> support-stale-index on 90 shared golden(s)
  baseline 83.3%   variant 63.3%
  difference -20.0% [-27.8%, -12.2%]  p=0.0000
  REGRESSION

$ langchef compare --variant support-truncated-context
  difference +0.0% [+0.0%, +0.0%]  p=1.0000
  INCONCLUSIVE
  (smallest effect this run could have seen: 6.0%)
```

That last one is the product in one screen. There *is* a regression in that arm
— we planted a 3.3-point one — and the honest answer at this sample size is not
"no regression found", it is "nothing we could have seen".

```console
$ langchef doctor 2>/dev/null     # stdout — written for the agent (abridged)
{
  "checks": "… five checks, each with name / ok / required / detail …",
  "credentials_present": [],
  "ok": true,
  "pack_search_path": [
    "/home/dk/code/github/langchef/evals/packs",
    "/home/dk/code/github/langchef/packs"
  ],
  "packs": [
    "genai-rag@0.1.0"
  ],
  "python": "3.12.14",
  "version": "0.1.0"
}
```

Two streams, always. The agent parses stdout; you read stderr. There is no
`--format` flag, and `--help` is the only thing that ever prints something else
to stdout.

---

## The contract

The interface between a model that decides and a binary that computes is written
down, generated from the code, and readable at runtime:

```sh
langchef contract      # the same document as JSON
```

Two rules carry most of the weight.

**The CLI produces every number.** The agent chooses what to look at and says
what it means. Model spend goes on judgement and synthesis, never on arithmetic
— a run that costs $0.40 in judge calls should cost nothing in reasoning tokens
to add up. A corollary the linter enforces: *no number without a run artifact*.

**Refusals are exit codes.** The approval gates and the pre-registration rule
cannot live in a prompt; a model asked nicely not to read out early will,
eventually, read out early. So:

| Code | Meaning |
|---|---|
| `0` | ok |
| `1` | unexpected error |
| `2` | refused — an approval gate is unmet |
| `3` | abstained — confidence below threshold |
| `4` | budget exhausted; report of what was left undone written |
| `5` | pin mismatch — judge model, version or rubric hash moved |

An agent cannot argue with a non-zero exit.

---

## Layout

```
src/langchef/
  cli/          typer commands — thin, no logic
  core/         statistics, calibration, metrics — no I/O, no LLM, no network
  judge/        rubric, providers.py, cache, two-tier runner
  connect/      duckdb-first read-only connectors      (M5)
  workspace/    paths, formats, config, runs, ledger, scaffold
  render/       decision memos
  packs/        loader + manifest schema — the boundary
packs/genai-rag/       the first expertise pack
adapters/claude-code/  skill + commands — disposable packaging
dogfood/               RAG app with three planted regressions
```

One rule holds the design together: **`core/` imports nothing from `judge/`,
`connect/` or `packs/`**, and nothing third-party beyond numpy and scipy. That
is enforced by `tests/test_boundaries.py`, which is what makes every number in
the product testable with no API key and no network. A matching test keeps
litellm inside `judge/providers.py`, so there is exactly one file to rewrite if
it goes bad.

The other marked directory is `packs/`. It stays separable because the core is
Apache-2.0 and the expertise packs are not; if pack logic leaks into the core,
that split becomes impossible. See [`DECISIONS.md`](DECISIONS.md) #5.

---

## Development

`./scripts/verify.sh` is the whole thing. While iterating, the individual
pieces:

```sh
uv run pytest                               # the whole suite, with no API key
uv run pytest tests/test_boundaries.py -q   # just the layering rules
uv run ruff check . && uv run ruff format .
uv run python scripts/render_contract.py    # regenerate docs/AGENT-CONTRACT.md
uv run langchef doctor                      # what the agent sees
```

Judge calls, when they arrive in M2, are recorded once and replayed forever, so
no test can ever spend money — and CI asserts the absence of a key rather than
assuming it.

---

## Roadmap

| | Milestone | What exists at the end |
|---|---|---|
| **M0** ✅ | Ground | This repository: decisions, contract, toolchain, CI |
| **M1** ✅ | Calibration math | Judge–human agreement — TPR, TNR, Cohen's κ, disagreement taxonomy. No LLM |
| **M2** ✅ | Judge runner | Batched scoring, content-addressed cache, two-tier escalation, pins |
| **M3** ✅ | Workspace | `langchef init`, file formats, run ledger, comparison, decision memos |
| **M4** ✅ | Agent layer | Claude Code plugin, calibration playbook as a skill, gate one enforced |
| M5 | Unattended | Scheduling, weekly recalibration, spend caps, connectors and sampling |
| M6 | Job one | Eval suites, variance-derived thresholds, triage, rubric diffing |
| M7 | Experiments | Pre-registration, integrity checks, gated readout, power |

Calibration comes first on purpose. A judge is a measuring instrument, not a
metric; an eval suite built on an uncalibrated judge produces confident garbage,
and no amount of downstream statistics repairs it.

---

## Background

Documentation: **<https://deepskandpal.github.io/LangChef/>** — overview,
quickstart, concepts, and a command reference generated from the contract.

- [Issues](https://github.com/deepskandpal/LangChef/issues) — where the work is, including
  what is already done: the closed issues are the build log
- [The board](https://github.com/users/deepskandpal/projects/5) — the same work by priority, area, size and ownership
- [`AGENTS.md`](AGENTS.md) — the working agreement: the lifecycle, the area boundaries, and
  the constraints that are not negotiable in a pull request
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to start, in about a minute
- [`DECISIONS.md`](DECISIONS.md) — eleven calls, each with the reasoning and the date
- [`NON-GOALS.md`](NON-GOALS.md) — what is deliberately not built, and why
- [`TRACKER.md`](TRACKER.md) — the map: where the build is and where to look
- [`docs/AGENT-CONTRACT.md`](docs/AGENT-CONTRACT.md) — generated; what the agent may read, write, spend and decide
- [`dogfood/README.md`](dogfood/README.md) — the planted regressions and what they prove

The market analysis, the PRD and the engineering plan behind this repository are
working documents and are not published. Their conclusions are in the docs above;
`DECISIONS.md` carries the parts that constrain the code.

The 1.0 platform is not published either. Its vocabulary carried over; its code
did not.

---

## Licence

Apache-2.0 for the CLI and the workspace format — see [`LICENSE`](LICENSE).
Expertise packs are separately licensed.

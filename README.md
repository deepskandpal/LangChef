# LangChef

**An installed eval engineer.** A scheduled agent that lives in your repository,
runs inside the coding harness you already pay for, on your compute and your
keys, and does the work an evaluation engineer would do — calibrate the judges,
run the evals, design the experiments, write the memo.

Every product in this market is capable and most of them are cheap. They also
all assume a human eval engineer exists to design the rubrics, interpret the
numbers and maintain the suites. Below a certain size that person does not
exist, which is why only about a third of teams running AI in production
evaluate it online at all. LangChef is the missing person, not another
dashboard.

> They bring the agent and the compute. We bring the expertise.

---

## Status — M0, the ground

This repository is four days old and deliberately small. M0 exists to make the
decisions that get expensive later and to prove the shape works end to end, not
to ship product.

**Works today**

- `langchef --version`, `langchef contract`, `langchef doctor`, `langchef packs list`
- The output contract: JSON to stdout, narration to stderr, gates as exit codes
- The expertise-pack loader and manifest schema, with one pack resolving
- CI that installs a pinned interpreter, refuses to run if a provider credential
  is visible, and keeps the generated contract document in sync with the code

**Not built yet** — judge running, calibration statistics, the eval workspace,
connectors, the agent layer. See the roadmap below and
[`docs/AGENT-CONTRACT.md`](docs/AGENT-CONTRACT.md) for where each command lands.

---

## Install

[uv](https://docs.astral.sh/uv/) is the only prerequisite. It fetches the
interpreter itself, so no system Python is involved and nothing is installed
globally.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh      # if you don't have it yet
```

Nothing is published and the repository has not been pushed — the name
reservation needs an account, see [`docs/RESERVE-NAMES.md`](docs/RESERVE-NAMES.md).
Until that is done, clone from wherever your copy lives:

```sh
git clone ~/code/github/langchef            # or the GitHub URL, once reserved
cd langchef
uv sync                                     # Python 3.12 + dependencies
uv run langchef doctor
```

A green `doctor` means the interpreter is the pinned one, an expertise pack
resolves, and no provider credential is sitting in your environment.

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
7. tests                                  PASS
8. distribution builds                    PASS
9. wheel runs from a clean env            PASS

9 passed, 0 failed
```

Step 1 comes first on purpose: the suite exercises the deterministic core and
replays recorded judge responses, so a provider key in the environment means a
test could quietly start spending money. Any failure prints the last 25 lines
of that step and exits non-zero.

---

## What it looks like

```console
$ langchef doctor                 # stderr — written for you
ok   python       3.12.14 (supported: 3.12, 3.13)
ok   uv           /home/dk/.local/bin/uv
ok   packs        genai-rag@0.1.0
note workspace    no evals/ here — run langchef init (M3)
ok   credentials  0 provider key(s) present: none
doctor: ok
```

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
  judge/        runner, cache, providers.py            (M2)
  connect/      duckdb-first read-only connectors      (M3)
  workspace/    formats, ledger, run directories       (M3)
  render/       memo markdown + ledger html            (M3)
  packs/        loader + manifest schema — the boundary
packs/genai-rag/    the first expertise pack
adapters/           harness packaging — disposable      (M4)
dogfood/            RAG app, traffic generator, planted regressions
```

One rule holds the design together: **`core/` imports nothing from `judge/`,
`connect/` or `packs/`**, and is stdlib-only until M1 brings numpy and scipy in
deliberately. Both halves are enforced by `tests/test_boundaries.py`, which is
what makes every number in the product testable with no API key and no network.

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
| **M0** | Ground | This repository: decisions, contract, toolchain, CI |
| M1 | Calibration math | Judge–human agreement — TPR, TNR, Cohen's κ, disagreement taxonomy. No LLM |
| M2 | Judge runner | Batched scoring, content-addressed cache, two-tier escalation, pins |
| — | *Gate* | *Three design partners committed to a paid pilot* |
| M3 | Workspace | `langchef init`, file formats, run ledger, decision memos |
| M4 | Agent layer | Claude Code plugin, calibration playbook as a skill, gate one enforced |
| M5 | Unattended | Scheduling, weekly recalibration, spend caps, the quality ledger |
| M6 | Job one | Eval suites, baselines, variance-derived thresholds, triage |

Calibration comes first on purpose. A judge is a measuring instrument, not a
metric; an eval suite built on an uncalibrated judge produces confident garbage,
and no amount of downstream statistics repairs it.

---

## Background

- [The Eval Gap](https://claude.ai/code/artifact/b9301ac6-23d0-4cbc-a7bc-980c3c31c3a4) — market analysis: who serves this today and why a gap survives cheap, capable tooling
- [LangChef 2.0](https://claude.ai/code/artifact/0acce76f-c204-48a9-85d2-0f62d39a62b1) — the PRD: users, requirements, approval gates, success metrics
- [Build Order](https://claude.ai/code/artifact/b3e1d521-3f23-475d-8a63-b46c507860f1) — the engineering sequence this repository follows
- [`DECISIONS.md`](DECISIONS.md) — nine calls made before the first commit
- [`docs/AGENT-CONTRACT.md`](docs/AGENT-CONTRACT.md) — generated; what the agent may read, write, spend and decide

The 1.0 platform lives on at
[`langchef-legacy`](https://github.com/deepskandpal/langchef-legacy). Its
vocabulary carried over; its code did not.

---

## Licence

Apache-2.0 for the CLI and the workspace format — see [`LICENSE`](LICENSE).
Expertise packs are separately licensed.

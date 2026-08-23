# Decisions

Nine calls made on **23 August 2026**, before the first line of product code, from
§3 of the [Build Order](https://claude.ai/code/artifact/b3e1d521-3f23-475d-8a63-b46c507860f1).

Each was cheap that day and expensive six weeks later. They are recorded here so
they are not relitigated. Reopening one is allowed; doing it without writing a
new dated entry underneath is not.

---

## 1. New repository. The 1.0 code is reference material.

**Closed.** A fresh `langchef` repo; the 1.0 working copy moved to
`langchef-legacy` and its GitHub remote renamed to match.

The autopsy concluded the platform code is not a base to build on. Keep the
name and the vocabulary — prompts, datasets, experiments, results — and keep
nothing else. Cheap to reverse today, impossible to reverse once the new repo
has history.

## 2. Python 3.12, pinned by uv. Not the system 3.14.

**Closed.** `.python-version` holds `3.12`; `requires-python = ">=3.12,<3.14"`.

Scientific wheels — scipy, statsmodels, duckdb, pyarrow — trail a new CPython
release by months. On 3.14 the first afternoon of M1 goes on source-building
numerical libraries instead of writing the product. The upper bound encodes the
decision literally and is one character to widen when the wheels land.

## 3. typer, and one output rule: JSON to stdout, human text to stderr.

**Closed.** No `--format` flag, now or later. `--help` is the single exception,
because it is written for people.

The agent parses stdout and the person reads stderr, so neither mode is an
afterthought bolted onto the other. Format flags proliferate and then diverge.

## 4. Text is the record. Parquet for bulk. DuckDB is a query engine, never the store.

**Closed.** TOML config, JSONL goldens and labels, Markdown judges and findings,
JSON baselines. Parquet only for per-example scores. DuckDB reads those files.

The whole trust story is that a person can review a workspace in a pull request.
A database file in git is a black box, and a black box in git is the same
product everyone else already sells.

## 5. The pack loader exists from day one.

**Closed.** `src/langchef/packs/` ships in the first commit with exactly one
pack, `genai-rag`, resolved through a manifest on a search path.

The single most expensive decision to reverse. If pack logic leaks into the
core, the core can never be open-sourced and the moat can never be sold
separately. Enforced by `tests/test_boundaries.py` rather than by discipline:
`core/` may not import `judge/`, `connect/` or `packs/`.

## 6. One provider shim. Nothing else imports a provider SDK.

**Closed.** `src/langchef/judge/providers.py` will wrap litellm from M2. No
other module may import it.

Customers bring their own keys across providers, so breadth matters; litellm
churns, so containment matters more. One file to rewrite if it goes bad.

## 7. numpy and scipy, hand-rolled statistics, `confseq` for always-valid bounds.

**Closed.** scikit-learn only for `cohen_kappa_score` and confusion matrices.
Every statistic ships with a known-answer test against an independent
implementation or a closed form.

The statistics engine is a differentiator, so it has to be readable and testable
rather than delegated to a framework. Until M1 brings them in deliberately,
`core/` is stdlib-only — and a test asserts it.

## 8. Apache-2.0 for the CLI and the workspace format. Packs proprietary.

**Closed.** This is decision 5's justification, and deciding it now is what makes
the module boundary real rather than aspirational.

## 9. Two-tier judging from the start.

**Closed.** A cheap model scores everything; a strong model re-scores only
boundary and disagreement cases.

Not an optimisation to add later. The model pin is part of the judge cache key,
so retrofitting tiering invalidates every cached judgement in every workspace.
It costs an hour in M2 and a migration afterwards.

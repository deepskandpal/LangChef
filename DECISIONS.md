# Decisions

Nine calls made on **23 August 2026**, before the first line of product code, from
§3 of the Build Order, the engineering plan this repository follows.

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

### Amended 23 August 2026 — the repository was reused, not created fresh.

**Reopened and closed differently.** The new code was force-pushed over
`deepskandpal/LangChef`, replacing the 1.0 history in place. The rename to
`langchef-legacy` never happened.

What held: the 1.0 code is reference material and none of it carried over. What
changed: keeping the old repository keeps the name, the URL and whatever
inbound links exist, and the alternative — a second repository with a worse name
— was paying a permanent cost to preserve a history nobody was going to read.
The 1.0 history is not lost; it is a full clone on the author's machine at
`b6fe9f0`, and restoring it is one push.

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

---

## 10. Open source from the start. No paid-pilot gate.

**Decided 23 August 2026.** Apache-2.0, public repository, published before the
product is finished.

The Build Order gated M3 on three design partners committed to a paid pilot.
That gate is withdrawn. Asking for money before anyone can see the thing work
inverts the order: this is a tool whose entire claim — that it finds regressions
a team would otherwise ship — can be demonstrated in a clone, offline, in about
a minute. Let it be demonstrated. Value first, commitment after.

This does not reopen #8. The core is Apache-2.0 and the expertise packs are
still separately licensed, and #5's module boundary is what keeps that possible.
What changed is the sequencing of the commercial ask, not the licence split —
though the split is now worth revisiting on its own terms, since the wedge is a
tool people adopt rather than a pilot they buy.

## 11. Comparisons are paired, and the null result carries a number.

**Decided 23 August 2026**, when `compare` was pulled forward from M6 to M3 to
make the loop runnable end to end.

Both arms of an eval experiment score the same goldens, so the pairs are the
unit: exact McNemar over the discordant pairs, not a two-sample proportion test.
Treating the arms as independent throws the pairing away and inflates the
variance, which is a reliable way to answer a question nobody asked with great
confidence while real regressions come back "not significant".

The second half matters more. Every inconclusive result is reported with the
minimum detectable effect, computed from the *discordant* rate rather than the
pass rate, because that is what carries the information under McNemar. "No
significant difference" on its own is not a finding; "no difference we could
see, and this run could not have resolved anything under six points" is. The
dogfood exists partly to keep this honest: one of its three planted regressions
is deliberately below what the sample can resolve, and the test suite asserts
that LangChef says so rather than reporting a clean bill of health.

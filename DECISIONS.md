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

## 12. Task classes reduce where reduction is free. One continuous path, in `compare` only.

**Closed 30 August 2026.** #18 asked whether to reduce every BYOD task class to
pass/fail at ingestion, or generalise the deterministic core. Neither, as posed.

Map the core to the classes and the question dissolves. `agreement.py`,
`taxonomy.py` and `sampling.py` are the **calibration** half, and calibration
only applies where the target is free text and a judge has to be trusted. Three
of the four task classes have a hard target, so those three modules never see
them. They stay binary, unchanged, and their forty-one dependent test files never
move.

`compare.py` and `design.py` are the **experiment** half and every class needs
them. Per example:

| Class | Outcome | Reduction cost |
|---|---|---|
| `qna` / `generation` | judge says pass or fail | none, already binary |
| `classification` | `predicted == ideal` | **none, that is the outcome** |
| `retrieval` | recall@k, MRR, nDCG | **total, and unacceptable** |
| `reranking` | nDCG, MAP | same |

Classification is the case that makes the point. "Correct or not" is not a
reduction of a multi-class label, it is the comparison you actually want, and
McNemar on it is exact. Multi-class κ would only matter for two humans
disagreeing with each other, which is not something this tool does.

Retrieval is the case that makes the other point. Recall 0.42 and 0.71 are both
"fail" against a threshold of 0.8, and the difference between them is the entire
finding. So retrieval and reranking get a **paired comparison over continuous
scores**, and that is the only generalisation anywhere in the core.

**Consequences.**

- One new continuous paired path in `compare.py`, and a matching detection limit
  in `design.py`. The waiter currently sizes every experiment from the discordant
  rate, which is a binary concept; pointed at a retrieval arm it would size
  confidently using arithmetic that does not apply.
- `calibrate`, `taxonomy` and `label plan` **refuse at exit 2** on a class with no
  judge, naming the class, rather than computing a κ that means nothing. A number
  with no meaning is worse than a refusal, because somebody will quote it.
- Where a threshold is genuinely needed, it lives in the pre-registration and is
  therefore under gate two. Editing it revokes approval, which is the whole point
  of the gate.
- Multi-class κ is a non-goal until something needs it.

**What this rejects.** Reducing everything (option a) would have hidden a
threshold in a loader where nobody reviews it, which #18 named as the likely
default and the outcome it existed to prevent. Generalising everything (option b)
would have rewritten the most heavily tested code in the repository to serve
three classes that never touch it.

## 13. One label budget buys diagnosis. Estimation is a separate mode, and it is allowed to refuse.

**Closed 2 September 2026.** #60 asked what a single label budget buys: an
estimate of the judge, a diagnosis of the rubric, or both from separate samples.
The answer is C, split the budget, with one amendment the coverage evidence
forced: at the budget this product is built around, only the diagnosis half is
affordable, so the estimation half is opt-in and refuses rather than guesses.

**Two separate faults, found in that order.**

The first is selection. `sampling.plan()` stratifies by the judge's verdict and
then takes the *lowest-confidence rows deterministically* inside each stratum;
the hash only breaks ties. A row's inclusion probability is therefore 0 or 1
given its confidence rank, not `n_h/N_h`. `Selection.weight` records `N_h/n_h`
and reads like a Horvitz-Thompson inclusion weight. It is not one.
Post-stratification corrects allocation *between* strata and cannot recover a
population rate when selection *inside* a stratum tracks the quantity being
measured, which confidence does almost by construction, since low confidence is
where judge and human part.

The second is estimation, and it survives fixing the first. A seeded coverage
check supplied genuine simple random samples without replacement, which is
exactly what fixing selection would give, and the interval still failed:

| Labels per stratum | TPR coverage | Kappa coverage |
| ---: | ---: | ---: |
| 10 | 43.35% | 64.05% |
| 20 | 63.85% | 74.10% |
| 40 | 86.70% | 88.00% |
| 80 | 90.55% | 93.95% |

Nominal was 95%. TNR covered 2,000 out of 2,000 at every budget, which is a
failure and not a pass: at a true TNR of 0.9942 the interval is so wide it cannot
miss and carries no information. One method wrong in two directions at once is
not repairable by a single correction.

The reason is structural. TPR is `TP / (TP + FN)`, and `TP` is estimated from the
judge-fail stratum while `FN` is estimated from the judge-pass stratum. It is a
ratio of two weighted totals from different strata, with a random denominator
dominated by the stratum sampled at one in ninety. Kish effective-n treats the
weighted sample as an unweighted sample of size `n_eff` from one population,
which is the wrong variance for that shape.

**What is decided.**

The default path keeps uncertainty-first selection, drops the weight, and makes
no population claim. Kappa and TPR are reported as what they are: screening
statistics measured on the cases the judge was least sure about. Selecting the
hardest rows biases agreement downward by construction, so the number is
conservative for the question anyone actually asks of it, which is whether this
judge can be trusted at all. That is a design argument and not a theorem, so the
claim stays directional and no interval is attached to it.

Estimation becomes a separate, opt-in mode that draws without replacement inside
each stratum, and **refuses at exit 2** when the budget cannot support the width
asked for, naming the budget that could. This is decision 12's rule applied to
the same problem: a number with no meaning is worse than a refusal, because a
refusal is read once and a number is repeated.

The Kish shortcut is removed either way, replaced by a stratified bootstrap over
the actual design. That fixes the variance formula. It does not fix the small
sample, and the budget at which it reaches nominal coverage is an open empirical
question that the same harness can settle.

**What this rejects.** Option A, random sampling within every stratum by default,
buys valid point estimates and, per the table above, still does not buy a valid
interval at any affordable budget. It pays for that by giving up the selection
rule that exists because labels are the scarce input: a case the judge was unsure
about separates two rubrics and a confident one usually does not. That trades the
thing that is cheap and useful for the thing that is expensive and out of reach.
Option B, keeping the current selection and declaring the estimates model-based,
was already weak because its assumption of within-stratum exchangeability is
known to be false, and the coverage evidence then killed it on arithmetic.

**Consequences.**

- Nothing shipping today is wrong. `Selection.weight` is written by `plan()` and
  read by nothing; `agreement()` is unweighted. This governs what gets built.
- `Selection.weight` is removed, or renamed so that nothing can mistake it for an
  inclusion probability again.
- #30 re-scopes to the default path only and stays with @LunaMeerkats. The opt-in
  estimation mode becomes a separate issue.
- The coverage simulation enters the test suite, seeded and fast, so the next
  version of this mistake fails a test rather than a review.
- `docs/ref-agreement.html` already carries the limitation in its strong form. Its
  closing sentence, that the question is open, is what changes here.
- Found by @LunaMeerkats on #30, who stopped before opening a pull request rather
  than shipping it, then produced the coverage sweep that decided the amendment.

## 14. Nothing reaches `main` without a pull request and one maintainer review.

**Closed 2 September 2026.** Direct commits to `main` end with the change that
records this. Every piece of issue work, from any contributor and from the
maintainer, goes on a branch and through a pull request that at least one
maintainer reviews.

The reason is the same one that produced decision 13 and every other defect this
repository has caught late. The failure mode here is a plausible wrong number: it
does not crash, it does not fail a test nobody wrote, and it reads exactly like a
right number. Review is the only control that has actually caught those. A
minimum detectable effect computed with an unpaired formula, a readout that
silently picked the newest run, an inclusion weight that was not one: none of
those were caught by CI, and all three were caught by somebody reading the
change. A rule that applies to contributors and not to the person merging is not
a review culture, it is a queue.

The weekday loop this serves: prioritise from `lifecycle:spec`, `lifecycle:ready`
and `lifecycle:blocked`, then dispatch the ready work to several agents at once.
The area labels are what keep that from colliding, and the pull request is what
keeps the output reviewable. Parallel agents make the review bar more necessary,
not less, because volume is exactly the condition under which a plausible wrong
number gets waved through.

**Consequences.**

- Branch, push, open a pull request, and let CI run. `main` is not a working
  branch for anyone.
- The maintainer's own changes are reviewed too. Self-merge after CI is green is
  acceptable when no other reviewer is available, and the pull request still
  exists so the change is readable afterwards.
- Repository documentation that is not issue work, such as this file, follows the
  same path from here.

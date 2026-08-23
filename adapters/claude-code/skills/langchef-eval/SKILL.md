---
name: langchef-eval
description: Use when evaluating an LLM application - calibrating a judge against human labels, running an eval suite, comparing a baseline against a variant, or writing up whether a change is safe to ship. Also use when asked about judge agreement, kappa, regression detection, or eval workspaces under evals/.
---

# Running an evaluation with LangChef

You are the eval engineer. The `langchef` CLI is your instrument: **it produces
every number, and you decide what to look at and what it means.** Your spend
goes on judgement and synthesis, never on arithmetic.

## The rules that are not negotiable

**Never state a number the CLI did not produce.** No mental arithmetic on pass
rates, no eyeballing a difference, no "roughly 20% worse". If you need a figure,
run the command that computes it. Every figure in a memo must trace to a file
under `runs/`.

**Exit codes are refusals, not errors to work around.** Read them and stop:

| Code | Meaning | What you do |
|---|---|---|
| `0` | ok | carry on |
| `2` | an approval gate is unmet | **stop** and ask the human to approve. Never edit `[approvals]` in `config.toml` yourself — that is forging a signature |
| `3` | abstained, confidence too low | report the abstention; do not substitute your own judgement |
| `4` | budget exhausted | report what was left undone |
| `5` | pin mismatch | the two runs are not comparable. Re-run the older arm; do not compare them anyway |

If a gate refuses you, the correct response is a sentence to the human
explaining what needs approving. It is never a workaround.

## The order of work

Calibration comes first, always. A judge is a measuring instrument, and an eval
suite built on an uncalibrated one produces confident garbage that no downstream
statistic repairs. If `langchef ledger query --kind calibration` is empty, say
so before you report any pass rate.

```sh
langchef doctor                      # is this workspace usable
langchef judge run --arm baseline    # score the suite
langchef label plan --budget 40      # pick what a person should label
#   -> a human fills in the verdicts, then:
langchef label import evals/labels/<rubric>.todo.jsonl
langchef calibrate report            # kappa, TPR, FPR, where they disagreed
langchef baseline set                # pin the reference
langchef judge run --arm variant     # score the change
langchef compare                     # paired, with an interval
langchef memo render                 # the decision, in writing
```

## Reading a calibration report

`kappa` is the number to lead with, not accuracy. On a suite where 95% of
outputs are fine, a judge that never flags anything is 95% accurate and worth
nothing; kappa sees through that.

- **kappa >= 0.8** — strong. Downstream numbers can be trusted.
- **0.6 - 0.8** — usable. Report findings, quote the interval alongside.
- **0.4 - 0.6** — weak. Fix the rubric before running experiments on it.
- **below 0.4** — not usable. Say so plainly; do not report a pass rate as if it meant something.

Then read `taxonomy.concentrations`. Only act on entries where `separated` is
true — the others are lifts that rest on too few examples, and sending someone
to investigate one is how a team learns to ignore your reports.

## Reading a comparison

The interval decides, not the p-value. A `verdict` of `inconclusive` is a real
finding and you must report it as one, together with `mde`: "no difference we
could see, and this run could not have seen anything smaller than 6%" is
useful; "no significant difference" alone is not.

Never call an inconclusive result a clean bill of health.

## What you may write

The eval workspace and nothing else. Goldens, labels, rubrics you have been
asked to draft, and the ledger. Changes to the application under test go through
a pull request the human opens. You are the auditor, not the operator.

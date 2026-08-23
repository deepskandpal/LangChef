# Dogfood

A small retrieval-augmented app with known ground truth, used to test LangChef
itself. Deterministic and offline: no model, no network, no unseeded randomness.

The point is not to build a good RAG system. It is to have one whose failures we
planted ourselves, so we can ask whether the harness detects them — and, more
usefully, find out where it does not.

## What is planted

| Arm | Knob | True effect | What breaks |
|---|---|---|---|
| `baseline` | — | — | 25% of answers are correct but reworded |
| `stale-index` | `drop_every=5` | **-20 pp** | documents missing from the index |
| `eager-hedging` | `hedge_below=0.35` | **-10 pp** | the app declines when it should answer |
| `truncated-context` | `chunk_chars=90` | **-3.3 pp** | the fact is cut off mid-chunk |

The effect sizes are spread on purpose. A dogfood where every planted regression
is obvious proves only that the harness can see obvious things. The third one is
smaller than 90 goldens can resolve, and the *required* result for it is an
inconclusive verdict quoting the minimum detectable effect — a harness that
reported a clean bill of health there would be worse than useless.

The baseline's paraphrasing is the other half. Those answers are correct and a
person reads straight through them; a token-overlap judge does not. That blind
spot is what the calibration step is supposed to surface before anyone trusts a
pass rate.

## Run it

```sh
uv run python -m dogfood.build          # corpus, goldens, ground-truth labels
cd dogfood/workspace

langchef approve rubric                 # gate one: a person signs off the rubric
langchef judge run --arm baseline --run-id support-baseline
langchef label plan --budget 40
cd - && uv run python -m dogfood.label \
    dogfood/workspace/evals/labels/answer-quality.todo.jsonl
cd dogfood/workspace

langchef label import evals/labels/answer-quality.todo.jsonl
langchef calibrate report --run support-baseline
langchef baseline set --run support-baseline

for arm in stale-index eager-hedging truncated-context; do
  langchef judge run --arm "$arm" --run-id "support-$arm"
  langchef compare --variant "support-$arm"
  langchef memo render --run "support-$arm"
done
```

`dogfood/label.py` stands in for the person. Those labels are ground truth the
harness planted and therefore knows — not a second model's opinion. If a model
produced both sides, the agreement figure would measure one model's
self-consistency and nothing else.

## The self-test

`tests/test_dogfood.py` asserts the whole claim without any of the above:

- the planted effects are the size the labels say they are
- the two large regressions are detected, with the measured effect landing on the planted one
- the small one comes back **inconclusive**, with an MDE larger than the effect
- calibration finds the paraphrase blind spot as false alarms
- the same inputs produce the same verdicts on any machine

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
| `chunk-size-doubled` | `docs_per_chunk=2 chunk_chars=480 top_k=2` | **-7.8 pp**, and **-14.4 pp** of retrieval recall | the chunk vector is diluted and the gold document stops reaching the prompt |
| `embedding-swap` | `embedder=minilm-small tail_noise=1.10` | **-12.2 pp** overall — **-33.3 pp** on tail queries, **0.0 pp** on head | a different vector space, worse on rare vocabulary |
| `temperature-0.9` | `temperature=0.9` | **0.0 pp**, and **16x** the between-call variance | the wording will not sit still between calls |
| `hallucinated-detail` | `embellish_every=6` | **-14.4 pp**, all of it on **Groundedness** | the app invents a clause that is in no document |

The effect sizes are spread on purpose, and so are the *shapes*. A dogfood where
every planted regression is a large drop in a single mean proves only that the
harness can subtract. Three of the six demand a different answer:

- `truncated-context` is smaller than 90 goldens can resolve, and the *required*
  result is an inconclusive verdict quoting the minimum detectable effect. A
  harness that reported a clean bill of health there would be worse than useless.
- `embedding-swap` leaves head queries untouched and takes a third of the tail.
  "Quality fell by 12 points" is true, and a miss. The finding is a slice.
- `temperature-0.9` does not move ground truth at all — not on average, but in
  every single trial, by construction. A comparison of means reports nothing,
  correctly, and the damage is real. It is the case that justifies reporting a
  spread at all.

The baseline's paraphrasing is the other half. Those answers are correct and a
person reads straight through them; a token-overlap judge does not. That blind
spot is what the calibration step is supposed to surface before anyone trusts a
pass rate.

## How each knob works

The mechanism matters as much as the size, because a knob that looks like a knob
and changes nothing is worse than no knob: it makes the rig lie about its own
sensitivity. That already happened here once. The first retrieval knob set
`top_k=1`, and the app answered from `retrieved[0]` whatever `k` was, so every
answer in the arm was the answer the baseline gave and the rig reported a
detector that could not miss.

**Every knob below was run before it was written down, and every planted number
here is a measured one.**

### `stale-index` — documents missing from the index

Every fifth document is dropped before retrieval. Nothing about the app is
broken; every answer that needed a missing document is now wrong. The most
boring production regression there is.

### `eager-hedging` — the app declines when it should answer

The reader's confidence threshold moves from 0.20 to 0.35, so answers it used to
give it now refuses. Fails the rubric on Directness rather than Correctness,
which is what makes it a different *shape* of finding from `stale-index` at a
similar size.

### `truncated-context` — the fact is cut off mid-chunk

Each retrieved chunk is clipped to 90 characters instead of 240, so a fact that
sits at the end of its document does not survive into the prompt. It costs three
answers out of ninety. **This is deliberately below the detection limit and must
stay there.** Its value to the rig is entirely in being unresolvable: it is the
only arm that proves the harness declines to claim a finding it cannot support.

### `chunk-size-doubled` — the chunk vector is diluted

Chunks hold two documents instead of one, and the context budget does not
change, so half as many chunks fit in it (`top_k` 4 → 2, `chunk_chars` 240 →
480: the same 960 characters of prompt).

The retriever scores a chunk by **mean-pooling its documents' scores**, which is
what a dense retriever does when it embeds a chunk as one vector: a chunk holding
two facts sits about half way between them and is about half as close to a query
about either. The noise floor does not shrink with it, so the signal-to-noise
ratio of the ranking falls and the gold document drops out of the top *k*.

The reader is deliberately left alone — it has the text in front of it, not a
pooled vector, so it still picks the right document out of a chunk it was given.
That keeps this a retrieval regression and nothing else, instead of quietly
moving the hedge threshold as well and making two knobs out of one.

Two things move, and the gap between them is the point:

| | baseline | doubled |
|---|---|---|
| gold document reaches the prompt | 96.7% | 82.2% |
| mean answer length | 73 chars | 142 chars |
| true pass rate | 83.3% | 75.6% |

Retrieval loses 14.4 points. Only about half of that survives into a wrong
answer, because a chunk that holds the wrong fact still sometimes holds enough
of the right words — so the end-to-end effect is 7.8 points, under what 90
pass/fail goldens can resolve. **The required verdict on the pass rate is
therefore `inconclusive`, and it is not a failure of the tool.** It is the case
where the honest report is "retrieval is broken, and this suite is the wrong
instrument to prove it, so go and measure retrieval".

### `embedding-swap` — a different vector space, worse on rare vocabulary

The retriever swaps to a smaller model. The planted defect is the ordinary one:
the smaller model matches the larger on vocabulary it saw constantly and loses
the rare words first. So the arm re-draws its retrieval error in a *different*
space, with a wider spread, **for tail queries only** — head queries land in
exactly the place they landed before, and their verdicts are not merely similar
but identical, with zero discordant pairs.

Head and tail are not labels invented for the occasion. A question is `head` when
one of its content words appears in at least three corpus documents — "account",
"payment", "return", "delivery" — and `tail` when it is carried by words the
corpus barely uses: "restocking", "timeout", "phishing". That is 57 head and 33
tail questions, and it ships as a `frequency` slice on every golden.

| slice | n | planted effect |
|---|---|---|
| head | 57 | **0.0 pp** |
| tail | 33 | **-33.3 pp** |
| all | 90 | **-12.2 pp** |

The aggregate is detected. That is the trap: a harness that stops there reports
"quality fell by 12 points" and sends someone to look at the reader, the rubric
and the prompt, when a third of one slice fell off a cliff and the rest of the
traffic never moved.

### `temperature-0.9` — the wording will not sit still

Sampling temperature goes from 0.2 to 0.9. A quarter of answers come out
reworded at *either* temperature — that rate is `paraphrase_every` and
temperature does not touch it. What temperature changes is whether the same
question is worded the same way the second time it is asked.

The chance that a call departs from its modal wording is the softmax of the
wording margin at the sampling temperature, `1 / (1 + exp(1.0 / T))`, which is
how a decoder actually behaves: **0.7% at T=0.2 and 24.8% at T=0.9, a factor of
37.** Reading temperature linearly would have put them a factor of 4.5 apart and
the knob would have been almost invisible — which is what the first version of
it did, and it measured a variance ratio of 1.4.

Because only the wording moves, **ground truth is identical in every trial**, not
just on average. So:

| over 120 calls | baseline (T=0.2) | T=0.9 |
|---|---|---|
| true pass rate, every call | 83.3% | 83.3% |
| measured pass rate, mean | 83.35% | 83.47% |
| measured pass rate, sd between calls | **0.29 pp** | **1.14 pp** |
| distinct pass rates over the 24 calls the test runs | 2 | 6 |

**Variance ratio 16.0, sd ratio 4.0** — against 37 in the departure probability,
because only some rewordings cross the judge's containment threshold. The
estimate off the 24 calls the test runs is 16.7; the assertion is a floor, since
an F ratio on 24 draws is wide.

A paired comparison of means is inconclusive on every single trial, and stays
inconclusive when all 24 trials are pooled into 2,160 pairs with a minimum
detectable effect of 0.8 pp. Nothing is wrong with that statistic. It is
measuring the wrong thing, and **there is nothing else in the rig that would
catch a tool for ignoring variance.**

The knob is repeatable *and* reproducible: a trial is a pure function of its
number, so trial 7 is the same call on every machine and in every process.

### Not yet planted: covariate shift

Build order §8 names a fourth knob — a covariate shift that degrades a
classifier, whose signature is that slice accuracy falls before aggregate
accuracy does. It needs a text classifier to degrade, and the rig has no
classification task yet. It is blocked on
[#14](https://github.com/deepskandpal/LangChef/issues/14) and
[#20](https://github.com/deepskandpal/LangChef/issues/20), not skipped.

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

for arm in stale-index eager-hedging truncated-context \
           chunk-size-doubled embedding-swap temperature-0.9; do
  langchef judge run --arm "$arm" --run-id "support-$arm"
  langchef compare --variant "support-$arm"
  langchef memo render --run "support-$arm"
done
```

`dogfood/label.py` stands in for the person. Those labels are ground truth the
harness planted and therefore knows — not a second model's opinion. If a model
produced both sides, the agreement figure would measure one model's
self-consistency and nothing else.

`temperature-0.9` has no signature in that loop, by construction — one call
cannot show a spread. Build repeated calls instead:

```sh
uv run python -m dogfood.build --trials 24    # writes baseline.t01 … temperature-0.9.t23
```

and judge `baseline.tNN` against `temperature-0.9.tNN`. Every comparison of
means will come back inconclusive. That is the correct answer and the useless
one, which is the whole reason the arm exists.

## The self-test

`tests/test_dogfood.py` asserts the whole claim without any of the above:

- the planted effects are the size the labels say they are, on every arm
- the three large regressions are detected, with the measured effect landing on
  the planted one
- the small one comes back **inconclusive**, with an MDE larger than the effect
- the chunking knob's retrieval loss is recovered at the retrieval layer, and
  its pass-rate verdict is honestly inconclusive
- the embedding swap moves the tail and leaves the head with **zero** discordant
  pairs, so slice attribution has something to find
- the temperature knob leaves ground truth untouched in every trial, a means-only
  comparison reports nothing on all 24 of them and on the pooled 2,160 pairs, and
  the between-call variance still rises by more than an order of magnitude
- calibration finds the paraphrase blind spot as false alarms
- the same inputs produce the same verdicts on any machine

### `hallucinated-detail` — the answer says something no document said

The only arm that moves **Groundedness**, and the reason it exists is that
nothing else did.

Every other knob here answers out of a retrieved document. Whatever is wrong
with the answer after that — it came from the wrong document, it was cut off, it
declined — the answer is still grounded in what the retriever handed over. So
across the whole rig the attribution only ever named `Correctness` and
`Directness`, and the sentence the product leads with was arithmetic nobody had
run end to end:

> not "quality dropped 4 points" but **"groundedness dropped 9 points while
> correctness held"**

Every sixth answer now gains an invented clause whose content words appear in no
document and in no expected answer. That is exactly what the groundedness check
looks for: text the app produced rather than retrieved. The requested fact stays
where it was, so `Correctness` is untouched — by construction, and to the
decimal.

| | Effect | Attribution |
|---|---:|---|
| overall | -13.3 pp | regression |
| **`Groundedness`** | **-13.3 pp** | **moved worse** |
| `Correctness` | 0.0 pp | inconclusive |

Ground truth falls 14.4 points rather than 13.3, and the gap is not an error. A
fabricated answer fails ground truth even when the requested fact is also
present, because a person does not read past an invented sentence on the grounds
that the rest was right. The judge catches most of that and not all of it, which
is the sort of thing calibration is for.

# The dogfood rig

Required before M1: a calibration engine with no labelled data is untestable,
and an eval agent with no known regressions cannot be shown to detect anything.

One RAG application over a public documentation corpus and one text classifier,
both emitting OpenInference traces to a local store, both driven by a traffic
generator with a realistic query mix. Roughly 400 generated question–answer
pairs, fifty of them hand-checked as seed ground truth.

Then **regression knobs** — degradations with known true effect, flipped at a
known timestamp:

| Knob | Degrades | Expected signature |
|---|---|---|
| Retrieval top-k 5 → 3 | recall | faithfulness drop concentrated in multi-hop queries |
| Chunk size doubled | precision | retrieval relevance falls, answer length rises |
| Embedding model swap | retrieval | tail queries degrade, head queries unaffected |
| Temperature 0.2 → 0.9 | consistency | variance rises, means barely move — the hard case |
| System prompt adds hedging | usefulness | judge scores *rise* on verbosity-biased rubrics — the Goodhart case |
| Context truncated at 2k | grounding | sharp faithfulness cliff on long documents |
| Covariate shift injected | classifier | slice accuracy falls before aggregate accuracy does |

Because the regressions are planted, the detector can be scored: run each knob
twenty times across a range of effect sizes and measure LangChef's own
true-positive rate at a fixed false-alarm budget. That curve sets the
variance-derived thresholds, and no vendor in this market publishes one.

# Rubric library — `genai-rag`

Empty **for now**, which is not the same thing as empty on purpose.

Both classes this pack serves — `qna` and `generation` — score free text, so
both declare `requires_judge = true` in [`../pack.toml`](../pack.toml). They need
rubrics; the shipped ones land with the calibration procedures (M1/M2), and
until then a workspace uses the starter rubric that `langchef init` writes.

Contrast [`../../classification/rubrics/README.md`](../../classification/rubrics/README.md),
which is empty and always will be.

A rubric added here must also be listed in `[contents].rubrics` in the manifest,
or the pack will not resolve — a rubric nobody declared is a rubric nobody
reviewed.

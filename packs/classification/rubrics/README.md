# Rubric library — `classification`

**Deliberately empty, and expected to stay that way.**

A rubric is how a judge is told what "good" means when the target is free text
and there is no other way to score an answer. A classification example has a
hard target: the row carries `ideal`, the system under test produced
`predicted`, and the outcome is `predicted == ideal`. There is nothing for a
judge to have an opinion about, so this pack declares
`requires_judge = false` for its one class and ships no rubrics
(DECISIONS.md #12).

That has consequences worth stating here, because they look like missing
features otherwise:

- **No calibration.** `calibrate`, `taxonomy` and `label plan` are the
  judge-trust half of the product. With no judge there is nothing to trust and
  nothing to calibrate.
- **No κ.** Cohen's κ measures how much two *raters* agree beyond chance. Here
  there is one hard label and no second rater. Multi-class κ is a non-goal, and
  [`NON-GOALS.md`](../../../NON-GOALS.md) records why.
- **The metrics are counting, not inference.** Accuracy, and precision and
  recall per class, computed in [`../metrics.py`](../metrics.py).

If this directory ever fills up, something has gone wrong: either a rubric was
put in the wrong pack, or this pack grew a class that scores free text — in
which case that class declares `requires_judge = true` and the emptiness stops
being the invariant `tests/test_packs.py` checks.

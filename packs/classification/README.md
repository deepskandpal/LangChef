# `classification` — the second pack

Text classification against a labelled set: intent routing, safety labels,
support triage, anything where a row already carries the answer.

It exists for two reasons. The first is that a classification team is the
cheapest possible first contact — they have a labelled dataset already, so there
is nothing to label and nothing to calibrate ([#14](https://github.com/deepskandpal/LangChef/issues/14)).
The second is that this repository had exactly one pack for its whole life, which
means the boundary `DECISIONS.md` #5 calls the most expensive decision to reverse
had never once been exercised. A second pack is the test.

## What it declares

| | |
|---|---|
| Task class | `classification` |
| Outcome | `predicted == ideal` — binary natively, nothing reduced on ingestion |
| Schema | required `example_id`, `input`, `predicted`, `ideal`; optional `slices` |
| Metrics | accuracy, per-class precision and recall, support |
| Judge | **none.** A hard target needs no judge, so no rubric and no calibration |
| Reporting | [`metrics.py`](metrics.py), resolved from `pack.toml` |

Everything above is in [`pack.toml`](pack.toml), which is the whole point: the
manifest is where a task class is defined, and `src/langchef/core/` never learns
that the word `classification` exists.

## The empty rubric library

[`rubrics/`](rubrics/) is empty and says so at length. `requires_judge = false`
in the manifest is the machine-readable half of the same statement, and
`tests/test_packs.py` holds the two together: a pack with no judged class may not
ship a rubric, and its library has to carry a README explaining the emptiness. An
empty directory is otherwise indistinguishable from unfinished work.

## Adding a third class

Copy this directory. A pack is a `pack.toml`, a `rubrics/` library, and
optionally a Python file for reporting the core does not produce. Nothing under
`src/` changes, nothing is registered, and `langchef packs list` picks it up from
the search path — `$LANGCHEF_PACK_PATH`, then `evals/packs`, then this directory.
`tests/test_packs.py::test_a_third_class_is_a_directory_not_a_patch` builds one
from scratch in a temporary directory to prove it.

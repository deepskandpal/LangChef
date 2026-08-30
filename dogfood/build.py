"""Build the dogfood workspace: goldens for every arm, and the labels a person would give.

Run it with ``uv run python -m dogfood.build``. Everything it writes is derived
from ``dogfood/corpus.py`` and ``dogfood/app.py``, so the whole workspace can be
deleted and rebuilt byte-for-byte.
"""

import argparse
from pathlib import Path

from dogfood.app import BASELINE, PLANTED_EFFECT, VARIANTS, Config, run
from dogfood.corpus import documents, questions
from langchef.workspace import scaffold
from langchef.workspace.formats import write_jsonl
from langchef.workspace.paths import WORKSPACE_DIR, Workspace

HERE = Path(__file__).resolve().parent
SUITE = "support"

# The goldens a judge sees. Ground truth is deliberately not among them.
PUBLIC = ("example_id", "question", "answer", "context", "expected", "slices")


def arm_name(config: Config, trial: int) -> str:
    """The goldens label for one call of one arm. Trial 0 keeps the plain name."""
    return config.name if trial == 0 else f"{config.name}.t{trial:02d}"


def write_arm(
    workspace: Workspace, config: Config, asked, suite: str = SUITE, trial: int = 0
) -> dict:
    rows = run(config, asked, trial=trial)
    name = arm_name(config, trial)
    path = workspace.goldens / f"{suite}.{name}.jsonl"
    write_jsonl(path, [{key: row[key] for key in PUBLIC} for row in rows])

    truth_path = HERE / "truth" / f"{suite}.{name}.jsonl"
    write_jsonl(
        truth_path,
        [{"example_id": row["example_id"], "verdict": row["_truth"]} for row in rows],
    )
    passed = sum(1 for row in rows if row["_truth"] == "pass")
    return {
        "arm": config.name,
        "trial": trial,
        "goldens": str(path),
        "truth": str(truth_path),
        "n": len(rows),
        "true_pass_rate": passed / len(rows),
        "config": config.describe(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=HERE / "workspace")
    parser.add_argument(
        "--trials",
        type=int,
        default=1,
        help=(
            "Call every arm this many times, one goldens file per call. The consistency "
            "knob has no signature in a single call by construction — its damage is the "
            "scatter between repeats — so seeing it needs more than one."
        ),
    )
    args = parser.parse_args()

    root = args.dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    workspace = Workspace(root / WORKSPACE_DIR)
    scaffold.create(workspace, name="dogfood-northwind", application_class="genai-rag")

    asked = questions()
    configs = [BASELINE, *VARIANTS.values()]
    arms = [
        write_arm(workspace, config, asked, trial=trial)
        for trial in range(max(1, args.trials))
        for config in configs
    ]
    first = [arm for arm in arms if arm["trial"] == 0]

    print(f"workspace  {workspace.root}")
    print(f"corpus     {len(documents())} documents, {len(asked)} questions")
    if args.trials > 1:
        print(f"trials     {args.trials} calls per arm")
    print()
    print(f"{'arm':<20} {'n':>4} {'true pass':>10} {'planted':>9}   config")
    for arm in first:
        planted = PLANTED_EFFECT.get(arm["arm"])
        planted_text = f"{planted:+.1%}" if planted is not None else "baseline"
        print(
            f"{arm['arm']:<20} {arm['n']:>4} {arm['true_pass_rate']:>9.1%} "
            f"{planted_text:>9}   {arm['config']}"
        )
    print()
    print("Ground-truth labels are in dogfood/truth/ — they stand in for a person.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def write_arm(workspace: Workspace, config: Config, asked, suite: str = SUITE) -> dict:
    rows = run(config, asked)
    path = workspace.goldens / f"{suite}.{config.name}.jsonl"
    write_jsonl(path, [{key: row[key] for key in PUBLIC} for row in rows])

    truth_path = HERE / "truth" / f"{suite}.{config.name}.jsonl"
    write_jsonl(
        truth_path,
        [{"example_id": row["example_id"], "verdict": row["_truth"]} for row in rows],
    )
    passed = sum(1 for row in rows if row["_truth"] == "pass")
    return {
        "arm": config.name,
        "goldens": str(path),
        "truth": str(truth_path),
        "n": len(rows),
        "true_pass_rate": passed / len(rows),
        "config": config.describe(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=HERE / "workspace")
    args = parser.parse_args()

    root = args.dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    workspace = Workspace(root / WORKSPACE_DIR)
    scaffold.create(workspace, name="dogfood-northwind", application_class="genai-rag")

    asked = questions()
    arms = [write_arm(workspace, BASELINE, asked)]
    arms += [write_arm(workspace, config, asked) for config in VARIANTS.values()]

    print(f"workspace  {workspace.root}")
    print(f"corpus     {len(documents())} documents, {len(asked)} questions")
    print()
    print(f"{'arm':<20} {'n':>4} {'true pass':>10} {'planted':>9}   config")
    for arm in arms:
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

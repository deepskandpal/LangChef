"""Answer a labelling plan from ground truth.

This is the one step a real deployment gives to a person. The dogfood knows the
true verdict for every example it generated, so it can fill the plan in and the
whole loop runs unattended — which is what makes the self-test repeatable.

These labels are ground truth, not a second model's opinion. That distinction is
the reason the calibration numbers downstream mean anything: if a model produced
both sides of the comparison, the agreement figure would be measuring one
model's self-consistency and nothing else.
"""

import argparse
from pathlib import Path

from langchef.workspace.formats import read_jsonl, write_jsonl

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("todo", type=Path, help="The plan written by `langchef label plan`.")
    parser.add_argument("--arm", default="baseline", help="Which arm's truth to answer from.")
    parser.add_argument("--suite", default="support")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    truth_path = HERE / "truth" / f"{args.suite}.{args.arm}.jsonl"
    truth = {row["example_id"]: row["verdict"] for row in read_jsonl(truth_path)}

    rows = read_jsonl(args.todo)
    missing = [row["example_id"] for row in rows if row["example_id"] not in truth]
    if missing:
        raise SystemExit(f"no ground truth for {len(missing)} example(s), first: {missing[0]}")

    filled = [
        {**row, "verdict": truth[row["example_id"]], "note": f"ground truth ({args.arm})"}
        for row in rows
    ]
    out = args.out or args.todo
    write_jsonl(out, filled)

    agreed = sum(1 for row in filled if row["verdict"] == row.get("judge_verdict"))
    print(f"labelled {len(filled)} example(s) from {truth_path.name} -> {out}")
    print(f"  the judge already agreed on {agreed}/{len(filled)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

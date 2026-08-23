---
description: Calibrate the judge against human labels and report whether it can be trusted.
argument-hint: "[run-id]"
allowed-tools: Bash(langchef:*), Read, Glob
---

Calibrate the judge in this workspace.

1. Run `langchef doctor`. If a required check fails, stop and report it.
2. Run `langchef calibrate report` (add `--run $1` if a run id was given).
3. If it exits non-zero because there are no labels, run `langchef label plan
   --budget 40`, then stop and tell the human which file to fill in. Do not
   invent labels — labels are the ground truth and a model's guess is not.
4. On success, report in this order: kappa with its interval, TPR, FPR, then
   any concentration where `separated` is true.
5. State plainly whether the judge is strong, usable, weak, or not usable, using
   the thresholds in the `langchef-eval` skill.

Quote no number you did not read out of the command's JSON.

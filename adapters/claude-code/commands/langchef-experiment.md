---
description: Compare a variant against the pinned baseline and write the decision memo.
argument-hint: "<variant-run-id>"
allowed-tools: Bash(langchef:*), Read, Glob
---

Run the experiment readout for variant `$1`.

1. `langchef ledger query --kind calibration --limit 1`. If it is empty, say so
   first — an uncalibrated judge makes everything below provisional.
2. `langchef compare --variant $1`.
   - Exit 5 means the pins moved: report what moved and stop. Do not compare.
   - Exit 0 with `verdict: inconclusive`: report it as an inconclusive result
     **and** quote `mde`. Do not describe it as no regression.
3. `langchef memo render --run $1`.
4. Summarise the memo in three sentences: what was measured, what it showed, and
   what it could not rule out.

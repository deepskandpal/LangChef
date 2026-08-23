---
description: Turn a described change into one or two experiment designs for a human to approve.
argument-hint: "<what changed, in plain language>"
allowed-tools: Bash(langchef:*), Read, Glob
---

Design an experiment for: $1

1. Decide the shape. If they are buying cost or latency and quality merely has to
   hold, this is `--kind non-inferiority` and it needs a `--margin`. If they want
   to know whether something is better, it is `--kind superiority`. **If it is
   non-inferiority and no margin was given, ask for one and stop.**
2. Run `langchef experiment design` with the intent quoted verbatim, the variant
   arm, and the flags from step 1.
3. Report both candidates to the human: how many goldens each needs, the smallest
   effect each could detect, and what it will cost in judge calls. Quote the
   caveats verbatim — especially "these goldens cannot resolve X".
4. Stop. Tell them the exact approve command. Do not run it.

Every number comes from the command's JSON. Do not compute one yourself.

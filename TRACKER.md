# Tracker

**Updated 27 August 2026** · `main` at M1–M4.5 · CI green · 17 of 22 contracted commands live

> **The work now lives in [GitHub issues](https://github.com/deepskandpal/LangChef/issues).**
> This file is the map, not the backlog. It is here so that somebody arriving cold
> knows where they are in about a minute; the issues are where anything actually
> gets picked up, claimed and closed.
>
> [`AGENTS.md`](AGENTS.md) is the working agreement — how work is claimed, which
> areas collide, and what cannot be changed in a pull request.

---

## State of the build

| | Milestone | Status | What exists |
|---|---|---|---|
| M0 | Ground | **done** ([#1](https://github.com/deepskandpal/LangChef/issues/1)) | decisions, contract, toolchain, CI |
| M1 | Calibration math | **done** ([#2](https://github.com/deepskandpal/LangChef/issues/2)) | κ + interval, TPR/TNR/PPV/NPV + Wilson, MCC, taxonomy, label planning |
| M2 | Judge runner | **done** ([#3](https://github.com/deepskandpal/LangChef/issues/3)) | hashed rubrics, provider shim ×3, content-addressed cache, two tiers, pins |
| M3 | Workspace | **done** ([#4](https://github.com/deepskandpal/LangChef/issues/4)) | `init`, formats, runs, ledger, paired `compare`, memos |
| M4 | Agent layer | **done** ([#5](https://github.com/deepskandpal/LangChef/issues/5)) | Claude Code skill + commands, gate one enforced at exit 2 |
| M4.5 | The waiter | **done** ([#6](https://github.com/deepskandpal/LangChef/issues/6)) | `experiment design`/`approve`/`check`/`readout`, pre-registration in TOML, gate two at exit 2, budgets at exit 4 |
| M4.75 | Bring your own dataset | next ([#14](https://github.com/deepskandpal/LangChef/issues/14)) | point at rows you already own; the cheapest first contact available |
| M5 | Unattended | not started ([#16](https://github.com/deepskandpal/LangChef/issues/16)) | scheduling, weekly recalibration, spend caps, connectors + sampling |
| M5.5 | Integrations | not started ([#26](https://github.com/deepskandpal/LangChef/issues/26)) | MLflow first, then Langfuse and OTel GenAI conventions |
| M6 | Job one | not started ([#17](https://github.com/deepskandpal/LangChef/issues/17)) | eval suites, `calibrate diff`, triage, variance-derived thresholds |
| M7 | Experiments | not started | standalone `power` and the remaining integrity checks |

`langchef contract` is the authority on what exists. The table in
`src/langchef/core/contract.py` is where a command's status changes; the five
unbuilt ones are [#42](https://github.com/deepskandpal/LangChef/issues/42)–[#46](https://github.com/deepskandpal/LangChef/issues/46).

---

## Where to look

| I want to | Query |
|---|---|
| pick up work as an agent | [`agent:ready` + `lifecycle:ready`](https://github.com/deepskandpal/LangChef/issues?q=is%3Aopen+label%3Aagent%3Aready+label%3Alifecycle%3Aready) |
| see what is next | [`priority:P0`](https://github.com/deepskandpal/LangChef/labels/priority%3AP0) |
| see what needs a person | [`agent:needs-human`](https://github.com/deepskandpal/LangChef/labels/agent%3Aneeds-human) |
| see what is undecided | [`type:decision`](https://github.com/deepskandpal/LangChef/labels/type%3Adecision) |
| read the build log | [closed issues](https://github.com/deepskandpal/LangChef/issues?q=is%3Aissue+is%3Aclosed) |
| see the plan | [milestones](https://github.com/deepskandpal/LangChef/milestones) |

**The three worth knowing about without opening anything:**

- [#14](https://github.com/deepskandpal/LangChef/issues/14) **BYOD** — probably the highest-leverage item on the list, and blocked on one decision ([#18](https://github.com/deepskandpal/LangChef/issues/18)) that must be settled before any statistics are written, because reversing it later is expensive.
- [#26](https://github.com/deepskandpal/LangChef/issues/26) **MLflow** — the cheapest version of storage, a cross-run index and comparison all at once, in a UI teams already have. Worth doing before [#15](https://github.com/deepskandpal/LangChef/issues/15) in case it makes it unnecessary.
- [#28](https://github.com/deepskandpal/LangChef/issues/28) **Per-criterion comparison** — the most useful thing already sitting unused in the data, and the docs now promise it.

---

## Known limits, deliberately accepted

Not issues. These are true, they are stated in the docs, and they are not going
to change without a new dated entry in [`DECISIONS.md`](DECISIONS.md).

- **The dogfood's "human" labels are ground truth the harness planted**, not
  people. That is what makes the self-test repeatable, and it is stated in
  `dogfood/README.md`. It is not a substitute for a real labelling study.
- **The default judge is token overlap.** It is a real technique and a real
  starting point, and it has a real blind spot — paraphrase — which calibration
  surfaces on purpose. It is not a good judge and does not claim to be.
- **The bootstrap in `compare` is seeded** (`BOOTSTRAP_SEED = 0`). The contract
  calls `compare` deterministic and this is how that is true.
- **Version pinning of the containment judge is manual.** Changing its checks
  means bumping `VERSION` in `providers.py`, because the model string is part of
  the cache key. Nothing catches forgetting — that part *is* an issue,
  [#32](https://github.com/deepskandpal/LangChef/issues/32).

---

## Routine

```sh
./scripts/verify.sh                        # 10 steps; the whole check
uv run pytest tests/test_dogfood.py -v     # the self-test behind the claims
uv run python scripts/build_docs.py        # regenerate docs/ after editing the site
uv run python scripts/render_contract.py   # regenerate the agent contract
```

`verify.sh` runs both generators in `--check` mode, so a stale contract or a
stale docs site fails CI rather than shipping.

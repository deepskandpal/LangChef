# Not building

Written down because every one of these will feel reasonable at some point, and
a scope decision defended from memory is a scope decision already lost.

`never` means it would make this a different product. `not now` has a trigger.

---

## never

**Assignment, feature flagging, or a serving SDK.** Integrate with GrowthBook,
Statsig, PostHog, LaunchDarkly, or whatever the team already runs. Deciding
*which users see which variant* is a solved problem with incumbents; deciding
*whether the variant was better* is not, and that is the whole opening.

**A trace collector or a hosted data plane.** **The absence of a data plane is
the product.** A team can grant read access to a scheduled agent without handing
their production traffic to a vendor — and the moment this stores their data,
that sentence stops being true and the security review starts.

**A model gateway.** One provider shim (`src/langchef/judge/providers.py`),
litellm behind it, and nothing else in the codebase imports a provider SDK. That
is containment, not a product surface.

**A web UI.** The workspace is files and the reviewer is a pull request. This is
the same argument as [`DECISIONS.md`](DECISIONS.md) #4: a database file in git is
a black box, and a black box in git is the same product everyone else already
sells. A dashboard is that black box with a login page.

The distinction worth keeping: **a leaderboard shows which variant won today; the
ledger shows whether the instrument that decided it has been drifting for three
weeks.**

---

## not now

**An agent framework.** The harness is the framework — that was the whole thesis.
`adapters/` stays trivial so that harness churn is an afternoon rather than an
existential risk.

**A labelling interface.** *Conditional*, not never, because labelling friction
is the adoption risk that sits directly on the calibration wedge. The trigger and
the reasoning are [#36](https://github.com/deepskandpal/LangChef/issues/36) —
and [#14](https://github.com/deepskandpal/LangChef/issues/14) may retire the
question entirely, since a team with an existing labelled dataset never labels
anything. If it is ever built: a local single file, no server.

**Connectors beyond DuckDB, Parquet and Postgres**, until somebody is actually
blocked on one. [#46](https://github.com/deepskandpal/LangChef/issues/46) is
tracked, not scheduled.

**Search and recommendation packs.** They are the expertise flagship and they
come after there is a business.

---

## How to change this file

Not by deciding it is fine in the moment. Open an issue with `type:decision`,
name the evidence that would close it, and record the call in
[`DECISIONS.md`](DECISIONS.md) with a date.

The failure mode this file exists to prevent is not one bad decision. It is
twelve reasonable ones, each defensible alone, that together turn a tool with a
sharp claim into another dashboard.

## Multi-class kappa

Deferred by [DECISIONS #12](DECISIONS.md). Cohen's kappa over an NxN confusion
matrix measures how much two *raters* agree beyond chance. LangChef compares one
judge against one set of human labels, and for a classification dataset the label
is a hard target with no second rater at all.

It becomes worth building the day two humans label the same set and disagree with
each other, which is a real problem and not one anything on the board has.

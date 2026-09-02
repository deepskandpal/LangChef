# Contributing

LangChef is Apache-2.0 and public from its first commit. The claim it makes —
that you can tell whether a change to your AI system made it better or worse —
is one you should be able to check in a clone in about a minute, before you
trust a word of it.

```sh
git clone https://github.com/deepskandpal/LangChef
cd LangChef
./scripts/verify.sh        # 10 steps, no API key, no network
```

If that is green, everything below is real on your machine too.

## Where the work is

All of it is in [issues](https://github.com/deepskandpal/LangChef/issues),
including what is already done — the closed issues are the build log, and they
say what was built and why.

| I want to | Query |
|---|---|
| start something small | [`good first issue`](https://github.com/deepskandpal/LangChef/labels/good%20first%20issue) |
| see what is next | [`priority:P0`](https://github.com/deepskandpal/LangChef/labels/priority%3AP0) |
| see the plan | [milestones](https://github.com/deepskandpal/LangChef/milestones) |
| slice it any other way | [the project board](https://github.com/users/deepskandpal/projects/5) |
| read the build log | [closed issues](https://github.com/deepskandpal/LangChef/issues?q=is%3Aissue+is%3Aclosed) |
| know what is undecided | [`type:decision`](https://github.com/deepskandpal/LangChef/labels/type%3Adecision) |

Every issue is written to be picked up cold, with the same sections every time:
**Description**, **Background**, **Dependencies**, **Acceptance criteria**,
**Implementation notes**, **Out of scope**, and a traceability line back to the
PRD requirement and the design document it came from.

Before proposing something new, check
[`NON-GOALS.md`](NON-GOALS.md). Several reasonable-sounding features are ruled
out on purpose, with the reasoning written down.

## The rules

[`AGENTS.md`](AGENTS.md) is the working agreement — the lifecycle, the area
boundaries, and the constraints that are not negotiable in a pull request. It is
written for agents, and it is the same agreement for people. Read it before your
first change.

[`DECISIONS.md`](DECISIONS.md) holds the calls that constrain the code, each
with its reasoning and its date. If a change of yours contradicts one, that is a
conversation on an issue first, and a new dated entry second.

**Everything goes through a pull request, reviewed by at least one maintainer.**
`main` takes no direct commits from anyone, the maintainer included. The failure
mode here is a number that looks right, and review is the only control that has
reliably caught one. *(DECISIONS #14)*

## The short version

- Branch, push, open a pull request. Nothing lands on `main` directly.
- `./scripts/verify.sh` passes before you open a pull request.
- A new statistic ships with a known-answer test against an independent
  implementation, or it does not ship.
- Generated files get regenerated, never hand-edited.
- No provider SDK is imported outside `src/langchef/judge/providers.py`.
- Nothing weakens an exit-code refusal to make a test pass.

## Reporting something wrong

A wrong number is worse than a crash here, because nothing complains. If a
figure looks wrong, that is the most valuable issue you can file — say what you
expected, what you got, and how to see it. The dogfood workspace reproduces
without an API key, which makes it the best place to demonstrate one.

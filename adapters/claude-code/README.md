# LangChef for Claude Code

The agent layer: a skill that carries the calibration playbook and two commands
that drive the CLI. Disposable by design — the CLI is the contract, and this
directory is packaging.

## Install

```sh
# From a checkout, for one project:
mkdir -p .claude/skills .claude/commands
ln -s "$(pwd)/adapters/claude-code/skills/langchef-eval" .claude/skills/langchef-eval
ln -s "$(pwd)/adapters/claude-code/commands/langchef-calibrate.md" .claude/commands/
ln -s "$(pwd)/adapters/claude-code/commands/langchef-experiment.md" .claude/commands/
```

Or install the whole directory as a plugin, which also carries `plugin.json`:

```sh
claude plugin install ./adapters/claude-code
```

Then, in the project you want evaluated:

```sh
langchef init
```

## What the agent may and may not do

The gates are in the CLI, not in the prompt, which is the point. The skill tells
the agent that exit 2 means stop; the CLI makes it true whether the agent reads
the skill or not. An agent cannot approve a rubric on a human's behalf, because
approving is a command a human runs, and running the eval without one exits 2.

Writes are limited to the eval workspace. Anything touching the application
under test goes through a pull request a person opens.

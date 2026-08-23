# Harness adapters

Deliberately thin and disposable: packaging only, no logic. Deleting an adapter
must lose packaging, not capability — verified by running the same cycle from a
shell script.

- `claude-code/` — skills plus a headless scheduled run. Arrives in M4.
- A second harness follows in M5 via the Agent Skills standard, chosen from
  which harness the first design partners actually run.

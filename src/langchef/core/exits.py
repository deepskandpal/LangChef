"""Exit codes — the gate mechanism.

The approval gates and the pre-registration rule cannot live in a prompt: a
model asked nicely not to read out early will, eventually, read out early. So
the refusals are exit codes. An agent cannot argue with a non-zero exit.
"""

from enum import IntEnum


class Exit(IntEnum):
    """Process exit codes. Stable public contract — never renumber."""

    OK = 0
    ERROR = 1
    REFUSED = 2
    ABSTAINED = 3
    BUDGET = 4
    PIN_MISMATCH = 5


REASON: dict[Exit, str] = {
    Exit.OK: "ok",
    Exit.ERROR: "unexpected error",
    Exit.REFUSED: "refused — an approval gate is unmet",
    Exit.ABSTAINED: "abstained — confidence below threshold",
    Exit.BUDGET: "budget exhausted; report of what was left undone written",
    Exit.PIN_MISMATCH: "pin mismatch — judge model, version or rubric hash moved",
}

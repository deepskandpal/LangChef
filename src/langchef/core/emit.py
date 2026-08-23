"""The stdout/stderr contract.

JSON to stdout, human text to stderr, no ``--format`` flag (DECISIONS.md #3).
The agent parses stdout; the person reads stderr; neither mode is an
afterthought bolted onto the other.
"""

import json
import sys
from typing import Any, NoReturn

from langchef.core.exits import REASON, Exit


def emit(payload: dict[str, Any]) -> None:
    """Write one JSON document to stdout. The only thing that ever goes there."""
    json.dump(payload, sys.stdout, indent=2, sort_keys=True, default=str, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def say(*lines: str) -> None:
    """Write human-readable narration to stderr."""
    for line in lines:
        print(line, file=sys.stderr)


def fail(code: Exit, message: str, **detail: Any) -> NoReturn:
    """Emit a machine-readable refusal and exit with the contract's code."""
    emit({"ok": False, "exit": int(code), "reason": REASON[code], "message": message, **detail})
    say(f"langchef: {REASON[code]} — {message}")
    raise SystemExit(int(code))

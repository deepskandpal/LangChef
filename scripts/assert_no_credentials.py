#!/usr/bin/env python3
"""Fail if any model-provider credential is visible.

CI runs this before the test suite. The suite must pass with no API key at all
— it exercises the deterministic core and replays recorded judge responses — so
a key in the job environment means a test could quietly start spending money.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchef.core.credentials import present  # noqa: E402


def main() -> int:
    found = present()
    if found:
        print(f"FAIL: provider credentials visible: {', '.join(found)}", file=sys.stderr)
        return 1
    print("ok: no provider credentials in this environment", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

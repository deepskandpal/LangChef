"""The generated contract document must match the code that generates it."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_contract_markdown_is_not_stale():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_contract.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_decisions_file_records_all_nine():
    text = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    for n in range(1, 10):
        assert f"## {n}." in text, f"decision {n} is missing from DECISIONS.md"

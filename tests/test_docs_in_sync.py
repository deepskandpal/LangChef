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


def test_ci_delegates_to_the_verify_script():
    """One list of checks, not two. CI must not carry its own copy."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "./scripts/verify.sh" in ci
    for duplicated in ("uv run pytest", "uv run ruff", "uv build"):
        assert duplicated not in ci, (
            f"ci.yml repeats {duplicated!r} — it can now drift from verify.sh"
        )


def test_verify_script_is_executable():
    script = ROOT / "scripts" / "verify.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111, "scripts/verify.sh is not executable"


def test_readme_tells_you_how_to_install_and_how_to_check():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "astral.sh/uv/install.sh" in readme, "README never says how to get uv"
    assert "./scripts/verify.sh" in readme, "README never says how to verify a build"
    assert "uv sync" in readme

"""CI must run with no API key present, and must say so out loud."""

import os
import subprocess
import sys
from pathlib import Path

from langchef.core.credentials import VARS, present

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "assert_no_credentials.py"


def test_present_reports_names_never_values():
    found = present({"OPENAI_API_KEY": "sk-secret", "UNRELATED": "x"})
    assert found == ["OPENAI_API_KEY"]


def test_present_ignores_empty_values():
    assert present({name: "" for name in VARS}) == []


def test_the_guard_fails_when_a_key_is_visible():
    env = {**os.environ, "OPENAI_API_KEY": "sk-whatever"}
    proc = subprocess.run(
        [sys.executable, str(GUARD)], capture_output=True, text=True, env=env, check=False
    )
    assert proc.returncode == 1
    assert "OPENAI_API_KEY" in proc.stderr


def test_the_guard_passes_in_a_clean_environment():
    env = {k: v for k, v in os.environ.items() if k not in VARS}
    proc = subprocess.run(
        [sys.executable, str(GUARD)], capture_output=True, text=True, env=env, check=False
    )
    assert proc.returncode == 0, proc.stderr


def test_this_environment_is_clean_when_running_in_ci():
    if os.environ.get("CI", "").lower() not in {"1", "true", "yes"}:
        return
    assert present() == [], "CI is holding a provider credential — the suite could spend money"

"""Shared helpers. The suite must pass with no API key and no network."""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Result:
    """One CLI invocation, with the two streams the contract keeps separate."""

    code: int
    payload: dict | None
    err: str
    out: str

    def __iter__(self):
        return iter((self.code, self.payload, self.err))


@pytest.fixture(scope="session")
def run_cli():
    """Invoke the CLI in a subprocess.

    ``payload`` is stdout parsed as JSON, or None when stdout is not JSON --
    which the contract permits for ``--help`` and nothing else.
    """

    def _run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> Result:
        proc = subprocess.run(
            [sys.executable, "-m", "langchef.cli.main", *args],
            capture_output=True,
            text=True,
            cwd=str(cwd or ROOT),
            env=env,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = None
        return Result(proc.returncode, payload, proc.stderr, proc.stdout)

    return _run

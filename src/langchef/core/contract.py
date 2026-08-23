"""The agent contract, as data.

``docs/AGENT-CONTRACT.md`` is the prose; this is the machine-readable copy the
agent reads via ``langchef contract``. ``tests/test_contract.py`` asserts the
two never drift apart, and that every command marked implemented really exists.
"""

from dataclasses import asdict, dataclass

DETERMINISM = ("deterministic", "seeded", "cached")


@dataclass(frozen=True)
class Command:
    """One entry in the contract's command table."""

    name: str
    summary: str
    determinism: str
    writes: str
    milestone: str
    implemented: bool


COMMANDS: tuple[Command, ...] = (
    Command("contract", "Emit this contract as JSON", "deterministic", "-", "M0", True),
    Command(
        "doctor", "Verify environment, credentials, pins, budget", "deterministic", "-", "M0", True
    ),
    Command("packs list", "List resolvable expertise packs", "deterministic", "-", "M0", True),
    Command(
        "init",
        "Scaffold the workspace",
        "deterministic",
        "workspace",
        "M3",
        True,
    ),
    Command(
        "approve rubric",
        "Record a human approval of the rubric as it stands. Gate one",
        "deterministic",
        "evals/config.toml",
        "M4",
        True,
    ),
    Command(
        "sample",
        "Pull and stratify production traces",
        "seeded",
        "runs/<id>/sample.parquet",
        "M5",
        False,
    ),
    Command(
        "label plan",
        "Choose the labelling subset that maximises information per label",
        "deterministic",
        "labels/<judge>.todo.jsonl",
        "M1",
        True,
    ),
    Command(
        "label import",
        "Ingest returned human labels",
        "deterministic",
        "labels/<judge>.jsonl",
        "M1",
        True,
    ),
    Command(
        "judge run",
        "Score examples against a pinned rubric",
        "cached",
        "runs/<id>/scores.parquet",
        "M2",
        True,
    ),
    Command(
        "calibrate report",
        "Agreement: TPR, TNR, confusion matrix, Cohen's kappa, disagreement taxonomy",
        "deterministic",
        "runs/<id>/calibration.json",
        "M1",
        True,
    ),
    Command(
        "calibrate diff",
        "Re-score a revised rubric against the same labels, report the delta",
        "deterministic",
        "runs/<id>/delta.json",
        "M6",
        False,
    ),
    Command("eval run", "Run a suite over goldens", "cached", "runs/<id>/", "M6", False),
    Command(
        "baseline set | show",
        "Pin a run as the reference",
        "deterministic",
        "baselines/",
        "M3",
        True,
    ),
    Command(
        "compare",
        "Paired deltas, confidence intervals, regression flags, minimum detectable effect",
        "deterministic",
        "runs/<id>/compare.json",
        "M3",
        True,
    ),
    Command(
        "triage",
        "Slice drill-down, deploy correlation, reproduction set",
        "deterministic",
        "findings/",
        "M6",
        False,
    ),
    Command(
        "power",
        "Minimum detectable effect, sample size, horizon",
        "deterministic",
        "-",
        "M7",
        False,
    ),
    Command(
        "experiment design | check | readout",
        "Pre-registration, integrity checks, gated readout",
        "deterministic",
        "experiments/",
        "M7",
        False,
    ),
    Command(
        "ledger append | query", "The persistent record", "deterministic", "ledger/", "M3", True
    ),
    Command(
        "memo render", "Decision memo from run artifacts", "deterministic", "memos/", "M3", True
    ),
)

RULES: tuple[str, ...] = (
    "JSON to stdout, human text to stderr. There is no --format flag.",
    "--help is the single exception to the stdout rule: it is written for people.",
    "The agent decides what to look at and what it means; the CLI produces every number.",
    "No number without a run artifact: any figure in a memo must trace to a file under runs/.",
    "Judge results are cached on input hash + rubric hash + model pin, "
    "so a rerun is free and reproducible.",
    "Writes are limited to the eval workspace and notification channels; "
    "anything further goes through a pull request.",
    "Approval gates are exit codes, not requests: exit 2 means stop and ask a "
    "person, never edit the approval yourself.",
    "A comparison across two different pins is two measurements; compare exits 5 "
    "rather than rendering one.",
    "An inconclusive comparison is a finding, and is reported with the minimum "
    "detectable effect rather than as an absence of regression.",
)


def as_dict() -> dict:
    """The whole contract, ready for ``emit``."""
    from langchef.core.exits import REASON, Exit

    return {
        "version": 1,
        "commands": [asdict(c) for c in COMMANDS],
        "exit_codes": {int(c): REASON[c] for c in Exit},
        "rules": list(RULES),
    }

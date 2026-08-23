"""Approval gates, as data.

The gates cannot live in a prompt. A model asked nicely not to read out an
experiment early will, eventually, read one out early — so a gate is a
comparison between what a person approved and what is about to be used, and an
unmet one is exit 2. An agent cannot argue with a non-zero exit.

Gate one, the only one M4 enforces: **the rubric a calibration uses must be the
rubric a person approved.** Editing a rubric changes its hash, which revokes the
approval, which stops the next run. That is the whole mechanism, and it is why
the rubric is a hashed file rather than a string in a config.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Gate:
    """One approval requirement and whether it is currently met."""

    name: str
    met: bool
    approved: str | None
    actual: str
    remedy: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "met": self.met,
            "approved": self.approved,
            "actual": self.actual,
            "remedy": self.remedy,
        }


def rubric_gate(approved: str | None, actual: str, name: str = "rubric") -> Gate:
    """Gate one: the rubric in use must be the one that was signed off.

    ``approved`` is the ``name@digest`` a person recorded in ``config.toml``.
    ``actual`` is what is on disk right now. A missing approval is not treated
    as permission — an unapproved rubric and an edited one both stop the run.
    """
    if approved is None:
        remedy = f"no rubric approved yet — review it, then run: langchef approve rubric {name}"
    elif approved != actual:
        remedy = (
            f"{name} changed since it was approved ({approved} -> {actual}). "
            f"Review the diff, then run: langchef approve rubric {name}"
        )
    else:
        remedy = ""
    return Gate(
        name="rubric-approved",
        met=approved is not None and approved == actual,
        approved=approved,
        actual=actual,
        remedy=remedy,
    )


def unmet(gates: list[Gate]) -> list[Gate]:
    return [gate for gate in gates if not gate.met]

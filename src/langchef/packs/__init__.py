"""Expertise pack loading — the commercial boundary.

Packs are versioned playbooks per application class: what to measure, golden-set
methodology, judge rubric libraries with calibration procedures, drift methods,
experiment design discipline, triage runbooks. They load from a directory
through a manifest, and they have done so since the first commit (DECISIONS.md
#5). If pack logic leaks into the core, the core can never be open-sourced and
the moat can never be sold separately.

A pack also declares the **task classes** it serves — the shape of an example,
its outcome, its metric set, and whether it needs a judge at all (DECISIONS.md
#12). ``core/`` never learns those names: it computes over outcomes, and a fifth
task class is a directory on the search path rather than a patch to the
statistics engine.
"""

from langchef.packs.loader import (
    discover,
    entry_point,
    load,
    load_class,
    reporting,
    search_path,
    task_classes,
)
from langchef.packs.manifest import Manifest, ManifestError, TaskClass

__all__ = [
    "Manifest",
    "ManifestError",
    "TaskClass",
    "discover",
    "entry_point",
    "load",
    "load_class",
    "reporting",
    "search_path",
    "task_classes",
]

"""Expertise pack loading — the commercial boundary.

Packs are versioned playbooks per application class: what to measure, golden-set
methodology, judge rubric libraries with calibration procedures, drift methods,
experiment design discipline, triage runbooks. They load from a directory
through a manifest, and they have done so since the first commit even though
there is exactly one pack (DECISIONS.md #5). If pack logic leaks into the core,
the core can never be open-sourced and the moat can never be sold separately.
"""

from langchef.packs.loader import discover, load, search_path
from langchef.packs.manifest import Manifest, ManifestError

__all__ = ["Manifest", "ManifestError", "discover", "load", "search_path"]

"""Finding packs on disk.

Resolution order, first match wins: ``$LANGCHEF_PACK_PATH`` entries, then the
workspace's own ``evals/packs``, then the checkout's ``packs/`` directory.
"""

import os
from pathlib import Path

from langchef.packs.manifest import Manifest, ManifestError, parse

ENV_VAR = "LANGCHEF_PACK_PATH"


def _checkout_packs() -> Path | None:
    """The ``packs/`` directory of a source checkout, if we are running from one."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "packs").is_dir():
            return parent / "packs"
    return None


def search_path() -> list[Path]:
    """Directories searched for packs, in resolution order, deduplicated."""
    candidates: list[Path] = []
    env = os.environ.get(ENV_VAR, "")
    candidates += [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    candidates.append(Path.cwd() / "evals" / "packs")
    checkout = _checkout_packs()
    if checkout is not None:
        candidates.append(checkout)

    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            ordered.append(resolved)
    return ordered


def discover() -> list[Manifest]:
    """Every valid pack on the search path. Malformed packs are skipped, not fatal."""
    found: dict[str, Manifest] = {}
    for root in search_path():
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name in found:
                continue
            try:
                found[child.name] = parse(child)
            except ManifestError:
                continue
    return list(found.values())


def load(name: str) -> Manifest:
    """Resolve one pack by name, or raise."""
    for manifest in discover():
        if manifest.name == name:
            return manifest
    roots = ", ".join(str(p) for p in search_path())
    raise ManifestError(f"pack {name!r} not found on the search path: {roots}")

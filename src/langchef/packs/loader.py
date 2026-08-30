"""Finding packs on disk, and the task classes they declare.

Resolution order, first match wins: ``$LANGCHEF_PACK_PATH`` entries, then the
workspace's own ``evals/packs``, then the checkout's ``packs/`` directory. A task
class resolves the same way, through the pack that declares it, so a second pack
adding a class is a directory on the search path and nothing else.

A pack may also ship the code for its own reporting. ``entry_point`` imports it
from the pack directory by the path the manifest names, and ``reporting`` is that
resolution for one task class — the loader is the only thing anywhere that
executes pack code, which is what keeps ``core/`` free of it.
"""

import importlib.util
import os
import sys
from collections.abc import Callable
from pathlib import Path

from langchef.packs.manifest import Manifest, ManifestError, TaskClass, parse

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


def task_classes() -> list[tuple[Manifest, TaskClass]]:
    """Every task class on the search path, with the pack that declares it.

    Ordered by pack resolution, then by class name. Where two packs declare the
    same class the earlier pack on the search path wins, exactly as it does for
    the packs themselves, so a local pack can shadow a shipped one.
    """
    resolved: list[tuple[Manifest, TaskClass]] = []
    claimed: set[str] = set()
    for manifest in discover():
        for name in sorted(manifest.task_classes):
            if name in claimed:
                continue
            claimed.add(name)
            resolved.append((manifest, manifest.task_classes[name]))
    return resolved


def load_class(name: str) -> tuple[Manifest, TaskClass]:
    """Resolve one task class by name to the pack that serves it, or raise."""
    for manifest, task_class in task_classes():
        if task_class.name == name:
            return manifest, task_class
    known = ", ".join(sorted(tc.name for _, tc in task_classes())) or "none"
    raise ManifestError(
        f"no pack on the search path serves task class {name!r} (available: {known})"
    )


def entry_point(manifest: Manifest, target: str) -> Callable[..., object]:
    """Import ``"<file>.py:<callable>"`` from inside a pack directory.

    This is the one place that executes code shipped in a pack. It is here
    rather than anywhere else for the same reason the manifest holds the task
    classes: what a pack knows how to measure is the pack's business, and the
    moment ``core/`` imports it the open-core split stops being possible.
    """
    filename, _, attribute = target.partition(":")
    module_path = manifest.path / filename
    module_name = f"langchef_pack.{manifest.name}.{Path(filename).stem}".replace("-", "_")

    module = sys.modules.get(module_name)
    if module is None or getattr(module, "__file__", None) != str(module_path):
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ManifestError(f"pack {manifest.name!r}: cannot import {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # a broken pack must not look like a broken core
            del sys.modules[module_name]
            raise ManifestError(
                f"pack {manifest.name!r}: {module_path} failed to import: {exc}"
            ) from exc

    function = getattr(module, attribute, None)
    if not callable(function):
        raise ManifestError(f"pack {manifest.name!r}: {module_path} has no callable {attribute!r}")
    return function


def reporting(manifest: Manifest, task_class: TaskClass) -> Callable[..., dict]:
    """The pack's own reporting for one task class, imported from the pack.

    Absent for a class the deterministic core already covers, which is why this
    refuses rather than returning a default: a class with no reporting and a
    class whose reporting failed to load must not look the same.
    """
    if not task_class.reporting:
        raise ManifestError(
            f"task class {task_class.name!r} in pack {manifest.name!r} declares no reporting "
            "entry point"
        )
    return entry_point(manifest, task_class.reporting)

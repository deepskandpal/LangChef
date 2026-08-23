"""The pack manifest schema."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ManifestError(ValueError):
    """A pack.toml is missing, malformed, or inconsistent with its directory."""


@dataclass(frozen=True)
class Manifest:
    """A parsed and validated ``pack.toml``."""

    name: str
    version: str
    application_class: str
    description: str
    requires_langchef: str
    path: Path
    judges: list[str] = field(default_factory=list)
    playbooks: list[str] = field(default_factory=list)

    @property
    def ref(self) -> str:
        """The form written into ``pack.lock``."""
        return f"{self.name}@{self.version}"


REQUIRED = ("name", "version", "application_class", "description")


def parse(path: Path) -> Manifest:
    """Read and validate ``<path>/pack.toml``."""
    toml_path = path / "pack.toml"
    if not toml_path.is_file():
        raise ManifestError(f"no pack.toml in {path}")

    try:
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{toml_path}: {exc}") from exc

    pack = raw.get("pack")
    if not isinstance(pack, dict):
        raise ManifestError(f"{toml_path}: missing [pack] table")

    missing = [key for key in REQUIRED if not pack.get(key)]
    if missing:
        raise ManifestError(f"{toml_path}: [pack] missing {', '.join(missing)}")

    if pack["name"] != path.name:
        raise ManifestError(f"{toml_path}: pack name {pack['name']!r} != directory {path.name!r}")

    contents = raw.get("contents") or {}
    return Manifest(
        name=pack["name"],
        version=str(pack["version"]),
        application_class=pack["application_class"],
        description=pack["description"],
        requires_langchef=str(pack.get("requires_langchef", ">=0.1.0")),
        path=path,
        judges=list(contents.get("judges") or []),
        playbooks=list(contents.get("playbooks") or []),
    )

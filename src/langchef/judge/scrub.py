"""Removing credentials from a recorded session before it becomes a public file.

A cassette recorded against a real model is a transcript of an authenticated
HTTP exchange. It goes into a public repository. The failure this module exists
to prevent is a key committed in a test fixture, which is unrecoverable in the
sense that mattered: the moment it is pushed it is public, and rotating it is
the only remedy.

The design rule is **deny by default**. Headers are dropped unless named as
safe, rather than dropped when they look dangerous, because the header a
provider adds next year is not on anyone's blocklist today.

``audit`` is the second half and the one that actually protects the repository.
Scrubbing is a transformation and can be wrong; the audit is a check on the
finished bytes, it knows the live credential values, and the recorder refuses to
write anything it flags. A scrubber alone would let a key ride out inside a
field nobody thought about.
"""

import re
from typing import Any

#: Response headers worth keeping. Everything else is dropped, including the
#: ones that are merely uninteresting, because an allowlist that has to be
#: correct about what is dangerous is the wrong shape for this problem.
SAFE_HEADERS: frozenset[str] = frozenset(
    {
        "content-type",
        "content-length",
        "x-request-id",
        "openai-processing-ms",
        "openai-version",
    }
)

#: What a redacted value is replaced with. Recognisable on sight in a diff.
REDACTED = "<redacted>"

#: Shapes that are credentials regardless of the field they arrive in. These are
#: prefixes real providers use, matched against any string in the payload.
KEY_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}"),
    re.compile(r"\borg-[A-Za-z0-9]{12,}\b"),
)


def headers(raw: dict[str, str]) -> dict[str, str]:
    """Keep the named headers, drop everything else. Case-insensitive."""
    return {k: v for k, v in sorted(raw.items()) if k.lower() in SAFE_HEADERS}


def text(value: str) -> str:
    """Redact anything credential-shaped inside a string."""
    for shape in KEY_SHAPES:
        value = shape.sub(REDACTED, value)
    return value


def payload(value: Any) -> Any:
    """Walk a decoded JSON body and redact credential shapes wherever they sit."""
    if isinstance(value, str):
        return text(value)
    if isinstance(value, dict):
        return {k: payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [payload(v) for v in value]
    return value


def audit(blob: str, secrets: list[str]) -> list[str]:
    """What is still wrong with these bytes. Empty means safe to write.

    ``secrets`` are the live credential values from the recording environment.
    They are checked by exact substring because that is the only test that
    cannot be fooled by a key shaped unlike any pattern above. This function is
    the reason the recorder can be trusted; the scrubber is only the reason it
    usually has nothing to report.
    """
    problems = []
    for secret in secrets:
        if secret and secret in blob:
            problems.append("a live credential value appears in the recording")
            break
    for shape in KEY_SHAPES:
        found = shape.search(blob)
        if found and found.group(0) != REDACTED:
            problems.append(f"a credential-shaped string survived scrubbing: {shape.pattern}")
    return problems

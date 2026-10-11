"""Refuse any name that could leave its directory or break on Windows (R65, TF7).

One job: the single validator every slug, id and slot key passes before it becomes part of a
path. It refuses `..`, an absolute path, either separator, a drive letter, a reserved Windows
device name (`CON`, `NUL`, ...), a trailing dot or space, control characters and a name longer
than `MAX_NAME_LEN`, with the same answer on Windows and Ubuntu. Callers get an `UnsafeName`
before any file is touched. Pure string logic: no filesystem access, nothing POSIX-only.
"""

from __future__ import annotations

import re
from urllib.parse import quote

SLUG_PATTERN = r"^[a-z][a-z0-9-]*$"
"""The project slug shape (the one `schema.project.Project.slug` and `ui.helpers` share)."""
MAX_NAME_LEN = 120
_DEVICES = frozenset({"con", "prn", "aux", "nul",
                      *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))})
_SLUG = re.compile(SLUG_PATTERN)
_DRIVE = re.compile(r"^[A-Za-z]:")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class UnsafeName(ValueError):
    """The name is not safe to use as one path segment; `str(exc)` says which rule it broke."""


def _refuse_structure(name: str) -> str:
    """Rules that hold for a raw name whatever the encoding: shape, separators, `..`."""
    if not name or name in {".", ".."}:
        raise UnsafeName(f"unsafe name {name!r}: empty or a dot segment")
    if "/" in name or "\\" in name:
        raise UnsafeName(f"unsafe name {name!r}: contains a path separator")
    if _CONTROL.search(name):
        raise UnsafeName(f"unsafe name {name!r}: contains a control character")
    return name


def safe_name(name: str) -> str:
    """`name` unchanged when it is a safe single path segment, else `UnsafeName`."""
    _refuse_structure(name)
    if _DRIVE.match(name):
        raise UnsafeName(f"unsafe name {name!r}: starts with a drive letter")
    if name.endswith((".", " ")):
        raise UnsafeName(f"unsafe name {name!r}: ends with a dot or a space")
    if name.split(".", 1)[0].lower() in _DEVICES:
        raise UnsafeName(f"unsafe name {name!r}: a reserved Windows device name")
    if len(name) > MAX_NAME_LEN:
        raise UnsafeName(f"unsafe name {name[:20]!r}...: longer than {MAX_NAME_LEN} characters")
    return name


def safe_slug(slug: str) -> str:
    """A project slug: the slug pattern, and a safe path segment."""
    if not _SLUG.fullmatch(slug):
        raise UnsafeName(f"unsafe slug {slug!r}: must match {SLUG_PATTERN}")
    return safe_name(slug)


def encode_slot_key(key: str) -> str:
    """A slot key (`<project>:<mode>:<instant>`) as a reversible, path-safe file name.

    Percent-encodes every character outside `[A-Za-z0-9_.-]` (so the `:` of a time can never
    read as a Windows drive letter), the same encoding `stages/schedule_store.py` uses."""
    return safe_name(quote(_refuse_structure(key), safe=""))

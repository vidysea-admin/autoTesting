"""Refuse any name that could leave its directory or break on Windows (R65, TF7).

One job: the single validator every slug, id and slot key passes before it becomes part of a
path. It refuses `..`, an absolute path, either separator, any `:` (drive letter, `nul:`, an NTFS
alternate data stream `ab:stream`), any of `< > " | ? *`, a reserved Windows device name
(`CON`, `NUL`, `COM1`, `CONIN$`, ... with or without an extension), a trailing dot or space,
control characters and a name longer than `MAX_NAME_LEN`, with the same answer on Windows and
Ubuntu. Callers get an `UnsafeName` before any file is touched. Pure string logic: no
filesystem access, nothing POSIX-only. `safe_key` is the same promise for a whole
relative POSIX state key (`projects/p/x.json`), the address every state backend uses.
"""

from __future__ import annotations

import re
from urllib.parse import quote

SLUG_PATTERN = r"^[a-z][a-z0-9-]*$"
"""The project slug shape (the one `schema.project.Project.slug` and `ui.helpers` share)."""
MAX_NAME_LEN = 120
_DIGITS = (*"0123456789", "¹", "²", "³")  # Windows reserves COM0 and COM¹ (as COM1) too
_DEVICES = frozenset({"con", "prn", "aux", "nul", "conin$", "conout$", "clock$",
                      *(f"com{n}" for n in _DIGITS), *(f"lpt{n}" for n in _DIGITS)})
_SLUG = re.compile(SLUG_PATTERN)
_DRIVE = re.compile(r"^[A-Za-z]:")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_FORBIDDEN = re.compile(r'[<>:"|?*]')
_SHORT = re.compile(r"[^.~]{1,6}~[0-9]{1,6}(\.[^.]{0,3})?")  # NTFS 8.3 alias: PROFIL~1, WORK~2.TXT


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
    if _FORBIDDEN.search(name):
        raise UnsafeName(f"unsafe name {name!r}: contains one of : < > \" | ? *")
    if name.endswith((".", " ")):
        raise UnsafeName(f"unsafe name {name!r}: ends with a dot or a space")
    if name.split(".", 1)[0].rstrip(" ").lower() in _DEVICES:
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


def _device(name: str) -> bool:
    return name.split(".", 1)[0].rstrip(" ").lower() in _DEVICES


def _bad_segment(segment: str, *, partial: bool) -> bool:
    """A dot or empty segment always; a trailing dot/space or device name only once it is whole
    (`p/CON` as a prefix may be the start of `p/CONFIG.json`)."""
    if segment in {"", ".", ".."}:
        return True
    return not partial and (segment.endswith((".", " ")) or _device(segment)
                            or bool(_SHORT.fullmatch(segment)))


def safe_key(key: str, *, prefix: bool = False) -> str:
    """A state-store key: a relative POSIX path inside the data root, else `UnsafeName` (M17).

    Refused before any I/O, with the same answer on Windows and Linux: a backslash, a control
    character (NUL), any of `: < > " | ? *` (drive letter, `nul:`, a stream), a leading `/`, a `.`,
    `..` or empty segment, and a whole segment that ends in a dot or space, is a reserved
    device name (`CON`, `nul.txt`, `COM1`) or is an NTFS 8.3 short name (`PROFIL~1`, M55).
    A `prefix` may be empty or end in `/`, and its last segment may be unfinished; a key may not
    be empty."""
    body = key[:-1] if prefix and key.endswith("/") else key
    segments = body.split("/") if body else []
    open_end = prefix and not key.endswith("/")
    last = len(segments) - 1
    if ("\\" in key or _CONTROL.search(key) or _FORBIDDEN.search(key)
            or (not body and not prefix)
            or any(_bad_segment(seg, partial=open_end and i == last)
                   for i, seg in enumerate(segments))):
        raise UnsafeName(f"unsafe state key {key!r}: not a relative path inside the data root")
    return key

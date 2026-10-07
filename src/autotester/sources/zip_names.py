"""Zip member-name vetting that behaves identically under Windows and Ubuntu path rules.

Contract: team-intake.md TI1 (R39, R65). A name is judged as a plain string: BOTH `/` and `\\`
are separators on every host, so it never consults `os.sep` or a `pathlib` flavour, and the
same hostile zip gets the same refusal on the dev host and on the server. The returned reason
is the human-readable cause the report shows; `None` means the name is safe to LIST. Nothing
here decides where bytes go: a destination is built from a generated name and then checked
with `ensure_inside` (TI4).
"""

from __future__ import annotations

import re
import stat
import unicodedata
import zipfile
from pathlib import Path

_DRIVE = re.compile(r"^[A-Za-z]:")
_RESERVED = frozenset({"CON", "PRN", "AUX", "NUL",
                       *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))})
_BIDI = frozenset("؜‎‏‪‫‬‭‮⁦⁧⁨⁩")
NESTED_SUFFIXES = frozenset({".zip", ".7z", ".rar", ".tar", ".gz", ".tgz"})
ARCHIVE_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"7z\xbc\xaf\x27\x1c", b"Rar!\x1a\x07",
                      b"\x1f\x8b")
_SPECIAL = ((stat.S_ISLNK, "symlink"), (stat.S_ISCHR, "device"), (stat.S_ISBLK, "device"),
            (stat.S_ISFIFO, "fifo"), (stat.S_ISSOCK, "socket"))


class UnsafePath(ValueError):
    """A destination that does not resolve inside the directory it must stay in."""


def _has_control(name: str) -> bool:
    return any(unicodedata.category(c) == "Cc" or c in _BIDI for c in name)


def vet_member_name(raw: str) -> str | None:
    """Why a member name is hostile, or `None` when it is safe. Pass `ZipInfo.orig_filename`:
    `ZipInfo.filename` is already cut at a NUL and has `os.sep` rewritten on Windows."""
    if _has_control(raw):
        return "control character in name"
    unified = raw.replace("\\", "/")
    if unified.startswith("//"):
        return "UNC path"
    if unified.startswith("/"):
        return "absolute path"
    if _DRIVE.match(unified):
        return "drive letter"
    parts = [p for p in unified.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return "path traversal (..)"
    if any(":" in p for p in parts):
        return "alternate data stream (:)"
    for part in parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if stem in _RESERVED:
            return "reserved device name"
    return None


def special_mode_kind(info: zipfile.ZipInfo) -> str | None:
    """`symlink` / `device` / `fifo` / `socket` when the entry's Unix mode says so (zip has no
    hardlink entry; a hardlink is carried as a regular entry and refused by the name rules)."""
    mode = info.external_attr >> 16
    return next((label for check, label in _SPECIAL if check(mode)), None)


def is_nested_archive_name(name: str) -> bool:
    return Path(name.replace("\\", "/")).suffix.lower() in NESTED_SUFFIXES


def looks_like_archive(head: bytes) -> bool:
    return head.startswith(ARCHIVE_SIGNATURES)


def ensure_inside(path: Path, root: Path) -> Path:
    """`path` resolved, only if it lies inside `root` resolved. A string prefix test would
    accept `staging-evil` for `staging`; `Path.is_relative_to` on resolved paths does not."""
    resolved, base = path.resolve(), root.resolve()
    if resolved != base and not resolved.is_relative_to(base):
        raise UnsafePath("destination escapes its directory")
    return resolved


def display_name(raw: str, limit: int = 200) -> str:
    """The member name as it may be shown or stored: control and bidi characters escaped, so a
    hostile name cannot spoof the report or the page."""
    shown = "".join(f"\\u{ord(c):04x}" if (unicodedata.category(c) == "Cc" or c in _BIDI) else c
                    for c in raw)
    return shown if len(shown) <= limit else shown[:limit] + "..."

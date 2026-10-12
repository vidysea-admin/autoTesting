"""Parse a pasted Google Drive link (or a bare id) into a `DriveRef`: only an id survives.

Contract: team-intake.md TI7 (the file, `open?id=`, `uc?id=`, folder and bare-id forms; every
other shape is refused) and hosting.md HO32 (https, host EXACTLY `drive.google.com` or
`docs.google.com`). The URL is never fetched: the id is handed to the `gws` adapter, so a
redirect cannot be steered from a pasted link. Refusal messages never echo the pasted text (a
link can carry a token).
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from autotester.schema.intake import DriveRef

DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{6,128}")
"""The Drive id character set: the ONE definition (`drive_verify` imports it)."""
DRIVE_HOSTS = frozenset({"drive.google.com", "docs.google.com"})
_FILE = re.compile(r"^/(?:file/(?:u/\d+/)?d)/([^/]+)(?:/.*)?$")
_FOLDER = re.compile(r"^/(?:drive/(?:u/\d+/)?)?folders/([^/]+)/?$")
_FORBIDDEN = re.compile(r"[\\\s\x00-\x1f\x7f]|[^\x00-\x7f]")


class DriveLinkError(ValueError):
    """A pasted value that is not a usable Drive link. The message never echoes the value."""


def _id_or_refuse(candidate: str | None) -> str:
    if not candidate or not DRIVE_ID.fullmatch(candidate):
        raise DriveLinkError("that link has no valid Google Drive id "
                             "(letters, digits, - and _ only)")
    return candidate


def _from_path(parts) -> DriveRef:
    path = parts.path
    if match := _FILE.match(path):
        return DriveRef(id=_id_or_refuse(match.group(1)), kind="file")
    if match := _FOLDER.match(path):
        return DriveRef(id=_id_or_refuse(match.group(1)), kind="folder")
    if path in ("/open", "/uc"):
        ids = parse_qs(parts.query).get("id", [])
        if len(ids) != 1:
            raise DriveLinkError("that link needs exactly one id= value")
        return DriveRef(id=_id_or_refuse(ids[0]))
    raise DriveLinkError("that is not a Google Drive file or folder link")


def parse_drive_link(text: str) -> DriveRef:
    """`DriveRef` for a Drive file/folder link or a bare id; `DriveLinkError` for anything else."""
    value = (text or "").strip()
    if "://" not in value:
        if "/" in value or "." in value or ":" in value:
            raise DriveLinkError("paste a Google Drive link (https://drive.google.com/...) "
                                 "or a bare Drive id")
        return DriveRef(id=_id_or_refuse(value))
    if _FORBIDDEN.search(value):
        raise DriveLinkError("that link contains characters a Drive link never has")
    try:
        parts = urlsplit(value)
        port, host = parts.port, (parts.hostname or "").lower()
    except ValueError:
        raise DriveLinkError("that is not a valid link") from None
    if parts.scheme != "https":
        raise DriveLinkError("only https Google Drive links are accepted")
    if parts.username is not None or parts.password is not None or port not in (None, 443):
        raise DriveLinkError("only plain https://drive.google.com links are accepted")
    if host not in DRIVE_HOSTS:
        raise DriveLinkError("only links on drive.google.com or docs.google.com are accepted")
    return _from_path(parts)

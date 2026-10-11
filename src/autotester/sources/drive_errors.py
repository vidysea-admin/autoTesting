"""The ways a Drive fetch fails, each with its own fixed, human message (TI8, HO33).

Contract: team-intake.md TI8. Not authenticated, permission denied, not found, quota exceeded and
network error are five different messages that say what to do next. The message is chosen from
a table by KIND; the text `gws` printed (which can hold a token, a signed URL or a file name) is
read here to pick the kind and is then dropped, so nothing it said can reach a log, a page, the
audit file or a source row.
"""

from __future__ import annotations

import json
from enum import StrEnum


class DriveFailure(StrEnum):
    NOT_AUTHENTICATED = "not_authenticated"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK_ERROR = "network_error"
    GWS_MISSING = "gws_missing"


MESSAGES: dict[DriveFailure, str] = {
    DriveFailure.NOT_AUTHENTICATED: (
        "The server is not signed in to Google. An administrator must run `gws auth login` "
        "on the server, then paste the link again."),
    DriveFailure.PERMISSION_DENIED: (
        "Google Drive refused access to that file. Make it viewable by anyone with the link, "
        "or share it with the server's Google account, then paste the link again."),
    DriveFailure.NOT_FOUND: (
        "Google Drive has no file with that id. Check the link, and that the file was not "
        "deleted or moved to a drive the server's Google account cannot see."),
    DriveFailure.QUOTA_EXCEEDED: (
        "Google Drive is rate-limiting or has used up its download quota for that file. "
        "Wait a while and try again, or upload the file directly."),
    DriveFailure.NETWORK_ERROR: (
        "The server could not reach Google Drive, or Drive's answer could not be read. "
        "Try again in a few minutes; if it keeps failing, upload the file directly."),
    DriveFailure.GWS_MISSING: (
        "The Google command-line tool (`gws`) is not installed on the server, so Drive links "
        "cannot be fetched. An administrator must install it, or you can upload the file."),
}


class DriveError(Exception):
    """A Drive failure of a known kind. `str(exc)` is the fixed message and nothing else."""

    def __init__(self, kind: DriveFailure) -> None:
        super().__init__(MESSAGES[kind])
        self.kind = kind


_AUTH = ("autherror", "unauthenticated", "invalid_grant", "invalid credentials", "no credentials",
         "gws auth login", "not logged in", "token has been expired", "token expired")
_QUOTA = ("ratelimit", "rate limit", "quota", "dailylimit", "too many requests",
          "toomanyrequests")
_NOT_FOUND = ("notfound", "not found", "file does not exist")
_DENIED = ("forbidden", "permission", "insufficient", "accessdenied", "access denied",
           "cannot download", "cannot be downloaded", "abuse")


def _error_fields(text: str) -> tuple[int | None, str]:
    """`(http code, lower-cased reason + message)` read from a JSON error body if there is one."""
    try:
        body = json.loads(text)
    except ValueError:
        return None, text.lower()
    err = body.get("error") if isinstance(body, dict) else None
    if not isinstance(err, dict):
        return None, text.lower()
    code = err.get("code") if isinstance(err.get("code"), int) else None
    reasons = " ".join(str(e.get("reason", "")) for e in err.get("errors", [])
                       if isinstance(e, dict))
    return code, f"{reasons} {err.get('status', '')} {err.get('message', '')}".lower()


def classify_gws_failure(stdout: str, stderr: str) -> DriveFailure:
    """Pick the failure kind from what `gws` printed. The text itself is never kept."""
    code, text = _error_fields(stderr.strip() or stdout.strip())
    if code == 401 or any(w in text for w in _AUTH):
        return DriveFailure.NOT_AUTHENTICATED
    if code == 429 or any(w in text for w in _QUOTA):
        return DriveFailure.QUOTA_EXCEEDED
    if code == 404 or any(w in text for w in _NOT_FOUND):
        return DriveFailure.NOT_FOUND
    if code == 403 or any(w in text for w in _DENIED):
        return DriveFailure.PERMISSION_DENIED
    return DriveFailure.NETWORK_ERROR

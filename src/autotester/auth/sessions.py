"""Server-side sessions (AU3): a 256-bit random id in the cookie, only its SHA-256 in the
store, looked up on every request, so a disable, delete, group change or reset takes
effect on the next request. Absolute lifetime, 12 h by default, never unlimited.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

from autotester.auth import db
from autotester.schema.auth import Principal

SESSION_HOURS_ENV = "AUTOTESTER_SESSION_HOURS"
DEFAULT_SESSION_HOURS = 12
MAX_SESSION_HOURS = 24 * 7
MAX_TOKEN_LENGTH = 128


def session_hours() -> int:
    """Configured lifetime in hours, clamped to 1..MAX_SESSION_HOURS (never unlimited)."""
    try:
        hours = int(os.environ.get(SESSION_HOURS_ENV, DEFAULT_SESSION_HOURS))
    except ValueError:
        hours = DEFAULT_SESSION_HOURS
    return min(max(hours, 1), MAX_SESSION_HOURS)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """A fresh id at every login (no fixation). Returns the cookie value."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    with db.transaction() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_digest(token), user_id, now.isoformat(),
             (now + timedelta(hours=session_hours())).isoformat()),
        )
    return token


def resolve_session(token: str | None) -> Principal | None:
    """The live principal for a cookie value, or None: unknown, expired, truncated,
    tampered, or the account is disabled. Never creates the store."""
    if not token or len(token) > MAX_TOKEN_LENGTH or not db.store_exists():
        return None
    now = datetime.now(UTC).isoformat()
    with db.reading() as conn:
        row = conn.execute(
            "SELECT u.id, u.email, u.display_name FROM sessions s JOIN users u "
            "ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ? "
            "AND u.disabled = 0", (_digest(token), now),
        ).fetchone()
        if row is None:
            return None
        perms = frozenset(r["permission"] for r in conn.execute(
            "SELECT DISTINCT p.permission FROM memberships m JOIN group_permissions p "
            "ON p.group_id = m.group_id WHERE m.user_id = ?", (row["id"],)))
    return Principal(user_id=row["id"], email=row["email"],
                     display_name=row["display_name"], permissions=perms)


def end_session(token: str | None) -> None:
    if token and len(token) <= MAX_TOKEN_LENGTH and db.store_exists():
        with db.transaction() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_digest(token),))

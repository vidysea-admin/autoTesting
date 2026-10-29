"""Server-side sessions (AU3): a 256-bit random id in the cookie, only its SHA-256 in the
store, looked up on every request, so a disable, delete, group change or reset takes
effect on the next request. Absolute lifetime, 12 h by default, never unlimited.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

from autotester.auth.store import auth_store
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
    with auth_store().transaction() as tx:
        tx.purge_sessions_before(now.isoformat())
        tx.insert_session(_digest(token), user_id, now.isoformat(),
                          (now + timedelta(hours=session_hours())).isoformat())
    return token


def _drop_expired(digest: str, now: str) -> None:
    with auth_store().transaction() as tx:
        tx.delete_session_if_expired(digest, now)


def resolve_session(token: str | None) -> Principal | None:
    """The live principal for a cookie value, or None: unknown, expired, truncated,
    tampered, or the account is disabled. Never creates the store."""
    store = auth_store()
    if not token or len(token) > MAX_TOKEN_LENGTH or not store.exists():
        return None
    now = datetime.now(UTC).isoformat()
    digest = _digest(token)
    with store.reading() as tx:
        principal = tx.live_principal(digest, now)
        if principal is None and tx.has_session(digest):
            _drop_expired(digest, now)  # a refused expired id: drop it (unknown ids cause no write)
    return principal


def end_session(token: str | None) -> None:
    store = auth_store()
    if token and len(token) <= MAX_TOKEN_LENGTH and store.exists():
        with store.transaction() as tx:
            tx.delete_session(_digest(token))

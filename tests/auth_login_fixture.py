"""The test suite's signed-in admin (T-204): one known session in whatever scratch
`AUTOTESTER_ROOT` the current test uses, so every existing UI test keeps reaching its
routes through the login gate (auth.md AU25) without weakening any assertion.

Never touches the real repository's store: a test with no scratch `AUTOTESTER_ROOT`
gets `AUTOTESTER_AUTH_DIR` pointed at a suite-wide temp directory for that request
(tests/conftest.py). `AUTOTESTER_TEST_NO_AUTO_LOGIN=1` turns it off, for the auth
tests that drive login themselves.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

from autotester.auth import db
from autotester.auth.passwords import hash_password

TEST_ADMIN_EMAIL = "suite-admin@autotester.test"
TOKEN = secrets.token_urlsafe(32)
_HASH = hash_password(secrets.token_urlsafe(24))  # nobody can sign in with it


def enabled() -> bool:
    return os.environ.get("AUTOTESTER_TEST_NO_AUTO_LOGIN") != "1"


def ensure_session() -> str:
    """Create (idempotently) the admin account and its session in the current store."""
    now = datetime.now(UTC)
    digest = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()
    with db.transaction() as conn:
        conn.execute("INSERT OR IGNORE INTO users (email, password_hash, created_at, generation) "
                     "VALUES (?, ?, ?, ?)",
                     (TEST_ADMIN_EMAIL, _HASH, now.isoformat(), db.new_account_generation()))
        user_id = conn.execute("SELECT id FROM users WHERE email = ?",
                               (TEST_ADMIN_EMAIL,)).fetchone()[0]
        admin = db.admin_group_id(conn)
        if admin is not None:
            conn.execute("INSERT OR IGNORE INTO memberships (user_id, group_id) VALUES (?, ?)",
                         (user_id, admin))
        conn.execute("INSERT OR REPLACE INTO sessions (token_hash, user_id, created_at, "
                     "expires_at) VALUES (?, ?, ?, ?)",
                     (digest, user_id, now.isoformat(), (now + timedelta(hours=1)).isoformat()))
    return TOKEN

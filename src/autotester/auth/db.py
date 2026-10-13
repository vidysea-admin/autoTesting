"""The auth store's SQLite file: connection, tables, one-time seeding, last-admin guard.

One file (`auth_db_path`, under `repo_root()`), stdlib `sqlite3`, foreign
keys on, every write inside `transaction()` (BEGIN IMMEDIATE), so two signups racing
for "first account becomes admin" serialize on the store's own lock (AU7, AU24).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from autotester.auth.defaults import ADMIN_SEED, DEFAULT_GROUPS
from autotester.core.paths import repo_root
from autotester.schema.auth import PermissionKey

ENV_AUTH_DIR = "AUTOTESTER_AUTH_DIR"


def auth_db_path() -> Path:
    """The team-login store (T-204): users, groups, sessions, project grants.

    `<repo root>/.auth/auth.sqlite3` (gitignored, never committed), or the directory in
    `AUTOTESTER_AUTH_DIR`. pathlib only, so the same code runs on Windows and Ubuntu."""
    override = os.environ.get(ENV_AUTH_DIR)
    base = Path(override).resolve() if override else repo_root() / ".auth"
    return base / "auth.sqlite3"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '', disabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, seed TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS group_permissions (
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    permission TEXT NOT NULL, PRIMARY KEY (group_id, permission));
CREATE TABLE IF NOT EXISTS memberships (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, group_id));
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_grants (
    slug TEXT NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    relation TEXT NOT NULL, PRIMARY KEY (slug, user_id, relation));
"""

_READY: set[Path] = set()


class LastAdmin(ValueError):
    """The change would leave no enabled Admin/CEO member who can manage users (AU9)."""


class NotAllowed(ValueError):
    """The acting account may not make this change (P5): it would grant what the actor
    does not hold, or touch Admin/CEO without being a member."""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def store_exists() -> bool:
    """A read that finds no store must not create one (AU16: a refused request
    changes no file under the data root)."""
    return auth_db_path().exists()


def _seed_once(conn: sqlite3.Connection) -> None:
    """AU11: seeded exactly once per store; a restart never resets an admin's edits or
    recreates a deleted default group."""
    if conn.execute("SELECT 1 FROM meta WHERE name = 'seeded'").fetchone():
        return
    for seed, (name, permissions) in DEFAULT_GROUPS.items():
        group = conn.execute("INSERT INTO groups (name, seed) VALUES (?, ?)", (name, seed))
        conn.executemany("INSERT INTO group_permissions (group_id, permission) VALUES (?, ?)",
                         [(group.lastrowid, p) for p in sorted(permissions)])
    conn.execute("INSERT INTO meta (name, value) VALUES ('seeded', ?)", (now_iso(),))


def _restrict(path: Path) -> None:
    """Owner-only access where the platform supports it (AU23; best effort on Windows)."""
    if os.name == "posix":
        os.chmod(path.parent, 0o700)
        os.chmod(path, 0o600)


def connect() -> sqlite3.Connection:
    path = auth_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    conn = sqlite3.connect(path, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if fresh or path not in _READY:
        conn.executescript(_SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        _seed_once(conn)
        conn.execute("COMMIT")
        _restrict(path)
        _READY.add(path)
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """One write transaction; rolled back whole on any exception."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.close()


@contextmanager
def reading() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def admin_group_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM groups WHERE seed = ?", (ADMIN_SEED,)).fetchone()
    return int(row["id"]) if row is not None else None


def ensure_an_admin_remains(conn: sqlite3.Connection, after_delete: bool = False) -> None:
    """AU9, called inside a write transaction after any change to users, memberships,
    groups or ticks: while any account exists, the Admin/CEO group must still exist,
    still hold `users.manage`, and still have at least one enabled member. An empty
    store passes (nobody has signed up yet) unless a delete just emptied it."""
    if not after_delete and conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        return
    admin = admin_group_id(conn)
    ok = admin is not None and conn.execute(
        """SELECT EXISTS (SELECT 1 FROM group_permissions WHERE group_id = ? AND permission = ?)
           AND EXISTS (SELECT 1 FROM memberships m JOIN users u ON u.id = m.user_id
                       WHERE m.group_id = ? AND u.disabled = 0)""",
        (admin, PermissionKey.USERS_MANAGE.value, admin),
    ).fetchone()[0]
    if not ok:
        raise LastAdmin("refused: this would leave no enabled Admin/CEO account "
                        "that can manage users")

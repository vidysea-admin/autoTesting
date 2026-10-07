"""Accounts: open signup, first-account admin, password check, admin account actions.

A new account joins no group, so it holds zero permissions until an admin adds it to
one (AU6). The first account becomes Admin/CEO atomically (AU7). Disable, delete and
password reset end the account's sessions in the same transaction (AU3, AU8), and no
change may leave the store without an enabled admin (AU9).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from autotester.auth import db
from autotester.auth.passwords import hash_password, needs_rehash, verify_password
from autotester.schema.auth import User

MAX_EMAIL_LENGTH = 254
MAX_DISPLAY_NAME = 80
FIRST_ADMIN_ENV = "AUTOTESTER_FIRST_ADMIN_EMAIL"


class AccountError(ValueError):
    """A signup or admin action was refused; the message is safe to show."""


def normalize_email(email: str) -> str:
    """Trimmed, lower-cased, one '@' with a non-empty local part and a dotted domain."""
    value = email.strip().lower()
    local, sep, domain = value.partition("@")
    if (not sep or not local or "@" in domain or "." not in domain.strip(".")
            or len(value) > MAX_EMAIL_LENGTH or any(c.isspace() or ord(c) < 32 for c in value)):
        raise AccountError("enter a valid email address")
    return value


def _user(conn: sqlite3.Connection, row: sqlite3.Row) -> User:
    groups = [r["name"] for r in conn.execute(
        "SELECT g.name FROM groups g JOIN memberships m ON m.group_id = g.id "
        "WHERE m.user_id = ? ORDER BY g.name", (row["id"],))]
    return User(id=row["id"], email=row["email"], display_name=row["display_name"],
                disabled=bool(row["disabled"]),
                created_at=datetime.fromisoformat(row["created_at"]), groups=groups)


def _load(conn: sqlite3.Connection, user_id: int) -> User:
    return _user(conn, conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def _becomes_first_admin(conn: sqlite3.Connection, address: str) -> bool:
    """AU7: with no accounts yet, the signup becomes admin. With
    AUTOTESTER_FIRST_ADMIN_EMAIL set, only that address can, while no admin exists."""
    wanted = os.environ.get(FIRST_ADMIN_ENV, "").strip().lower()
    if not wanted:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    admin = db.admin_group_id(conn)
    has_admin = admin is not None and conn.execute(
        "SELECT 1 FROM memberships WHERE group_id = ?", (admin,)).fetchone() is not None
    return address == wanted and not has_admin


def signup(email: str, password: str) -> User:
    """Create an account; it gets a group only when it is the first admin."""
    address = normalize_email(email)
    password_hash = hash_password(password)
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (address,)).fetchone():
            raise AccountError("an account with this email already exists")
        first = _becomes_first_admin(conn, address)
        user_id = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (address, password_hash, db.now_iso()),
        ).lastrowid
        admin = db.admin_group_id(conn)
        if first and admin is not None:
            conn.execute("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                         (user_id, admin))
        return _load(conn, user_id)


def authenticate(email: str, password: str) -> User | None:
    """The account for a correct email + password, or None (wrong, unknown or disabled).
    Every path runs one hash verification (AU2)."""
    try:
        address = normalize_email(email)
    except AccountError:
        address = ""
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (address,)).fetchone()
        stored = row["password_hash"] if row is not None else None
        if not verify_password(stored, password) or row is None or row["disabled"]:
            return None
        user = _user(conn, row)
    if needs_rehash(stored):
        with db.transaction() as conn:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (hash_password(password), user.id))
    return user


def get_user(user_id: int) -> User | None:
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user(conn, row) if row is not None else None


def find_user(email: str) -> User | None:
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?",
                           (email.strip().lower(),)).fetchone()
        return _user(conn, row) if row is not None else None


def list_users() -> list[User]:
    with db.reading() as conn:
        return [_user(conn, r) for r in conn.execute("SELECT * FROM users ORDER BY email")]


def _update(sql: str, args: tuple, user_id: int, end_sessions: bool,
            deleting: bool = False) -> None:
    with db.transaction() as conn:
        if conn.execute(sql, args).rowcount == 0:
            raise AccountError("no such account")
        if end_sessions:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        db.ensure_an_admin_remains(conn, after_delete=deleting)


def set_disabled(user_id: int, disabled: bool) -> None:
    _update("UPDATE users SET disabled = ? WHERE id = ?", (int(disabled), user_id),
            user_id, end_sessions=disabled)


def delete_user(user_id: int) -> None:
    """Sessions, memberships and project relations go with the account (ON DELETE
    CASCADE), so a project it owned has no owner afterwards (AU8)."""
    _update("DELETE FROM users WHERE id = ?", (user_id,), user_id, end_sessions=False,
            deleting=True)


def reset_password(user_id: int, password: str) -> None:
    """Admin reset: a new hash and every existing session of that user revoked (AU8)."""
    _update("UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user_id), user_id, end_sessions=True)


def set_display_name(user_id: int, name: str) -> None:
    clean = " ".join(name.split())
    if len(clean) > MAX_DISPLAY_NAME or any(ord(c) < 32 for c in clean):
        raise AccountError(f"a display name has at most {MAX_DISPLAY_NAME} printable characters")
    _update("UPDATE users SET display_name = ? WHERE id = ?", (clean, user_id),
            user_id, end_sessions=False)


def set_user_groups(user_id: int, group_ids: list[int]) -> None:
    """Replace the account's group memberships with exactly `group_ids`."""
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise AccountError("no such account")
        known = {r["id"] for r in conn.execute("SELECT id FROM groups")}
        if not set(group_ids) <= known:
            raise AccountError("unknown group")
        conn.execute("DELETE FROM memberships WHERE user_id = ?", (user_id,))
        conn.executemany("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                         [(user_id, g) for g in sorted(set(group_ids))])
        db.ensure_an_admin_remains(conn)


def bootstrap_admin(email: str, password: str) -> tuple[User, bool]:
    """CLI break-glass: create the account or reset its password, enable it, put it in
    Admin/CEO and end its old sessions. Returns (user, created)."""
    address = normalize_email(email)
    password_hash = hash_password(password)
    with db.transaction() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (address,)).fetchone()
        if row is None:
            user_id = conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (address, password_hash, db.now_iso()),
            ).lastrowid
        else:
            user_id = row["id"]
            conn.execute("UPDATE users SET password_hash = ?, disabled = 0 WHERE id = ?",
                         (password_hash, user_id))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        admin = db.admin_group_id(conn)
        if admin is None:
            raise AccountError("the Admin/CEO group was deleted; restore it before bootstrap")
        conn.execute("INSERT OR IGNORE INTO memberships (user_id, group_id) VALUES (?, ?)",
                     (user_id, admin))
        return _load(conn, user_id), row is None

"""Accounts: open signup, first-account admin, password check, admin account actions.

A new account joins no group, so it holds zero permissions until an admin adds it to
one (AU6). The first account becomes Admin/CEO atomically (AU7). Disable, delete and
password reset end the account's sessions in the same transaction (AU3, AU8), and no
change may leave the store without an enabled admin (AU9). While Admin/CEO has no member,
a signed-in account may claim it, first claim wins (D-109).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from autotester.auth import access, db
from autotester.auth.config import first_admin_email, public_facing
from autotester.auth.passwords import hash_password, needs_rehash, verify_password
from autotester.schema.auth import Principal, User

MAX_EMAIL_LENGTH = 254
MAX_DISPLAY_NAME = 80


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
                disabled=bool(row["disabled"]), generation=row["generation"],
                created_at=datetime.fromisoformat(row["created_at"]), groups=groups)


def _load(conn: sqlite3.Connection, user_id: int) -> User:
    return _user(conn, conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def _becomes_first_admin(conn: sqlite3.Connection, address: str, secure_cookie: bool) -> bool:
    """AU7 / D-074 (d): with AUTOTESTER_FIRST_ADMIN_EMAIL set, only that address can become
    the first admin, while no admin exists. Unset: on a local loopback server the first
    account becomes admin; on a hosted / non-loopback server nobody does (the CLI
    `bootstrap-admin` creates the first admin)."""
    wanted = first_admin_email()
    if not wanted:
        if public_facing(secure_cookie):
            return False
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    return address == wanted and not _has_admin_member(conn)


def _has_admin_member(conn: sqlite3.Connection) -> bool:
    """True when Admin/CEO exists and has at least one member (enabled or not)."""
    admin = db.admin_group_id(conn)
    return admin is not None and conn.execute(
        "SELECT 1 FROM memberships WHERE group_id = ?", (admin,)).fetchone() is not None


def _claim_refusal(conn: sqlite3.Connection, user_id: int) -> str | None:
    """Why this account may not claim Admin/CEO now (D-109), or None when it may."""
    row = conn.execute("SELECT email, disabled FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None or row["disabled"]:
        return "this account cannot claim admin"
    if db.admin_group_id(conn) is None:
        return "the Admin/CEO group was deleted; restore it first"
    if _has_admin_member(conn):
        return "an administrator already exists"
    wanted = first_admin_email()
    if wanted and row["email"] != wanted:
        return "only the configured first-admin address may claim admin"
    return None


def may_claim_admin(email: str) -> bool:
    """D-109: whether the Claim admin button is shown to this signed-in address (a read;
    `claim_admin` re-checks inside its own transaction)."""
    with db.reading() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row is not None and _claim_refusal(conn, row["id"]) is None


def claim_admin(user_id: int) -> User:
    """D-109: while Admin/CEO has no member, put this account in it. One write transaction
    re-checks emptiness and inserts, so two concurrent claims yield exactly one admin.
    Raises AccountError (message safe to show) when refused."""
    with db.transaction() as conn:
        refusal = _claim_refusal(conn, user_id)
        if refusal is not None:
            raise AccountError(refusal)
        conn.execute("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                     (user_id, db.admin_group_id(conn)))
        db.ensure_an_admin_remains(conn)
        return _load(conn, user_id)


def signup(email: str, password: str, secure_cookie: bool = False) -> User:
    """Create an account; it gets a group only when it is the first admin.
    `secure_cookie`: the request's session cookie is Secure (AU7 counts that as hosted)."""
    address = normalize_email(email)
    password_hash = hash_password(password)
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (address,)).fetchone():
            raise AccountError("an account with this email already exists")
        first = _becomes_first_admin(conn, address, secure_cookie)
        user_id = conn.execute(
            "INSERT INTO users (email, password_hash, created_at, generation) VALUES (?, ?, ?, ?)",
            (address, password_hash, db.now_iso(), db.new_account_generation()),
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


def list_waiting() -> list[User]:
    """Enabled accounts with no group: what a new signup is until an admin decides."""
    return [u for u in list_users() if not u.disabled and not u.groups]


def user_managers() -> list[str]:
    """Emails of enabled accounts holding users.manage: who to tell about a new signup."""
    with db.reading() as conn:
        return [r["email"] for r in conn.execute(
            "SELECT DISTINCT u.email FROM users u JOIN memberships m ON m.user_id = u.id "
            "JOIN group_permissions p ON p.group_id = m.group_id "
            "WHERE p.permission = 'users.manage' AND u.disabled = 0 ORDER BY u.email")]


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
            deleting: bool = False, actor: Principal | None = None) -> None:
    with db.transaction() as conn:
        access.require_may_touch(conn, actor, user_id)
        if conn.execute(sql, args).rowcount == 0:
            raise AccountError("no such account")
        if end_sessions:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        db.ensure_an_admin_remains(conn, after_delete=deleting)


def set_disabled(user_id: int, disabled: bool, actor: Principal | None = None) -> None:
    _update("UPDATE users SET disabled = ? WHERE id = ?", (int(disabled), user_id),
            user_id, end_sessions=disabled, actor=actor)


def delete_user(user_id: int, actor: Principal | None = None) -> None:
    """Sessions, memberships and project relations go with the account (ON DELETE
    CASCADE), so a project it owned has no owner afterwards (AU8)."""
    _update("DELETE FROM users WHERE id = ?", (user_id,), user_id, end_sessions=False,
            deleting=True, actor=actor)


def reset_password(user_id: int, password: str, actor: Principal | None = None) -> None:
    """Admin reset: a new hash and every existing session of that user revoked (AU8).
    Only an Admin/CEO member may reset an admin's password (P5)."""
    _update("UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user_id), user_id, end_sessions=True, actor=actor)


def set_display_name(user_id: int, name: str) -> None:
    clean = " ".join(name.split())
    if len(clean) > MAX_DISPLAY_NAME or any(ord(c) < 32 for c in clean):
        raise AccountError(f"a display name has at most {MAX_DISPLAY_NAME} printable characters")
    _update("UPDATE users SET display_name = ? WHERE id = ?", (clean, user_id),
            user_id, end_sessions=False)


def set_user_groups(user_id: int, group_ids: list[int],
                    actor: Principal | None = None) -> None:
    """Replace the account's group memberships with exactly `group_ids`. With an `actor`
    (P5): only an Admin/CEO member changes Admin/CEO membership, and a group may be added
    only if the actor holds every permission it carries (users.manage alone never mints
    more access than its holder has)."""
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise AccountError("no such account")
        known = {r["id"] for r in conn.execute("SELECT id FROM groups")}
        if not set(group_ids) <= known:
            raise AccountError("unknown group")
        access.require_may_regroup(conn, actor, user_id, set(group_ids))
        conn.execute("DELETE FROM memberships WHERE user_id = ?", (user_id,))
        conn.executemany("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                         [(user_id, g) for g in sorted(set(group_ids))])
        db.ensure_an_admin_remains(conn)


def _require_waiting(conn: sqlite3.Connection, user_id: int) -> None:
    row = conn.execute("SELECT disabled FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise AccountError("no such account")
    if row["disabled"] or conn.execute("SELECT 1 FROM memberships WHERE user_id = ?",
                                       (user_id,)).fetchone():
        raise AccountError("this account is not waiting for access")


def approve_waiting(user_id: int, group_id: int, actor: Principal | None = None) -> None:
    """Put a waiting account (enabled, no group) into `group_id`. Same limits as
    `set_user_groups`; refused, changing nothing, once it already has a group."""
    with db.transaction() as conn:
        _require_waiting(conn, user_id)
        if conn.execute("SELECT 1 FROM groups WHERE id = ?", (group_id,)).fetchone() is None:
            raise AccountError("unknown group")
        access.require_may_regroup(conn, actor, user_id, {group_id})
        conn.execute("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                     (user_id, group_id))


def decline_waiting(user_id: int, actor: Principal | None = None) -> None:
    """Disable a waiting account and end its sessions; refused once it has a group."""
    with db.transaction() as conn:
        _require_waiting(conn, user_id)
        access.require_may_touch(conn, actor, user_id)
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (user_id,))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def bootstrap_admin(email: str, password: str) -> tuple[User, bool]:
    """CLI break-glass: create the account or reset its password, enable it, put it in
    Admin/CEO and end its old sessions. Returns (user, created)."""
    address = normalize_email(email)
    password_hash = hash_password(password)
    with db.transaction() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (address,)).fetchone()
        if row is None:
            user_id = conn.execute(
                "INSERT INTO users (email, password_hash, created_at, generation) "
                "VALUES (?, ?, ?, ?)",
                (address, password_hash, db.now_iso(), db.new_account_generation()),
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

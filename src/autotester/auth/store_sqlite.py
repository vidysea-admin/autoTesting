"""The SQLite implementation of the auth store seam (`auth/store.py`).

The SQL here is the SQL that used to sit inline in `accounts`, `groups`, `sessions` and
`access`, moved without change of behaviour (mongo-store U6a, M29). The connection, schema,
seeding and the last-admin guard stay in `auth/db.py`; this module only adapts one
`sqlite3.Connection` to the `AuthTx` Protocol. Video shares, links, requests and comments
are not on the seam yet (U6c) and keep using `db.transaction()` directly.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from autotester.auth import db
from autotester.schema.auth import Group, Principal, User

_USER_HELD = ("EXISTS (SELECT 1 FROM memberships m JOIN group_permissions p "
              "ON p.group_id = m.group_id WHERE m.user_id = u.id AND p.permission {})")


class SqliteAuthTx:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def _all(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        return self._c.execute(sql, args).fetchall()

    def _one(self, sql: str, args: tuple = ()) -> sqlite3.Row | None:
        return self._c.execute(sql, args).fetchone()

    def _user(self, row: sqlite3.Row | None) -> User | None:
        if row is None:
            return None
        groups = [r["name"] for r in self._all(
            "SELECT g.name FROM groups g JOIN memberships m ON m.group_id = g.id "
            "WHERE m.user_id = ? ORDER BY g.name", (row["id"],))]
        return User(id=row["id"], email=row["email"], display_name=row["display_name"],
                    disabled=bool(row["disabled"]), generation=row["generation"],
                    created_at=datetime.fromisoformat(row["created_at"]), groups=groups)

    # -- users ---------------------------------------------------------------------
    def count_users(self) -> int:
        return int(self._c.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def get_user(self, user_id: int) -> User | None:
        return self._user(self._one("SELECT * FROM users WHERE id = ?", (user_id,)))

    def find_user(self, email: str) -> User | None:
        return self._user(self._one("SELECT * FROM users WHERE email = ?", (email,)))

    def login_record(self, email: str) -> tuple[User, str] | None:
        row = self._one("SELECT * FROM users WHERE email = ?", (email,))
        user = self._user(row)
        return None if row is None or user is None else (user, row["password_hash"])

    def list_users(self) -> list[User]:
        return [u for r in self._all("SELECT * FROM users ORDER BY email")
                if (u := self._user(r)) is not None]

    def user_manager_emails(self) -> list[str]:
        return [r["email"] for r in self._all(
            "SELECT u.email FROM users u WHERE u.disabled = 0 AND "
            + _USER_HELD.format("= 'users.manage'") + " AND "
            + _USER_HELD.format("LIKE 'access.approve@%'") + " ORDER BY u.email")]

    def known_user_ids(self) -> set[int]:
        return {r["id"] for r in self._all("SELECT id FROM users")}

    def insert_user(self, email: str, password_hash: str) -> int:
        cur = self._c.execute(
            "INSERT INTO users (email, password_hash, created_at, generation) "
            "VALUES (?, ?, ?, ?)",
            (email, password_hash, db.now_iso(), db.new_account_generation()))
        return int(cur.lastrowid or 0)

    def set_password_hash(self, user_id: int, password_hash: str) -> bool:
        return self._c.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                               (password_hash, user_id)).rowcount > 0

    def enable_with_password_hash(self, user_id: int, password_hash: str) -> None:
        self._c.execute("UPDATE users SET password_hash = ?, disabled = 0 WHERE id = ?",
                        (password_hash, user_id))

    def set_disabled(self, user_id: int, disabled: bool) -> bool:
        return self._c.execute("UPDATE users SET disabled = ? WHERE id = ?",
                               (int(disabled), user_id)).rowcount > 0

    def set_display_name(self, user_id: int, name: str) -> bool:
        return self._c.execute("UPDATE users SET display_name = ? WHERE id = ?",
                               (name, user_id)).rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        return self._c.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount > 0

    # -- groups and memberships ----------------------------------------------------
    def admin_group_id(self) -> int | None:
        return db.admin_group_id(self._c)

    def admin_has_member(self) -> bool:
        admin = self.admin_group_id()
        return admin is not None and self._one(
            "SELECT 1 FROM memberships WHERE group_id = ?", (admin,)) is not None

    def _group(self, row: sqlite3.Row | None) -> Group | None:
        if row is None:
            return None
        return Group(id=row["id"], name=row["name"], seed=row["seed"],
                     permissions=sorted(self.group_permissions(row["id"])),
                     member_ids=sorted(self.group_member_ids(row["id"])))

    def list_groups(self) -> list[Group]:
        return [g for r in self._all("SELECT * FROM groups ORDER BY id")
                if (g := self._group(r)) is not None]

    def get_group(self, group_id: int) -> Group | None:
        return self._group(self._one("SELECT * FROM groups WHERE id = ?", (group_id,)))

    def known_group_ids(self) -> set[int]:
        return {r["id"] for r in self._all("SELECT id FROM groups")}

    def group_name_taken(self, name: str, except_id: int | None = None) -> bool:
        if except_id is None:
            return self._one("SELECT 1 FROM groups WHERE name = ?", (name,)) is not None
        return self._one("SELECT 1 FROM groups WHERE name = ? AND id != ?",
                         (name, except_id)) is not None

    def insert_group(self, name: str) -> int:
        return int(self._c.execute("INSERT INTO groups (name) VALUES (?)", (name,)).lastrowid or 0)

    def rename_group(self, group_id: int, name: str) -> None:
        self._c.execute("UPDATE groups SET name = ? WHERE id = ?", (name, group_id))

    def delete_group(self, group_id: int) -> bool:
        return self._c.execute("DELETE FROM groups WHERE id = ?", (group_id,)).rowcount > 0

    def group_permissions(self, group_id: int) -> set[str]:
        return {r["permission"] for r in self._all(
            "SELECT permission FROM group_permissions WHERE group_id = ?", (group_id,))}

    def set_group_permissions(self, group_id: int, permissions: set[str]) -> None:
        self._c.execute("DELETE FROM group_permissions WHERE group_id = ?", (group_id,))
        self._c.executemany("INSERT INTO group_permissions (group_id, permission) VALUES (?, ?)",
                            [(group_id, p) for p in sorted(permissions)])

    def group_member_ids(self, group_id: int) -> set[int]:
        return {r["user_id"] for r in self._all(
            "SELECT user_id FROM memberships WHERE group_id = ?", (group_id,))}

    def set_group_members(self, group_id: int, user_ids: set[int]) -> None:
        self._c.execute("DELETE FROM memberships WHERE group_id = ?", (group_id,))
        self._c.executemany("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                            [(u, group_id) for u in sorted(user_ids)])

    def user_group_ids(self, user_id: int) -> set[int]:
        return {r["group_id"] for r in self._all(
            "SELECT group_id FROM memberships WHERE user_id = ?", (user_id,))}

    def set_user_groups(self, user_id: int, group_ids: set[int]) -> None:
        self._c.execute("DELETE FROM memberships WHERE user_id = ?", (user_id,))
        self._c.executemany("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                            [(user_id, g) for g in sorted(group_ids)])

    def add_membership(self, user_id: int, group_id: int, ignore_existing: bool = False) -> None:
        verb = "INSERT OR IGNORE" if ignore_existing else "INSERT"
        self._c.execute(f"{verb} INTO memberships (user_id, group_id) VALUES (?, ?)",
                        (user_id, group_id))

    def ensure_an_admin_remains(self, after_delete: bool = False) -> None:
        db.ensure_an_admin_remains(self._c, after_delete=after_delete)

    # -- sessions ------------------------------------------------------------------
    def insert_session(self, digest: str, user_id: int, created_at: str,
                       expires_at: str) -> None:
        self._c.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?)", (digest, user_id, created_at, expires_at))

    def purge_sessions_before(self, now: str) -> None:
        self._c.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))

    def delete_session(self, digest: str) -> None:
        self._c.execute("DELETE FROM sessions WHERE token_hash = ?", (digest,))

    def delete_session_if_expired(self, digest: str, now: str) -> None:
        self._c.execute("DELETE FROM sessions WHERE token_hash = ? AND expires_at <= ?",
                        (digest, now))

    def delete_user_sessions(self, user_id: int) -> None:
        self._c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def has_session(self, digest: str) -> bool:
        return self._one("SELECT 1 FROM sessions WHERE token_hash = ?", (digest,)) is not None

    def live_principal(self, digest: str, now: str) -> Principal | None:
        row = self._one(
            "SELECT u.id, u.email, u.display_name FROM sessions s JOIN users u "
            "ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ? "
            "AND u.disabled = 0", (digest, now))
        if row is None:
            return None
        perms = frozenset(r["permission"] for r in self._all(
            "SELECT DISTINCT p.permission FROM memberships m JOIN group_permissions p "
            "ON p.group_id = m.group_id WHERE m.user_id = ?", (row["id"],)))
        return Principal(user_id=row["id"], email=row["email"],
                         display_name=row["display_name"], permissions=perms)

    # -- project grants ------------------------------------------------------------
    def project_people(self, slug: str) -> dict[str, set[str]]:
        people: dict[str, set[str]] = {}
        for row in self._all(
                "SELECT g.relation, u.email FROM project_grants g JOIN users u "
                "ON u.id = g.user_id WHERE g.slug = ?", (slug,)):
            people.setdefault(row["relation"], set()).add(row["email"])
        return people

    def replace_project_owner(self, slug: str, user_id: int) -> None:
        self._c.execute("DELETE FROM project_grants WHERE slug = ? AND relation = 'owner'",
                        (slug,))
        self._c.execute("INSERT INTO project_grants (slug, user_id, relation) "
                        "VALUES (?, ?, 'owner')", (slug, user_id))

    def add_project_relation(self, slug: str, user_id: int, relation: str) -> None:
        self._c.execute("INSERT OR IGNORE INTO project_grants (slug, user_id, relation) "
                        "VALUES (?, ?, ?)", (slug, user_id, relation))

    def remove_project_relation(self, slug: str, user_id: int, relation: str) -> None:
        self._c.execute("DELETE FROM project_grants WHERE slug = ? AND user_id = ? "
                        "AND relation = ?", (slug, user_id, relation))


class SqliteAuthStore:
    def exists(self) -> bool:
        return db.store_exists()

    @contextmanager
    def reading(self) -> Iterator[SqliteAuthTx]:
        with db.reading() as conn:
            yield SqliteAuthTx(conn)

    @contextmanager
    def transaction(self) -> Iterator[SqliteAuthTx]:
        with db.transaction() as conn:
            yield SqliteAuthTx(conn)


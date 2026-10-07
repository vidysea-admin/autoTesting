"""IAM-style groups: create, rename, tick permissions, set members, delete (AU10).

Each permission string is validated against the closed catalogue
(`schema.auth.parse_permission`); an unknown key or a scope the key does not allow is
refused and nothing is stored. Every edit re-checks the last-admin guard (AU9).
"""

from __future__ import annotations

import sqlite3

from autotester.auth import db
from autotester.schema.auth import Group, parse_permission

MAX_GROUP_NAME = 64


class GroupError(ValueError):
    """A group edit was refused; the message is safe to show."""


def _clean_name(name: str) -> str:
    value = " ".join(name.split())
    if not value or len(value) > MAX_GROUP_NAME or any(ord(c) < 32 for c in value):
        raise GroupError(f"a group name needs 1 to {MAX_GROUP_NAME} printable characters")
    return value


def validate_permissions(values: list[str]) -> set[str]:
    """Canonical permission strings, or GroupError naming nothing user-supplied."""
    out: set[str] = set()
    for value in values:
        try:
            key, scope = parse_permission(value)
        except (ValueError, KeyError) as exc:
            raise GroupError("unknown permission or scope") from exc
        out.add(key.value if scope is None else f"{key.value}@{scope.value}")
    return out


def _group(conn: sqlite3.Connection, row: sqlite3.Row) -> Group:
    perms = sorted(r["permission"] for r in conn.execute(
        "SELECT permission FROM group_permissions WHERE group_id = ?", (row["id"],)))
    members = [r["user_id"] for r in conn.execute(
        "SELECT user_id FROM memberships WHERE group_id = ? ORDER BY user_id", (row["id"],))]
    return Group(id=row["id"], name=row["name"], permissions=perms, member_ids=members,
                 seed=row["seed"])


def list_groups() -> list[Group]:
    with db.reading() as conn:
        return [_group(conn, r) for r in conn.execute("SELECT * FROM groups ORDER BY id")]


def get_group(group_id: int) -> Group | None:
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
        return _group(conn, row) if row is not None else None


def _set_permissions(conn: sqlite3.Connection, group_id: int, permissions: set[str]) -> None:
    conn.execute("DELETE FROM group_permissions WHERE group_id = ?", (group_id,))
    conn.executemany("INSERT INTO group_permissions (group_id, permission) VALUES (?, ?)",
                     [(group_id, p) for p in sorted(permissions)])


def create_group(name: str, permissions: list[str]) -> Group:
    clean, perms = _clean_name(name), validate_permissions(permissions)
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM groups WHERE name = ?", (clean,)).fetchone():
            raise GroupError("a group with this name already exists")
        new_id = conn.execute("INSERT INTO groups (name) VALUES (?)", (clean,)).lastrowid
        _set_permissions(conn, new_id, perms)
        return _group(conn, conn.execute("SELECT * FROM groups WHERE id = ?",
                                         (new_id,)).fetchone())


def update_group(group_id: int, name: str, permissions: list[str],
                 member_ids: list[int] | None = None) -> Group:
    """Replace the name and ticks; with `member_ids`, the members too. One transaction."""
    clean, perms = _clean_name(name), validate_permissions(permissions)
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM groups WHERE id = ?", (group_id,)).fetchone() is None:
            raise GroupError("no such group")
        if conn.execute("SELECT 1 FROM groups WHERE name = ? AND id != ?",
                        (clean, group_id)).fetchone():
            raise GroupError("a group with this name already exists")
        conn.execute("UPDATE groups SET name = ? WHERE id = ?", (clean, group_id))
        _set_permissions(conn, group_id, perms)
        if member_ids is not None:
            known = {r["id"] for r in conn.execute("SELECT id FROM users")}
            if not set(member_ids) <= known:
                raise GroupError("unknown member")
            conn.execute("DELETE FROM memberships WHERE group_id = ?", (group_id,))
            conn.executemany("INSERT INTO memberships (user_id, group_id) VALUES (?, ?)",
                             [(u, group_id) for u in sorted(set(member_ids))])
        db.ensure_an_admin_remains(conn)
        return _group(conn, conn.execute("SELECT * FROM groups WHERE id = ?",
                                         (group_id,)).fetchone())


def delete_group(group_id: int) -> int:
    """Delete the group; returns how many members lost it. Refused for Admin/CEO while
    it is the last admin path (AU9)."""
    with db.transaction() as conn:
        members = conn.execute("SELECT COUNT(*) FROM memberships WHERE group_id = ?",
                               (group_id,)).fetchone()[0]
        if conn.execute("DELETE FROM groups WHERE id = ?", (group_id,)).rowcount == 0:
            raise GroupError("no such group")
        db.ensure_an_admin_remains(conn)
        return int(members)

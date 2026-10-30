"""IAM-style groups: create, rename, tick permissions, set members, delete (AU10).

Each permission string is validated against the closed catalogue
(`schema.auth.parse_permission`); an unknown key or a scope the key does not allow is
refused and nothing is stored. Every edit re-checks the last-admin guard (AU9).
"""

from __future__ import annotations

from autotester.auth import access
from autotester.auth.defaults import ADMIN_SEED
from autotester.auth.store import auth_store
from autotester.schema.auth import Group, Principal, parse_permission

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


def list_groups() -> list[Group]:
    with auth_store().reading() as tx:
        return tx.list_groups()


def get_group(group_id: int) -> Group | None:
    with auth_store().reading() as tx:
        return tx.get_group(group_id)


def _fetched(group: Group | None) -> Group:
    if group is None:
        raise GroupError("no such group")
    return group


def create_group(name: str, permissions: list[str], actor: Principal | None = None) -> Group:
    clean, perms = _clean_name(name), validate_permissions(permissions)
    with auth_store().transaction() as tx:
        access.require_may_grant(tx, actor, perms)
        if tx.group_name_taken(clean):
            raise GroupError("a group with this name already exists")
        new_id = tx.insert_group(clean)
        tx.set_group_permissions(new_id, perms)
        return _fetched(tx.get_group(new_id))


def update_group(group_id: int, name: str, permissions: list[str],
                 member_ids: list[int] | None = None, actor: Principal | None = None) -> Group:
    """Replace the name and ticks; with `member_ids`, the members too. One transaction.
    With an `actor` (P5): only an Admin/CEO member edits Admin/CEO, and only permissions
    the actor holds (never an admin-only key, unless admin) can be newly ticked or newly
    handed to members."""
    clean, perms = _clean_name(name), validate_permissions(permissions)
    with auth_store().transaction() as tx:
        current = tx.get_group(group_id)
        if current is None:
            raise GroupError("no such group")
        if current.seed == ADMIN_SEED:
            access.require_admin(tx, actor, "edit the Admin/CEO group")
        before = tx.group_permissions(group_id)
        access.require_may_grant(tx, actor, perms - before)
        if member_ids is not None and set(member_ids) - tx.group_member_ids(group_id):
            access.require_may_grant(tx, actor, perms)
        if tx.group_name_taken(clean, except_id=group_id):
            raise GroupError("a group with this name already exists")
        tx.rename_group(group_id, clean)
        tx.set_group_permissions(group_id, perms)
        if member_ids is not None:
            if not set(member_ids) <= tx.known_user_ids():
                raise GroupError("unknown member")
            tx.set_group_members(group_id, set(member_ids))
        tx.ensure_an_admin_remains()
        return _fetched(tx.get_group(group_id))


def delete_group(group_id: int, actor: Principal | None = None) -> int:
    """Delete the group; returns how many members lost it. Refused for Admin/CEO while
    it is the last admin path (AU9), and for a non-admin actor (P5)."""
    with auth_store().transaction() as tx:
        current = tx.get_group(group_id)
        if current is not None and current.seed == ADMIN_SEED:
            access.require_admin(tx, actor, "delete the Admin/CEO group")
        members = len(tx.group_member_ids(group_id))
        if not tx.delete_group(group_id):
            raise GroupError("no such group")
        tx.ensure_an_admin_remains()
        return members

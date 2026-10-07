"""The one authorization function (AU12) and the project relation data it reads.

`authorize(principal, key, resource)` is the only place scopes are evaluated: `all`
always; `assigned` iff the user is an assignee; `own` iff the owner; `shared` iff in
`shared_with`. A project with no recorded owner matches only `@all`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from autotester.auth import db
from autotester.auth.db import NotAllowed
from autotester.schema.auth import (
    CATALOGUE,
    PermissionKey,
    Principal,
    ProjectRelation,
    ResourceRef,
    Scope,
)


def _scope_holds(scope: Scope, email: str, resource: ResourceRef) -> bool:
    if scope is Scope.ALL:
        return True
    if scope is Scope.ASSIGNED:
        return email in resource.assignees
    if scope is Scope.OWN:
        return resource.owner_email is not None and resource.owner_email == email
    return email in resource.shared_with


def authorize(principal: Principal, key: PermissionKey,
              resource: ResourceRef | None = None) -> bool:
    """True when the principal's effective permissions allow `key` on `resource`."""
    if not principal.authenticated:
        return False
    scopes = CATALOGUE[key]
    if not scopes:
        return key.value in principal.permissions
    if resource is None:  # "may this user do it anywhere?" (nav links, list filters)
        return any(f"{key.value}@{s.value}" in principal.permissions for s in scopes)
    return any(f"{key.value}@{s.value}" in principal.permissions
               and _scope_holds(s, principal.email, resource) for s in scopes)


def resource_for(slug: str) -> ResourceRef:
    """The project's owner, assignees and shared-with set, by email."""
    if not db.store_exists():
        return ResourceRef(project_slug=slug)
    people: dict[str, set[str]] = {r.value: set() for r in ProjectRelation}
    with db.reading() as conn:
        for row in conn.execute(
            "SELECT g.relation, u.email FROM project_grants g JOIN users u "
            "ON u.id = g.user_id WHERE g.slug = ?", (slug,)):
            people[row["relation"]].add(row["email"])
    owners = sorted(people[ProjectRelation.OWNER.value])
    return ResourceRef(project_slug=slug, owner_email=owners[0] if owners else None,
                       assignees=frozenset(people[ProjectRelation.ASSIGNED.value]),
                       shared_with=frozenset(people[ProjectRelation.SHARED.value]))


def visible_slugs(principal: Principal, slugs: list[str]) -> list[str]:
    """AU13: only the projects this principal may view."""
    return [s for s in slugs
            if authorize(principal, PermissionKey.PROJECT_VIEW, resource_for(s))]


def set_owner(slug: str, user_id: int) -> None:
    """The creator of a project becomes its one owner."""
    with db.transaction() as conn:
        conn.execute("DELETE FROM project_grants WHERE slug = ? AND relation = ?",
                     (slug, ProjectRelation.OWNER.value))
        conn.execute("INSERT INTO project_grants (slug, user_id, relation) VALUES (?, ?, ?)",
                     (slug, user_id, ProjectRelation.OWNER.value))


def set_relation(slug: str, user_id: int, relation: ProjectRelation, present: bool) -> None:
    """Add or remove an `assigned` or `shared` relation (owner goes through set_owner)."""
    if relation is ProjectRelation.OWNER:
        raise ValueError("ownership changes through set_owner")
    with db.transaction() as conn:
        if present:
            conn.execute("INSERT OR IGNORE INTO project_grants (slug, user_id, relation) "
                         "VALUES (?, ?, ?)", (slug, user_id, relation.value))
        else:
            conn.execute("DELETE FROM project_grants WHERE slug = ? AND user_id = ? "
                         "AND relation = ?", (slug, user_id, relation.value))


# -- P5: who may hand out or touch what ----------------------------------------------
# These keys are admin-only to grant: holding users.manage or groups.manage must not be
# a route to settings, credentials or the Admin group itself.
_ADMIN_ONLY_KEYS = frozenset({PermissionKey.USERS_MANAGE.value, PermissionKey.GROUPS_MANAGE.value,
                              PermissionKey.SETTINGS_MANAGE.value,
                              PermissionKey.CREDENTIALS_VIEW.value})


def acts_as_admin(conn: sqlite3.Connection, actor: Principal | None) -> bool:
    """`None` is the system itself (CLI, tests). `user_id` 0 is the single local operator
    when login is off (AU17). Otherwise: a member of the Admin/CEO group."""
    if actor is None or actor.user_id == 0:
        return True
    admin = db.admin_group_id(conn)
    return (actor.user_id is not None and admin is not None and conn.execute(
        "SELECT 1 FROM memberships WHERE user_id = ? AND group_id = ?",
        (actor.user_id, admin)).fetchone() is not None)


def _held(permissions: frozenset[str], wanted: str) -> bool:
    key, _, scope = wanted.partition("@")
    return wanted in permissions or (bool(scope) and f"{key}@all" in permissions)


def require_may_grant(conn: sqlite3.Connection, actor: Principal | None,
                      permissions: Iterable[str]) -> None:
    """Refuse (NotAllowed) a grant of a permission the actor does not hold, and a grant of
    an admin-only key by a non-admin."""
    if actor is None:
        return
    admin = acts_as_admin(conn, actor)
    for perm in permissions:
        if not _held(actor.permissions, perm):
            raise NotAllowed("refused: you can only grant permissions you hold yourself")
        if perm.partition("@")[0] in _ADMIN_ONLY_KEYS and not admin:
            raise NotAllowed("refused: only an Admin/CEO member can grant "
                             "users.manage, groups.manage, settings.manage or credentials.view")


def require_admin(conn: sqlite3.Connection, actor: Principal | None, what: str) -> None:
    if not acts_as_admin(conn, actor):
        raise NotAllowed(f"refused: only an Admin/CEO member can {what}")


def _group_perms(conn: sqlite3.Connection, group_id: int) -> list[str]:
    return [r["permission"] for r in conn.execute(
        "SELECT permission FROM group_permissions WHERE group_id = ?", (group_id,))]


def require_may_touch(conn: sqlite3.Connection, actor: Principal | None, user_id: int) -> None:
    """Disable, enable, delete or reset the password of an Admin/CEO member: admin only."""
    admin = db.admin_group_id(conn)
    if actor is None or admin is None:
        return
    if conn.execute("SELECT 1 FROM memberships WHERE user_id = ? AND group_id = ?",
                    (user_id, admin)).fetchone() is not None:
        require_admin(conn, actor, "change an Admin/CEO account")


def require_may_regroup(conn: sqlite3.Connection, actor: Principal | None, user_id: int,
                        new_groups: set[int]) -> None:
    if actor is None:
        return
    old = {r["group_id"] for r in conn.execute(
        "SELECT group_id FROM memberships WHERE user_id = ?", (user_id,))}
    admin = db.admin_group_id(conn)
    if admin in (old ^ new_groups):
        require_admin(conn, actor, "change who is in Admin/CEO")
    for group_id in new_groups - old:
        require_may_grant(conn, actor, _group_perms(conn, group_id))

"""The one authorization function (AU12) and the project relation data it reads.

`authorize(principal, key, resource)` is the only place scopes are evaluated: `all`
always; `assigned` iff the user is an assignee; `own` iff the owner; `shared` iff in
`shared_with`. A project with no recorded owner matches only `@all`.
"""

from __future__ import annotations

from autotester.auth import db
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

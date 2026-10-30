"""The one authorization function (AU12) and the project relation data it reads.

`authorize(principal, key, resource)` is the only place scopes are evaluated: `all`
always; `assigned` iff the user is an assignee; `own` iff the owner; `shared` iff in
`shared_with`. A project with no recorded owner matches only `@all`.
"""

from __future__ import annotations

from collections.abc import Iterable

from autotester.auth.db import NotAllowed
from autotester.auth.store import AuthTx, auth_store
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
    store = auth_store()
    if not store.exists():
        return ResourceRef(project_slug=slug)
    with store.reading() as tx:
        people = tx.project_people(slug)
    owners = sorted(people.get(ProjectRelation.OWNER.value, set()))
    return ResourceRef(project_slug=slug, owner_email=owners[0] if owners else None,
                       assignees=frozenset(people.get(ProjectRelation.ASSIGNED.value, set())),
                       shared_with=frozenset(people.get(ProjectRelation.SHARED.value, set())))


def visible_slugs(principal: Principal, slugs: list[str]) -> list[str]:
    """AU13: only the projects this principal may view."""
    return [s for s in slugs
            if authorize(principal, PermissionKey.PROJECT_VIEW, resource_for(s))]


def set_owner(slug: str, user_id: int) -> None:
    """The creator of a project becomes its one owner."""
    with auth_store().transaction() as tx:
        tx.replace_project_owner(slug, user_id)


def set_relation(slug: str, user_id: int, relation: ProjectRelation, present: bool) -> None:
    """Add or remove an `assigned` or `shared` relation (owner goes through set_owner)."""
    if relation is ProjectRelation.OWNER:
        raise ValueError("ownership changes through set_owner")
    with auth_store().transaction() as tx:
        if present:
            tx.add_project_relation(slug, user_id, relation.value)
        else:
            tx.remove_project_relation(slug, user_id, relation.value)


# -- P5: who may hand out or touch what ----------------------------------------------
# These keys are admin-only to grant: holding users.manage or groups.manage must not be
# a route to settings, credentials or the Admin group itself.
_ADMIN_ONLY_KEYS = frozenset({PermissionKey.USERS_MANAGE.value, PermissionKey.GROUPS_MANAGE.value,
                              PermissionKey.SETTINGS_MANAGE.value,
                              PermissionKey.CREDENTIALS_VIEW.value})


def acts_as_admin(tx: AuthTx, actor: Principal | None) -> bool:
    """`None` is the system itself (CLI, tests). `user_id` 0 is the single local operator
    when login is off (AU17). Otherwise: a member of the Admin/CEO group."""
    if actor is None or actor.user_id == 0:
        return True
    admin = tx.admin_group_id()
    return (actor.user_id is not None and admin is not None
            and admin in tx.user_group_ids(actor.user_id))


def _held(permissions: frozenset[str], wanted: str) -> bool:
    key, _, scope = wanted.partition("@")
    return wanted in permissions or (bool(scope) and f"{key}@all" in permissions)


def require_may_grant(tx: AuthTx, actor: Principal | None,
                      permissions: Iterable[str]) -> None:
    """Refuse (NotAllowed) a grant of a permission the actor does not hold, and a grant of
    an admin-only key by a non-admin."""
    if actor is None:
        return
    admin = acts_as_admin(tx, actor)
    for perm in permissions:
        if not _held(actor.permissions, perm):
            raise NotAllowed("refused: you can only grant permissions you hold yourself")
        if perm.partition("@")[0] in _ADMIN_ONLY_KEYS and not admin:
            raise NotAllowed("refused: only an Admin/CEO member can grant "
                             "users.manage, groups.manage, settings.manage or credentials.view")


def require_admin(tx: AuthTx, actor: Principal | None, what: str) -> None:
    if not acts_as_admin(tx, actor):
        raise NotAllowed(f"refused: only an Admin/CEO member can {what}")


def require_may_touch(tx: AuthTx, actor: Principal | None, user_id: int) -> None:
    """Disable, enable, delete or reset the password of an Admin/CEO member: admin only."""
    admin = tx.admin_group_id()
    if actor is None or admin is None:
        return
    if admin in tx.user_group_ids(user_id):
        require_admin(tx, actor, "change an Admin/CEO account")


def require_may_regroup(tx: AuthTx, actor: Principal | None, user_id: int,
                        new_groups: set[int]) -> None:
    if actor is None:
        return
    old = tx.user_group_ids(user_id)
    admin = tx.admin_group_id()
    if admin in (old ^ new_groups):
        require_admin(tx, actor, "change who is in Admin/CEO")
    for group_id in new_groups - old:
        require_may_grant(tx, actor, tx.group_permissions(group_id))

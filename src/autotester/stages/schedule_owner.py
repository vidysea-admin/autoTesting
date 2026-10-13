"""HO24: a schedule has no more rights than its owner, checked at fire time.

`owner_guard` is the `TickDeps.owner_guard` for one project. It re-reads the owner's account
and effective permissions on every slot: a disabled or deleted owner, or one who has lost
`project.run` on the project, gets the schedule paused and a reason returned (the tick records
the slot `refused` with it, and the schedule card shows that reason). With auth switched off
(local mode) or no account store yet there is nothing to check, so it never refuses.
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.auth import db
from autotester.auth.access import authorize, resource_for
from autotester.auth.config import auth_disabled
from autotester.schema.auth import PermissionKey, Principal
from autotester.stages.scheduler import Slot
from autotester.store.project_store import ProjectStore


def owner_principal(email: str | None) -> Principal | None:
    """The owner's live principal, or None when missing or disabled."""
    if not email or not db.store_exists():
        return None
    with db.reading() as conn:
        row = conn.execute("SELECT id, email, display_name FROM users "
                           "WHERE email = ? AND disabled = 0", (email,)).fetchone()
        if row is None:
            return None
        perms = frozenset(r["permission"] for r in conn.execute(
            "SELECT DISTINCT p.permission FROM memberships m JOIN group_permissions p "
            "ON p.group_id = m.group_id WHERE m.user_id = ?", (row["id"],)))
    return Principal(user_id=row["id"], email=row["email"],
                     display_name=row["display_name"], permissions=perms)


def owner_refusal(slug: str, owner: str | None) -> str | None:
    """Why the owner may not run `slug` now, or None. Reads only."""
    who = owner_principal(owner)
    if who is None:
        return "owner_refused: the schedule's owner is disabled or no longer exists"
    if not authorize(who, PermissionKey.PROJECT_RUN, resource_for(slug)):
        return "owner_refused: the schedule's owner no longer holds project.run on this project"
    return None


def owner_guard(slug: str, owner: str | None, store: ProjectStore
                ) -> Callable[[Slot], str | None]:
    """Refuse a slot (and pause the schedule) when the owner has lost the right to run it."""
    def guard(_slot: Slot) -> str | None:
        if auth_disabled() or not db.store_exists():  # no accounts exist to hold rights
            return None
        reason = owner_refusal(slug, owner)
        if reason is not None:
            project = store.load_project()
            if project is not None and project.schedule and not project.schedule.paused:
                store.save_project(project.model_copy(update={
                    "schedule": project.schedule.model_copy(update={"paused": True})}))
        return reason
    return guard

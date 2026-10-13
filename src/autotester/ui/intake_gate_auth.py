"""The real intake gate: sign-in and `video.upload` on that project (team-intake.md TI10, TI11).

`AuthGate` plugs T-204's single `authorize()` into the `IntakeGate` seam. The route policy table
already refuses an anonymous or unauthorised request before a handler runs; this gate is the
second, handler-side check, and the only source of `uploaded_by`: the session's email, never a
form field. `recheck` runs when a queued Drive fetch starts and reads the account and its groups
afresh, so a member disabled or demoted in between gets `refused` and no bytes are fetched
(hosting.md HO19 does the same for runs).

With auth switched off for local use (AU17) the principal has no real account: the gate admits
and records nobody, exactly as `OpenGate` did.
"""

from __future__ import annotations

from fastapi import Request

from autotester.auth import db
from autotester.auth.access import authorize, resource_for
from autotester.auth.config import auth_disabled
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey, Principal
from autotester.schema.intake import IntakeActor
from autotester.ui.intake_gate import IntakeRefused

__all__ = ["AuthGate", "principal_for_email"]

_NO_PROJECT = "No such project."
_NOT_ALLOWED = "You do not have the video.upload permission on this project."


def principal_for_email(email: str) -> Principal | None:
    """The enabled account with this email and its permissions right now, or None."""
    if not db.store_exists():
        return None
    with db.reading() as conn:
        row = conn.execute("SELECT id, email, display_name FROM users WHERE email = ? "
                           "AND disabled = 0", (email,)).fetchone()
        if row is None:
            return None
        perms = frozenset(r["permission"] for r in conn.execute(
            "SELECT DISTINCT p.permission FROM memberships m JOIN group_permissions p "
            "ON p.group_id = m.group_id WHERE m.user_id = ?", (row["id"],)))
    return Principal(user_id=row["id"], email=row["email"],
                     display_name=row["display_name"], permissions=perms)


def _decide(who: Principal | None, slug: str) -> None:
    """Raise `IntakeRefused` unless `who` may add videos to `slug`."""
    if who is None or not who.authenticated:
        raise IntakeRefused(401, "Sign in to add videos.")
    resource = resource_for(slug)
    if not authorize(who, PermissionKey.PROJECT_VIEW, resource):
        raise IntakeRefused(404, _NO_PROJECT)   # same answer as a project that is not there
    if not authorize(who, PermissionKey.VIDEO_UPLOAD, resource):
        raise IntakeRefused(403, _NOT_ALLOWED)


class AuthGate:
    def check(self, request: Request, slug: str) -> IntakeActor:
        who = current_principal()
        _decide(who, slug)
        assert who is not None
        return IntakeActor(email=None if who.user_id == 0 else who.email)

    def recheck(self, actor: IntakeActor, slug: str) -> None:
        if actor.email is None:
            if auth_disabled():
                return
            raise IntakeRefused(401, "Sign in to add videos.")
        _decide(principal_for_email(actor.email), slug)

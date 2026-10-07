"""Team login shapes (T-204, D-072; contract qa/contracts/auth.md): the closed permission
catalogue, accounts, groups, resource references, the request principal, route rules.

A permission is a catalogue key, scoped (`project.view@own`) when the key takes scopes.
A user holds the union of its groups' permissions (additive, no deny, AU10); a new
account holds none until an admin adds it to a group (AU6).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PermissionKey(StrEnum):
    """The closed catalogue (auth.md "Permission catalogue")."""

    PROJECT_VIEW = "project.view"
    PROJECT_CREATE = "project.create"
    PROJECT_EDIT = "project.edit"
    PROJECT_RUN = "project.run"
    PROJECT_ASSIGN = "project.assign"
    REPORT_VIEW = "report.view"
    VIDEO_VIEW = "video.view"
    VIDEO_UPLOAD = "video.upload"
    VIDEO_SHARE = "video.share"
    ACCESS_APPROVE = "access.approve"
    COMMENT_CREATE = "comment.create"
    CREDENTIALS_VIEW = "credentials.view"
    CREDENTIALS_EDIT = "credentials.edit"
    SCHEDULE_MANAGE = "schedule.manage"
    LIVE_VIEW = "live.view"
    LIVE_CONTROL = "live.control"
    USERS_MANAGE = "users.manage"
    GROUPS_MANAGE = "groups.manage"
    SETTINGS_MANAGE = "settings.manage"


class Scope(StrEnum):
    ALL = "all"
    ASSIGNED = "assigned"
    OWN = "own"
    SHARED = "shared"


_A, _S, _O, _SH = Scope.ALL, Scope.ASSIGNED, Scope.OWN, Scope.SHARED
K = PermissionKey

CATALOGUE: dict[PermissionKey, tuple[Scope, ...]] = {
    K.PROJECT_VIEW: (_A, _S, _O, _SH), K.PROJECT_CREATE: (),
    K.PROJECT_EDIT: (_A, _S, _O), K.PROJECT_RUN: (_A, _S, _O), K.PROJECT_ASSIGN: (_A,),
    K.REPORT_VIEW: (_A, _S, _O, _SH), K.VIDEO_VIEW: (_A, _S, _O, _SH),
    K.VIDEO_UPLOAD: (_A, _S, _O), K.VIDEO_SHARE: (_A, _S, _O), K.ACCESS_APPROVE: (_A, _S, _O),
    K.COMMENT_CREATE: (_A, _S, _O, _SH), K.CREDENTIALS_VIEW: (),
    K.CREDENTIALS_EDIT: (_A, _S, _O), K.SCHEDULE_MANAGE: (_A, _S, _O),
    K.LIVE_VIEW: (), K.LIVE_CONTROL: (), K.USERS_MANAGE: (), K.GROUPS_MANAGE: (),
    K.SETTINGS_MANAGE: (),
}
"""Key -> the scopes it allows; an empty tuple means the key is unscoped."""


def parse_permission(text: str) -> tuple[PermissionKey, Scope | None]:
    """`"project.view@own"` -> (key, scope). Raises ValueError for an unknown key, a
    scope the key does not allow, or a scope missing on a scoped key (AU10)."""
    key_text, sep, scope_text = text.strip().partition("@")
    key = PermissionKey(key_text)
    allowed = CATALOGUE[key]
    if not allowed:
        if sep:
            raise ValueError(f"{key.value} takes no scope")
        return key, None
    scope = Scope(scope_text)
    if scope not in allowed:
        raise ValueError(f"{key.value} does not allow @{scope.value}")
    return key, scope


def all_permissions() -> list[str]:
    """Every saveable permission string, in catalogue order."""
    return [k.value if not scopes else f"{k.value}@{s.value}"
            for k, scopes in CATALOGUE.items() for s in (scopes or (None,))]


class User(BaseModel):
    """One account. The password hash never leaves the auth store's own modules."""

    model_config = ConfigDict(extra="forbid")

    id: int
    email: str = Field(description="trimmed, lower-cased, unique")
    display_name: str = ""
    disabled: bool = False
    created_at: datetime
    groups: list[str] = Field(default_factory=list, description="group names")


class Group(BaseModel):
    """An IAM-style group: a name, its ticked permissions, and its members' ids."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    permissions: list[str] = Field(default_factory=list, description="'key' or 'key@scope'")
    member_ids: list[int] = Field(default_factory=list)
    seed: str | None = Field(default=None, description="which default group it was seeded as")


class ProjectRelation(StrEnum):
    OWNER = "owner"
    ASSIGNED = "assigned"
    SHARED = "shared"


class ResourceRef(BaseModel):
    """What `authorize` judges a scoped key against (auth.md Vocabulary)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_slug: str
    owner_email: str | None = None
    assignees: frozenset[str] = frozenset()
    shared_with: frozenset[str] = frozenset()
    video_id: str | None = None


class Principal(BaseModel):
    """Who makes the current request, resolved from a live server-side session.

    `user_id` None is anonymous (a public page)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: int | None = None
    email: str = ""
    display_name: str = ""
    permissions: frozenset[str] = frozenset()

    @property
    def authenticated(self) -> bool:
        return self.user_id is not None


class RouteRule(BaseModel):
    """One row of the central route policy table (AU14).

    kind: `public` (AU16 set), `session` (any signed-in account, even with no groups),
    `member` (signed in with at least one permission), `key` (an unscoped key) or
    `project` (a key judged against the `{slug}` project; unviewable -> 404, AU13)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["public", "session", "member", "key", "project"]
    key: PermissionKey | None = None

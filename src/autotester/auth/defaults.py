"""The four seeded groups and their default ticks (auth.md "Default groups", AU11).

Seeded once into a fresh store; afterwards an admin edits them like any other group.
"""

from __future__ import annotations

from autotester.schema.auth import PermissionKey as K
from autotester.schema.auth import all_permissions

ADMIN_SEED = "admin"
ADMIN_GROUP = "Admin/CEO"

_SCOPED_WORK = (K.PROJECT_VIEW, K.PROJECT_EDIT, K.PROJECT_RUN, K.REPORT_VIEW, K.VIDEO_VIEW,
                K.VIDEO_UPLOAD, K.VIDEO_SHARE, K.ACCESS_APPROVE, K.COMMENT_CREATE,
                K.CREDENTIALS_EDIT, K.SCHEDULE_MANAGE)
_SHARED_READ = (K.PROJECT_VIEW, K.REPORT_VIEW, K.VIDEO_VIEW, K.COMMENT_CREATE)


def _at(scope: str, keys: tuple[K, ...]) -> set[str]:
    return {f"{k.value}@{scope}" for k in keys}


# seed id -> (display name, permissions)
DEFAULT_GROUPS: dict[str, tuple[str, frozenset[str]]] = {
    # every key, every scoped key at @all (only @all scopes are kept for scoped keys)
    ADMIN_SEED: (ADMIN_GROUP, frozenset(
        p for p in all_permissions() if "@" not in p or p.endswith("@all"))),
    "sub-admin": ("Sub-admin", frozenset(_at("assigned", _SCOPED_WORK) | {K.LIVE_VIEW.value})),
    "developer": ("Developer", frozenset(
        {K.PROJECT_CREATE.value, K.LIVE_VIEW.value} | _at("own", _SCOPED_WORK)
        | _at("shared", _SHARED_READ))),
    "tester": ("Tester", frozenset(_at("shared", _SHARED_READ))),
}

# Display order and headings for the group editor's checkboxes (AU10).
PERMISSION_SECTIONS: tuple[tuple[str, tuple[K, ...]], ...] = (
    ("Administration", (K.USERS_MANAGE, K.GROUPS_MANAGE, K.SETTINGS_MANAGE)),
    ("Projects", (K.PROJECT_CREATE, K.PROJECT_VIEW, K.PROJECT_EDIT, K.PROJECT_RUN,
                  K.PROJECT_ASSIGN, K.SCHEDULE_MANAGE)),
    ("Reports, videos and comments", (K.REPORT_VIEW, K.VIDEO_VIEW, K.VIDEO_UPLOAD,
                                      K.VIDEO_SHARE, K.ACCESS_APPROVE, K.COMMENT_CREATE)),
    ("Credentials", (K.CREDENTIALS_VIEW, K.CREDENTIALS_EDIT)),
    ("Live browser", (K.LIVE_VIEW, K.LIVE_CONTROL)),
)

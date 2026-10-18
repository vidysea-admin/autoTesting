"""The per-role state and shared guards of the live role port (MP11, MP15).

One job: the small shapes `stages/role_session_port.py` and its two capability mixins share --
what the port remembers about each role (login outcome, repro steps, visited screens), the errors
it raises, and the guards that stop an oracle from reading a role that is not signed in. Nothing
here touches a browser. Errors carry a role id and a short reason code, never a page, a URL with a
value or a secret, because the oracle registry reports only the exception type and a log may not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from autotester.browser.role_probe import ResponseLog
from autotester.schema.role_signin import RoleSignIn

MAX_SCREENS = 50
MAX_REPRO = 48
WITHHELD_DETAIL = "[withheld: looks like personal data]"


class RoleLoginFailed(RuntimeError):
    """A role could not sign in; nothing may be reported clean for it."""


class RoleNotSignedIn(RuntimeError):
    """A role with a declared sign-in was used before it signed in."""


class UnsupportedStep(ValueError):
    """The step's verb or target cannot be performed by this port."""


class ChannelUnavailable(LookupError):
    """The assertion's channel is not wired on this port (the mailbox is T-212's)."""


@dataclass
class ScreenRecord:
    """One visited screen. `url` is for re-visiting; `shown_url` and `text` are secret-scrubbed."""

    label: str
    url: str
    shown_url: str
    text: str


@dataclass
class RoleState:
    """What the port knows about one role account."""

    log: ResponseLog
    signed_in: bool = False
    failed: str | None = None
    repro: list[str] = field(default_factory=list)
    screens: dict[str, ScreenRecord] = field(default_factory=dict)
    last_log: int | None = None

    def remember(self, step_action: str, *, restart: bool, signed_in_as: str | None) -> None:
        """Extend the replayable steps; a `goto` starts a fresh sequence after the login."""
        if restart:
            self.repro = [f"login {signed_in_as}"] if signed_in_as else []
        self.repro = [*self.repro, step_action][-MAX_REPRO:]

    def keep_screen(self, record: ScreenRecord) -> None:
        key = urlsplit(record.url).path or "/"
        self.screens.pop(key, None)
        self.screens[key] = record
        while len(self.screens) > MAX_SCREENS:
            self.screens.pop(next(iter(self.screens)))


class PortBase:
    """Attributes and guards the capability mixins rely on; `LiveRolePort.__init__` sets them."""

    roles: Any
    _states: dict[str, RoleState]
    _logins: dict[str, RoleSignIn]
    _redactor: Any

    def _guard(self, role_id: str) -> RoleState:
        """The role's state, or an error when it cannot be used (unknown, failed, not in)."""
        account = self.roles.account(role_id)  # KeyError for an unknown id
        state = self._states[role_id]
        if state.failed:
            raise RoleLoginFailed(f"role {role_id} could not sign in ({state.failed})")
        if account.platform_id in self._logins and not state.signed_in:
            raise RoleNotSignedIn(f"role {role_id} has not signed in")
        return state

    def _require_every_role(self) -> None:
        """Whole-run reads (screens, layouts, the network log) refuse a run with a failed login."""
        broken = sorted(rid for rid, st in self._states.items() if st.failed)
        if broken:
            raise RoleLoginFailed(f"role {', '.join(broken)} could not sign in")

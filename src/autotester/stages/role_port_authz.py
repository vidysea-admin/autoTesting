"""The live role port's authorisation capabilities: `ReadTransport`, `EscalationTransport`.

Serves MP18-MP20.

One job: let `oracle_tenant` and `oracle_privilege` probe through real role sessions. `read` GETs a
URL with the role's own cookies and answers one `ProbeReply` (status, and the rows in memory only);
`can_reach` / `assign` / `revert` press the bound role-assign control and its undo
(`ControlBinding`).
Nothing here decides whether a probe may be sent: the signed ADVERSARIAL `RunApproval`, the code
ceiling, the request cap and the write policy are `stages/authz_probe.py` and `oracle_privilege`'s,
and they run before and around every call. This module adds one more refusal of its own: a URL, or
a redirect hop, outside the acting account's platform is never requested (`PlatformScopeError`).

Honesty rules:
  * A redirect to the platform's sign-in page is a 401, not a 200 (a logged-out role did not read).
  * `rows` come from a JSON body only (a list, or an object holding one under a known envelope key,
    or a single object); a page that is not JSON has no rows. They are never written anywhere.
  * A control with no binding raises `UnsupportedStep`, so the oracle cannot count it as "refused".
  * A role signed out while probing raises `RoleLoginFailed` (listed unprobed), never "refused".
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit

from autotester.browser import role_probe
from autotester.browser.secrets import host_of
from autotester.schema.authz_probe import ProbeReply, RoleAssignControl
from autotester.schema.role_control import ControlBinding
from autotester.stages.multi_role_session import PlatformScopeError, host_in_platform
from autotester.stages.role_port_state import (
    AssignUnproven,
    PortBase,
    RoleLoginFailed,
    UnsupportedStep,
)

MAX_ROWS = 200
ENVELOPE_KEYS = ("results", "items", "data", "rows", "records", "value")
UNAUTHENTICATED = 401
SETTLE_MS = 2000


def rows_from(text: str) -> list[dict[str, object]]:
    """The records a JSON response holds, at most `MAX_ROWS`; [] for anything that is not JSON."""
    try:
        data: Any = json.loads(text)
    except ValueError:
        return []
    if isinstance(data, dict):
        held = next((data[k] for k in ENVELOPE_KEYS if isinstance(data.get(k), list)), None)
        data = held if held is not None else [data]
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)][:MAX_ROWS]


class AuthzMixin(PortBase):
    """`read`, `can_reach`, `assign`, `revert`."""

    _controls: dict[str, ControlBinding]

    def read(self, role_id: str, url: str) -> ProbeReply:
        """GET `url` as `role_id`; raises if the role is unusable or the URL leaves its platform."""
        self._guard(role_id)
        absolute = self._absolute(role_id, url)
        platform = self.roles.platform_of(role_id)
        raw = self.roles.run_as(role_id, lambda s: role_probe.http_get(
            s, absolute, lambda target: host_in_platform(platform, host_of(target))))
        if raw.off_platform:
            raise PlatformScopeError("a redirect led outside the role's platform")
        login = self._logins.get(platform.id)
        if login is not None and urlsplit(raw.url).path == urlsplit(login.login_url).path:
            return ProbeReply(status=UNAUTHENTICATED)
        ok = 200 <= raw.status < 300
        return ProbeReply(status=raw.status, rows=rows_from(raw.text) if ok else [])

    def _not_at_login(self, role_id: str, path: str) -> None:
        """A role bounced to the sign-in page is a dead session, not a refused control."""
        login = self._logins.get(self.roles.platform_of(role_id).id)
        if login is not None and path == urlsplit(login.login_url).path:
            raise RoleLoginFailed(f"role {role_id} was signed out while probing")

    def _binding(self, role_id: str, control: RoleAssignControl) -> tuple[ControlBinding, str]:
        binding = self._controls.get(control.id)
        if binding is None:
            raise UnsupportedStep("no binding says how to press or undo this control")
        self._guard(role_id)
        return binding, self._absolute(role_id, control.url)

    def can_reach(self, role_id: str, control: RoleAssignControl) -> bool:
        """Is the assign control on its page for this role?"""
        binding, url = self._binding(role_id, control)

        def look(session: Any) -> bool:
            session.goto(url)
            session.settle(timeout_ms=SETTLE_MS)
            self._not_at_login(role_id, role_probe.path_of(session))
            return role_probe.appears(session, binding.assign_locator)

        return self.roles.run_as(role_id, look)

    def assign(self, role_id: str, control: RoleAssignControl) -> bool:
        """Press the control once; True when the app shows it accepted the assignment.

        Pressed but not shown accepted raises `AssignUnproven`: the oracle then tries the undo and
        records it, because the account may now hold the higher role (MPI4)."""
        binding, url = self._binding(role_id, control)

        def press(session: Any) -> bool:
            session.goto(url)
            session.click(binding.assign_locator)
            session.settle(timeout_ms=SETTLE_MS)
            if not role_probe.appears(session, binding.accepted_target):
                raise AssignUnproven("the control was pressed and its outcome was not shown")
            return True

        return self.roles.run_as(role_id, press)

    def revert(self, role_id: str, control: RoleAssignControl) -> bool:
        """Undo an accepted assignment; True only when the old role is shown to be back."""
        binding, url = self._binding(role_id, control)

        def undo(session: Any) -> bool:
            if not role_probe.appears(session, binding.revert_locator, timeout_ms=500):
                session.goto(url)
            session.click(binding.revert_locator)
            session.settle(timeout_ms=SETTLE_MS)
            return role_probe.appears(session, binding.reverted_target)

        return self.roles.run_as(role_id, undo)

"""The live `RoleSessionPort`: T-210's `RoleSessions` seen through the oracle interface (MP15).

One job: let the six G11 oracles that need a browser run on real role accounts. `LiveRolePort`
wraps an OPEN `RoleSessions` (one isolated, persistent browser context per account, each on its own
thread) and implements `schema/oracle_context.py::RoleSessionPort` (`perform`, `observe`) plus the
optional capabilities the oracle units defined in their own schema files and asked for: typing
(`stages/oracle_negative_input.py::FormInputPort`), `TextSurface` and `LayoutSurface`
(`schema/lint_rule.py`) and `NetworkLogPort` (`schema/request_budget.py`). The protocols are
imported, never redefined. Thread rule: every page touch runs through `RoleSessions.run_as`.

Rules held here, each tested against a real Chromium:
  * Secrets are typed only as `{{SECRET:KEY}}` placeholders resolved at fill time by the session
    (MPI5). Page text and observation detail pass the run's `Redactor`; text that looks like an
    email or a phone number is withheld from `Observation.detail`.
  * A navigation target outside the acting account's own platform is refused before the browser
    moves (`PlatformScopeError`).
  * A role whose sign-in did not reach `RoleSignIn.signed_in_target` is `failed`: every later step,
    look or whole-run read raises, so the registry reports the oracle `errored`, never clean.
  * Steps: `login <role>`, `goto <url>`, `click|submit <locator>`, `fill <locator> {{SECRET:KEY}}`,
    `select <locator> <value>`. A mailbox assertion raises `ChannelUnavailable` (T-212's seam).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urljoin

from autotester.browser import role_probe
from autotester.browser.role_probe import PageSnapshot, ResponseLog
from autotester.browser.secrets import host_of
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_enums import AssertChannel
from autotester.schema.multi_role_finding import ReproVerb, parse_repro_step
from autotester.schema.request_budget import RequestBudget, StepNetworkLog
from autotester.schema.role_signin import RoleSignIn
from autotester.schema.role_step import RoleStep
from autotester.stages.multi_role_session import PlatformScopeError, RoleSessions, host_in_platform
from autotester.stages.role_port_network import NetworkMixin, load_budget
from autotester.stages.role_port_state import (
    WITHHELD_DETAIL,
    ChannelUnavailable,
    RoleLoginFailed,
    RoleState,
    ScreenRecord,
    UnsupportedStep,
)
from autotester.stages.role_port_surface import SurfaceMixin

_BRACES = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
_VALUE_TAIL = re.compile(r"^(?P<loc>.*\S)\s+(?P<val>\S+)$")
_ABSOLUTE = re.compile(r"^https?://", re.IGNORECASE)


class LiveRolePort(SurfaceMixin, NetworkMixin):
    """Drive open `RoleSessions` as the oracles' port. Close the sessions yourself (or `close`)."""

    def __init__(self, roles: RoleSessions, logins: Sequence[RoleSignIn] = (), *,
                 success_selectors: Sequence[str] = (), request_budget: RequestBudget | None = None,
                 bindings: Mapping[str, str] | None = None) -> None:
        self.roles = roles
        self._logins = {login.platform_id: login for login in logins}
        self._success = tuple(success_selectors)
        self._budget = request_budget or load_budget(roles.run_dir)
        self._bindings = dict(bindings or {})
        self._redactor = roles.secrets.redactor()
        self._policy = SafetyPolicy()
        self._logs: list[StepNetworkLog] = []
        self._states = {aid: RoleState(log=ResponseLog()) for aid in roles.accounts}
        _, errors = roles.run_parallel({aid: st.log.attach for aid, st in self._states.items()})
        if errors:
            raise next(iter(errors.values()))

    # -- sign-in ------------------------------------------------------------
    def login(self, role_id: str) -> None:
        """Sign `role_id` in and prove it; on failure the role is marked failed and this raises."""
        state, account = self._states[role_id], self.roles.account(role_id)
        state.attempted = True
        spec = self._logins.get(account.platform_id)
        if spec is None:
            state.failed = "NoSignInDeclared"
            raise RoleLoginFailed(f"role {role_id} has no sign-in declared for its platform")
        try:
            self.roles.sign_in(role_id, spec.login_url, user_locator=spec.user_locator,
                               password_locator=spec.password_locator,
                               submit_locator=spec.submit_locator)
            proven = self.roles.run_as(
                role_id, lambda s: role_probe.appears(s, spec.signed_in_target))
        except Exception as exc:  # the type only: a message may hold a URL
            state.signed_in, state.failed = False, type(exc).__name__
            raise RoleLoginFailed(f"role {role_id} could not sign in ({state.failed})") from None
        state.signed_in, state.failed = proven, None if proven else "SignedInTargetMissing"
        if not proven:
            raise RoleLoginFailed(f"role {role_id} could not sign in ({state.failed})")
        state.repro, state.last_log = [], None
        self.roles.run_as(role_id, lambda _s: state.log.mark())

    def login_all(self) -> dict[str, str]:
        """Sign every account in; returns role id -> reason for each that failed (never raises)."""
        failures: dict[str, str] = {}
        for role_id in self._states:
            try:
                self.login(role_id)
            except RoleLoginFailed as exc:
                failures[role_id] = str(exc)
        return failures

    # -- RoleSessionPort ----------------------------------------------------
    def perform(self, step: RoleStep) -> None:
        """Do `step.action` as `step.role_id`; raises on any failure."""
        verb, target = parse_repro_step(step.action)
        role_id = step.role_id
        if verb is ReproVerb.LOGIN:
            if target != role_id:
                raise UnsupportedStep("a login step names the acting role")
            return self.login(role_id)
        state = self._guard(role_id)
        self._absorb(role_id)
        url = self._absolute(role_id, target) if verb is ReproVerb.GOTO else None
        args = self._split(verb, target)
        snap = self.roles.run_as(role_id, lambda s: self._do(s, role_id, verb, url, args))
        self._after(step, verb, state, snap)

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        """Look at the channel once, as the observer role."""
        role_id = assertion.observer_role_id
        state = self._guard(role_id)
        if assertion.channel is AssertChannel.UI:
            matched, text = self.roles.run_as(
                role_id, lambda s: role_probe.look(s, assertion.target))
        elif assertion.channel is AssertChannel.API:
            matched, text = self.roles.run_as(role_id, lambda _s: state.log.seen(assertion.target))
        else:
            raise ChannelUnavailable(f"channel {assertion.channel.value} is not wired on this port")
        return Observation(matched=matched, detail=self._detail(text))

    def fill_field(self, role_id: str, field: str, value: str) -> None:
        """Type `value` into the form field named `field` (`FormInputPort`)."""
        state = self._guard(role_id)

        def type_it(session: Any) -> None:
            session.fill(role_probe.field_locator(session, field), value)

        self.roles.run_as(role_id, type_it)
        if not contains_personal_shape(field):
            state.remember(f"fill {field}", restart=False, signed_in_as=None)

    def close(self) -> None:
        self.roles.close()

    # -- internals ----------------------------------------------------------
    def _detail(self, text: str) -> str:
        shown = self._redactor.scrub(text)
        return WITHHELD_DETAIL if contains_personal_shape(shown) else shown[:200]

    def _absolute(self, role_id: str, target: str) -> str:
        """The concrete URL for a `goto` target, inside the acting account's own platform."""
        def bind(match: re.Match[str]) -> str:
            if match[1] not in self._bindings:
                raise UnsupportedStep(f"no value bound for the {{{match[1]}}} placeholder")
            return self._bindings[match[1]]

        platform = self.roles.platform_of(role_id)
        bound = _BRACES.sub(bind, target)
        url = bound if _ABSOLUTE.match(bound) else urljoin(platform.base_url, bound)
        if not host_in_platform(platform, host_of(url)):
            raise PlatformScopeError(f"host {host_of(url)!r} is outside platform {platform.id!r}")
        return url

    @staticmethod
    def _split(verb: ReproVerb, target: str) -> tuple[str, str]:
        """(locator, value) for fill and select; (target, "") otherwise."""
        if verb not in (ReproVerb.FILL, ReproVerb.SELECT):
            return target, ""
        match = _VALUE_TAIL.match(target)
        if match is None:
            raise UnsupportedStep(f"a {verb.value} step needs a locator and a value")
        if verb is ReproVerb.FILL and not PLACEHOLDER_RE.fullmatch(match["val"]):
            raise UnsupportedStep("a fill step may carry only a {{SECRET:KEY}} value")
        return match["loc"], match["val"]

    def _do(self, session: Any, role_id: str, verb: ReproVerb, url: str | None,
            args: tuple[str, str]) -> PageSnapshot:
        """Runs on the role's thread: act, let the page settle, read what it shows."""
        target, value = args
        if verb is ReproVerb.GOTO and url is not None:
            session.goto(url)
        elif verb in (ReproVerb.CLICK, ReproVerb.SUBMIT):
            session.click(target)
        elif verb is ReproVerb.FILL:
            session.fill(target, value)
        elif verb is ReproVerb.SELECT:
            session.select_option(target, value)
        session.settle()
        return role_probe.page_snapshot(session, self._success, self._states[role_id].log)

    def _after(self, step: RoleStep, verb: ReproVerb, state: RoleState, snap: PageSnapshot) -> None:
        """Remember the step, the screen it ended on and the requests it caused."""
        goto = verb is ReproVerb.GOTO
        state.remember(step.action, restart=goto,
                       signed_in_as=step.role_id if goto and state.signed_in else None)
        if snap.url.startswith(("http://", "https://")):
            shown = self._redactor.scrub(snap.url)
            label = (shown.split("://", 1)[1].partition("/")[2].split("?")[0] or "/")[:120]
            state.keep_screen(ScreenRecord(label="/" + label.lstrip("/"), url=snap.url,
                                           shown_url=shown, text=self._redactor.scrub(snap.text)))
        self._record_step(step, snap)

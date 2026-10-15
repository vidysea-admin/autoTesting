"""One owned visible browser: scoped secrets, masked evidence and bounded actions (B5-B9)."""

from __future__ import annotations

import contextlib
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autotester.browser import assertions
from autotester.browser.click_recovery import ready_to_click
from autotester.browser.destroy_guard import AccountDestroyRefused, DestroyGuardMixin
from autotester.browser.evidence import MASK_ATTR, MASK_CSS, EvidenceMixin
from autotester.browser.launch import (
    CdpEndpointError,
    forget_cdp_port,
    launch_options,
    verified_cdp_url,
)
from autotester.browser.locators import LocatorMixin
from autotester.browser.secrets import SecretStore, bad_scheme, host_of
from autotester.browser.video import VIDEO_DIR_NAME, VideoMixin
from autotester.core.paths import ProjectPaths
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.enums import EvidenceKind, Outcome
from autotester.schema.flowspec import ExpectedState
from autotester.schema.project import Project
from autotester.schema.run import Evidence
from autotester.stages.run_budget import RunBudget, RunBudgetExceeded

__all__ = ["MASK_ATTR", "MASK_CSS", "AccountDestroyRefused", "BrowserSession", "HitlRequest",
           "NavigationRefused", "SessionState", "check_destination", "launch_options"]


class NavigationRefused(RuntimeError):
    """The destination host is outside the project's allowed domains."""


@dataclass
class HitlRequest:
    """The run must pause for a human (OTP, captcha, consent). B8."""

    prompt: str
    outcome: Outcome = Outcome.BLOCKED_HITL


@dataclass
class SessionState:
    """What the session has done so far — the executor reads this, never the page."""

    run_dir: Path
    evidence: list[Evidence] = field(default_factory=list)
    secret_locators: list[str] = field(default_factory=list)
    hitl: HitlRequest | None = None
    screenshots: int = 0
    evidence_prefix: str = ""
    evidence_start: int = 0


def check_destination(project: Project, url: str) -> str:
    """Return the host if `url` is inside the project's domains, else raise (B6).
    AT-341: `url` can carry a resolved secret (AT-076), so the message never
    embeds `url` itself — only the already-extracted, never-secret HOST."""
    host, bad = host_of(url), bad_scheme(url)
    if bad or not host or not project.allows_domain(host):
        where = (f"scheme {bad!r} (only http and https)" if bad else
                 f"host {host!r}" if host else "an unparseable destination")
        raise NavigationRefused(f"{where} is outside allowed domains {project.allowed_domains}")
    return host


class BrowserSession(DestroyGuardMixin, EvidenceMixin, LocatorMixin, VideoMixin):
    """Drive one project's browser. Construct, `start()`, act, `close()`."""

    def __init__(self, project: Project, secrets: SecretStore, run_dir: Path,
                 paths: ProjectPaths | None = None, *, observer: Any | None = None,
                 record_video: bool = False, expose_cdp: bool = False) -> None:
        self.budget: RunBudget | None = None
        self.project = project
        self.secrets = secrets
        self.paths = paths or ProjectPaths(project.slug)
        self.state = SessionState(run_dir=run_dir)
        self.observer = observer
        self.record_video, self.expose_cdp, self._cdp_url = record_video, expose_cdp, None
        self._video_case_id: str | None = None
        self._video_scratch_id = uuid.uuid4().hex[:12]  # ISS-t191-run-video-1: isolates siblings
        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None

    def start(self) -> BrowserSession:
        from playwright.sync_api import sync_playwright
        self.state.run_dir.mkdir(parents=True, exist_ok=True)
        video_dir = (self.state.run_dir / VIDEO_DIR_NAME / self._video_scratch_id
                     if self.record_video else None)
        self._playwright = sync_playwright().start()
        try:  # `__exit__` never runs when `__enter__` raises: nothing may outlive a failed start
            if self.budget is not None:
                self.budget.check_start()
            timeout = self._timeout()
            forget_cdp_port(self.paths.profile_dir)  # a stale port file must never read as ours
            self._context = self._playwright.chromium.launch_persistent_context(
                **launch_options(self.project, self.paths, record_video_dir=video_dir,
                                 expose_cdp=self.expose_cdp), **timeout
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._timeout()
            if self.expose_cdp:
                self._publish_cdp()
            if self.observer is not None:
                self.observer.attach(self._page)
        except BaseException:
            self._close_quietly()
            raise
        return self

    def _publish_cdp(self) -> None:
        """Record the verified DevTools URL; on any doubt tear the browser down and refuse."""
        try:
            self._cdp_url = verified_cdp_url(self.paths.profile_dir)
        except CdpEndpointError:
            self._close_quietly()
            raise

    def _close_quietly(self) -> None:
        """Teardown on a failure path: a `close()` error must never mask the error being raised.
        `close()` clears its state and the port file, so nothing is left behind."""
        with contextlib.suppress(Exception):
            self.close()

    def close(self) -> None:
        """Close only this session's context and driver (B9). Never a process kill."""
        context, driver = self._context, self._playwright
        self._context = self._page = self._playwright = self._cdp_url = None
        for step in (getattr(context, "close", None), getattr(driver, "stop", None)):
            if callable(step):  # each teardown step guarded: one failure skips none
                with contextlib.suppress(Exception):
                    step()
        with contextlib.suppress(Exception):
            forget_cdp_port(self.paths.profile_dir)
        if self.record_video:
            self._sweep_orphan_videos()

    def _sweep_orphan_videos(self) -> None:
        """Sweep only this session's video scratch, never a sibling's (V1)."""
        scratch = self.state.run_dir / VIDEO_DIR_NAME / self._video_scratch_id
        shutil.rmtree(scratch, ignore_errors=True)

    def __enter__(self) -> BrowserSession:
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @property
    def cdp_url(self) -> str | None:
        """Loopback DevTools endpoint of THIS browser, or None (not started / not exposed)."""
        return self._cdp_url if self._context else None

    @property
    def page(self) -> Any:
        timeout = self._timeout()
        if self._page is None:
            raise RuntimeError("session not started")
        if timeout and callable(getattr(self._page, "set_default_timeout", None)):
            self._page.set_default_timeout(timeout["timeout"])
            self._timeout()
        return self._page

    def _timeout(self, requested: float = 30000) -> dict:
        """Positive supported RPC timeout; no timeout-capable operation gets zero."""
        return {"timeout": self.budget.remaining_ms(requested)} if self.budget else {}

    def goto(self, url: str) -> Evidence:
        """Resolve against secret scope, then bind project destination (AT-076)."""
        real = self.secrets.resolve_for_navigation(url) if PLACEHOLDER_RE.search(url) else url
        check_destination(self.project, real)
        self.page.goto(real, wait_until="domcontentloaded", **self._timeout())
        return self._record(EvidenceKind.URL, self.page.url)

    def fill(self, locator: str, value: str | None, *, step_order: int | None = None) -> None:
        """Type into `locator`. A `{{SECRET:KEY}}` value is resolved for the CURRENT page
        host only (B2/B3, AT-007: never the intended URL) and the input is tagged for masking."""
        is_secret = bool(value and PLACEHOLDER_RE.search(value))
        real = self.secrets.resolve(value, self.page.url) if is_secret else value
        target = self.locate(locator)
        before = self._field_sample(target, locator, secret=is_secret)
        if is_secret:
            target.evaluate(f"el => el.setAttribute('{MASK_ATTR}', '1')", **self._timeout())
            self.state.secret_locators.append(locator)
        target.fill(real or "", **self._timeout())
        after = "unavailable"
        try:
            after = self._field_sample(target, locator, secret=is_secret or before == "[secret]")
        finally:
            self._record(EvidenceKind.DOM, f"filled {locator}"
                         + (" [secret]" if is_secret else "")
                         + f" before={before} after={after}", step_order=step_order)

    def click(self, locator: str, *, step_order: int | None = None) -> Evidence:
        target = self.locate(locator)
        self._guard_destroy(target, locator)
        began = time.monotonic()
        for note in ready_to_click(self.page, target):  # never a force-click; each step recorded
            self._record(EvidenceKind.DOM, f"{note} before clicking {locator}",
                         step_order=step_order)
        spent_ms = (time.monotonic() - began) * 1000  # probes count against the step timeout
        target.click(**self._timeout(max(1.0, 30000 - spent_ms)))
        return self._record(EvidenceKind.DOM, f"clicked {locator}", step_order=step_order)

    def current_url(self) -> str:
        """The page's current URL; the explorer reads this, never `.page` (choke-point)."""
        return str(self.page.url)

    def go_back(self, *, step_order: int | None = None) -> Evidence:
        self.page.go_back(wait_until="domcontentloaded", **self._timeout())
        return self._record(EvidenceKind.URL, self.page.url, step_order=step_order, label="back")

    def hover(self, locator: str, *, step_order: int | None = None) -> Evidence:
        self.locate(locator).hover(**self._timeout())
        return self._record(EvidenceKind.DOM, f"hovered {locator}", step_order=step_order)

    def press_key(
        self, key: str, locator: str | None = None, *, step_order: int | None = None
    ) -> Evidence:
        if locator:
            target = self.locate(locator)
            self._guard_destroy(target, locator)
            target.press(key, **self._timeout())
        else:
            self.page.keyboard.press(key)
        return self._record(EvidenceKind.DOM, f"pressed {key}", step_order=step_order)

    def scroll(self, delta_y: int = 800, *, step_order: int | None = None) -> Evidence:
        self.page.mouse.wheel(0, delta_y)
        return self._record(EvidenceKind.DOM, f"scrolled {delta_y}px", step_order=step_order)

    def select_option(
        self, locator: str, value: str | None, *, step_order: int | None = None
    ) -> Evidence:
        self.locate(locator).select_option(value, **self._timeout())
        return self._record(EvidenceKind.DOM, f"selected {value!r} in {locator}",
                             step_order=step_order)

    def first_option(self, locator: str) -> str | None:
        """A `<select>`'s first non-empty option value (X10-b). `None` when not
        a combobox or nothing selectable — the caller records that honestly."""
        try:
            for option in self.page.locator(locator).locator("option").all():
                value = option.get_attribute("value", **self._timeout())
                if value:
                    return value
        except RunBudgetExceeded:
            raise
        except Exception:
            return None
        return None

    def upload(self, locator: str, file_path: str, *, step_order: int | None = None) -> Evidence:
        self.locate(locator).set_input_files(file_path, **self._timeout())
        return self._record(EvidenceKind.DOM, f"uploaded to {locator}", step_order=step_order)

    def settle(self, expected: ExpectedState | None = None, timeout_ms: int = 8000) -> None:
        """Best-effort transition observation, except a mandatory budget brake."""
        assertions.settle(self, expected, timeout_ms)

    def _met(self, expected: ExpectedState) -> bool:
        """Whether the expectation holds right now (one probe, no waiting)."""
        return assertions.met(self, expected)

    def assert_expected(self, expected: ExpectedState, *,
                        timeout_ms: int = 8000, step_order: int | None = None) -> list:
        """Record deterministic assertions, never grade (D-032/C7)."""
        return assertions.assert_expected(self, expected, timeout_ms=timeout_ms,
                                          step_order=step_order)

    def wait_for(
        self, locator: str | None, *, timeout_ms: int = 5000, step_order: int | None = None
    ) -> Evidence:
        timeout_ms = self._timeout(timeout_ms).get("timeout", timeout_ms)
        if locator:
            self.locate(locator).wait_for(timeout=timeout_ms)
            label = f"waited for {locator}"
        else:
            self.page.wait_for_timeout(timeout_ms)
            label = f"waited {timeout_ms}ms"
        self._timeout()
        return self._record(EvidenceKind.DOM, label, step_order=step_order)

    def request_human(self, prompt: str) -> HitlRequest:
        """Pause for OTP/2FA (B8). The executor turns this into `blocked_hitl`."""
        self.state.hitl = HitlRequest(prompt=prompt)
        return self.state.hitl

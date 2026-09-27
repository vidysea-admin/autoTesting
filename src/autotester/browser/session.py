"""One real, visible browser session per project. Contract: browser-and-secrets.md B5-B9.

The session owns exactly one persistent Chromium context (so a human login
survives to later runs), refuses to leave the project's domains, types secrets
only through the `SecretStore` boundary, masks secret inputs before every
screenshot, and on teardown closes only what it opened — never another
process's Chrome.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autotester.browser import assertions
from autotester.browser.evidence import MASK_ATTR, MASK_CSS, EvidenceMixin
from autotester.browser.launch import launch_options
from autotester.browser.secrets import SecretStore, host_of
from autotester.core.paths import ProjectPaths
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.enums import EvidenceKind, Outcome
from autotester.schema.flowspec import ExpectedState
from autotester.schema.project import Project
from autotester.schema.run import Evidence

__all__ = ["MASK_ATTR", "MASK_CSS", "BrowserSession", "HitlRequest", "NavigationRefused",
           "SessionState", "check_destination", "launch_options"]


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
    """AT-572: a per-case subdirectory name under `run_dir`, set by T-173's
    parallel fan-out so sibling sessions sharing one `run_dir` never collide
    on the same step number; empty (default) leaves the serial path unchanged."""
    evidence_start: int = 0
    """AT-578: index into `evidence` where the CURRENT case begins (set by
    `run_case`, same index AT-577's `RawResult` slice uses); `assertions.py
    ::_network_met` reads it so a reused session's `network` check is never
    satisfied by an earlier case's traffic."""


def check_destination(project: Project, url: str) -> str:
    """Return the host if `url` is inside the project's domains, else raise (B6).
    AT-341: `url` can carry a resolved secret (AT-076), so the message never
    embeds `url` itself — only the already-extracted, never-secret HOST."""
    host = host_of(url)
    if not host or not project.allows_domain(host):
        where = f"host {host!r}" if host else "an unparseable destination"
        raise NavigationRefused(f"{where} is outside allowed domains {project.allowed_domains}")
    return host


class BrowserSession(EvidenceMixin):
    """Drive one project's browser. Construct, `start()`, act, `close()`.

    Every method that touches the page is small on purpose: the executor stage
    composes them per step and records the returned evidence.
    """

    def __init__(self, project: Project, secrets: SecretStore, run_dir: Path,
                 paths: ProjectPaths | None = None, *, observer: Any | None = None) -> None:
        self.project = project
        self.secrets = secrets
        self.paths = paths or ProjectPaths(project.slug)
        self.state = SessionState(run_dir=run_dir)
        self.observer = observer
        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> BrowserSession:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            **launch_options(self.project, self.paths)
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self.state.run_dir.mkdir(parents=True, exist_ok=True)
        if self.observer is not None:
            self.observer.attach(self._page)
        return self

    def close(self) -> None:
        """Close only this session's context and driver (B9). Never a process kill."""
        try:
            if self._context is not None:
                self._context.close()
        finally:
            self._context = self._page = None
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None

    def __enter__(self) -> BrowserSession:
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- actions --------------------------------------------------------------
    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("session not started")
        return self._page

    def goto(self, url: str) -> Evidence:
        """Navigate to `url`. A `{{SECRET:KEY}}` target resolves against its OWN
        declared domains (AT-076: the whole target may be a placeholder — see
        `SecretStore.resolve_for_navigation`); `check_destination` then binds
        `allowed_domains` on the resolved destination."""
        real = self.secrets.resolve_for_navigation(url) if PLACEHOLDER_RE.search(url) else url
        check_destination(self.project, real)
        self.page.goto(real, wait_until="domcontentloaded")
        return self._record(EvidenceKind.URL, self.page.url)

    def fill(self, locator: str, value: str | None, *, step_order: int | None = None) -> None:
        """Type into `locator`. A `{{SECRET:KEY}}` value is resolved for the CURRENT page
        host only (B2/B3, AT-007: never the intended URL) and the input is tagged for masking."""
        is_secret = bool(value and PLACEHOLDER_RE.search(value))
        real = self.secrets.resolve(value, self.page.url) if is_secret else value
        target = self.page.locator(locator)
        if is_secret:
            target.evaluate(f"el => el.setAttribute('{MASK_ATTR}', '1')")
            self.state.secret_locators.append(locator)
        target.fill(real or "")
        self._record(EvidenceKind.DOM, f"filled {locator}" + (" [secret]" if is_secret else ""),
                     step_order=step_order)

    def click(self, locator: str, *, step_order: int | None = None) -> Evidence:
        self.page.locator(locator).click()
        return self._record(EvidenceKind.DOM, f"clicked {locator}", step_order=step_order)

    def current_url(self) -> str:
        """The page's current URL. The explorer (Track B) reads this instead of
        touching `.page` directly (the actuator choke-point)."""
        return str(self.page.url)

    def go_back(self, *, step_order: int | None = None) -> Evidence:
        self.page.go_back(wait_until="domcontentloaded")
        return self._record(EvidenceKind.URL, self.page.url, step_order=step_order, label="back")

    def hover(self, locator: str, *, step_order: int | None = None) -> Evidence:
        self.page.locator(locator).hover()
        return self._record(EvidenceKind.DOM, f"hovered {locator}", step_order=step_order)

    def press_key(
        self, key: str, locator: str | None = None, *, step_order: int | None = None
    ) -> Evidence:
        if locator:
            self.page.locator(locator).press(key)
        else:
            self.page.keyboard.press(key)
        return self._record(EvidenceKind.DOM, f"pressed {key}", step_order=step_order)

    def scroll(self, delta_y: int = 800, *, step_order: int | None = None) -> Evidence:
        self.page.mouse.wheel(0, delta_y)
        return self._record(EvidenceKind.DOM, f"scrolled {delta_y}px", step_order=step_order)

    def select_option(
        self, locator: str, value: str | None, *, step_order: int | None = None
    ) -> Evidence:
        self.page.locator(locator).select_option(value)
        return self._record(EvidenceKind.DOM, f"selected {value!r} in {locator}",
                             step_order=step_order)

    def first_option(self, locator: str) -> str | None:
        """A `<select>`'s first non-empty option value (X10-b). `None` when not
        a combobox or nothing selectable — the caller records that honestly."""
        try:
            for option in self.page.locator(locator).locator("option").all():
                value = option.get_attribute("value")
                if value:
                    return value
        except Exception:
            return None
        return None

    def upload(self, locator: str, file_path: str, *, step_order: int | None = None) -> Evidence:
        self.page.locator(locator).set_input_files(file_path)
        return self._record(EvidenceKind.DOM, f"uploaded to {locator}", step_order=step_order)

    def settle(self, expected: ExpectedState | None = None, timeout_ms: int = 8000) -> None:
        """Best-effort wait for an async page transition (AT-045: the grader
        used to see a click's evidence but never what it caused). Polls the
        step's own declared signal (`expected.url`/`visible_text`) when
        present instead of generic network-idle (AT-046: an inline error
        needs no request); falls back to network-idle+grace otherwise. E5
        holds either way -- purely observation, bounded, never raises."""
        if expected and (expected.url or expected.visible_text):
            self._poll_for_expected(expected, timeout_ms)
            return
        with contextlib.suppress(Exception):
            self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
        with contextlib.suppress(Exception):
            self.page.wait_for_timeout(500)

    def _poll_for_expected(self, expected: ExpectedState, timeout_ms: int) -> None:
        poll_ms = 250
        elapsed = 0
        while elapsed < timeout_ms:
            with contextlib.suppress(Exception):
                if expected.url and expected.url in self.page.url:
                    return
                if expected.visible_text:
                    body = self.page.locator("body").inner_text()
                    if any(text in body for text in expected.visible_text):
                        return
            with contextlib.suppress(Exception):
                self.page.wait_for_timeout(poll_ms)
            elapsed += poll_ms

    def _met(self, expected: ExpectedState) -> bool:
        """Whether the expectation holds right now (one probe, no waiting)."""
        return assertions.met(self, expected)

    def assert_expected(self, expected: ExpectedState, *,
                        timeout_ms: int = 8000, step_order: int | None = None) -> list:
        """D-032/AT-540: evaluate a declared expectation and RECORD the
        result -- deterministic fields only (`url`/`visible_text`/
        `absent_text`/`dom_asserts`/`network`, T-170; `visual_signal` stays
        the judge's). Polls to `timeout_ms`, records one `assert <field>:
        met|unmet` evidence item per field, raises nothing (C7: facts
        recorded, the grader still owns the verdict). Delegates to
        `browser/assertions.py` (the line-cap split)."""
        return assertions.assert_expected(self, expected, timeout_ms=timeout_ms,
                                          step_order=step_order)

    def wait_for(
        self, locator: str | None, *, timeout_ms: int = 5000, step_order: int | None = None
    ) -> Evidence:
        if locator:
            self.page.locator(locator).wait_for(timeout=timeout_ms)
            label = f"waited for {locator}"
        else:
            self.page.wait_for_timeout(timeout_ms)
            label = f"waited {timeout_ms}ms"
        return self._record(EvidenceKind.DOM, label, step_order=step_order)

    def request_human(self, prompt: str) -> HitlRequest:
        """Pause for OTP/2FA (B8). The executor turns this into `blocked_hitl`."""
        self.state.hitl = HitlRequest(prompt=prompt)
        return self.state.hitl

    # `screenshot()` and `_record()` are defined on `EvidenceMixin`
    # (browser/evidence.py, AT-567) and inherited here unchanged.

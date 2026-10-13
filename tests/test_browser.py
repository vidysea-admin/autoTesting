"""Browser session. Contract: qa/contracts/browser-and-secrets.md B5-B9.

Domain refusal, masking, HITL, and cleanup scope run without a browser. The
launch test needs Playwright's Chromium and is skipped when it is absent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.browser.session import (
    MASK_ATTR,
    MASK_CSS,
    BrowserSession,
    NavigationRefused,
    check_destination,
    launch_options,
)
from autotester.core.paths import ProjectPaths
from autotester.schema.enums import EvidenceKind, Outcome
from autotester.schema.project import Project, SecretRef

PASSWORD = "hunter2-trombone-staple"


def make_project(headed: bool = True) -> Project:
    return Project(
        slug="pathlynks", name="Pathlynks", base_url="https://app.pathlynks.test",
        allowed_domains=["pathlynks.test"], headed=headed,
        secrets=[SecretRef(key="PATHLYNKS_PASSWORD", domains=["app.pathlynks.test"])],
    )


def make_store(tmp_path: Path) -> SecretStore:
    env = tmp_path / ".env"
    env.write_text(f"PATHLYNKS_PASSWORD={PASSWORD}\n", encoding="utf-8")
    return SecretStore.load(make_project(), env)


class FakeLocator:
    def __init__(self, page: FakePage, selector: str) -> None:
        self.page, self.selector = page, selector

    def evaluate(self, script: str) -> None:
        self.page.attrs.setdefault(self.selector, []).append(script)

    def fill(self, value: str) -> None:
        self.page.filled[self.selector] = value

    def click(self) -> None:
        self.page.clicks.append(self.selector)

    def inner_text(self) -> str:
        return self.page.body_text


class FakePage:
    """Just enough of a Playwright page to exercise the session without a browser."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.filled: dict[str, str] = {}
        self.attrs: dict[str, list[str]] = {}
        self.clicks: list[str] = []
        self.styles: list[str] = []
        self.shots: list[str] = []
        self.body_text = ""

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def add_style_tag(self, content: str) -> None:
        self.styles.append(content)

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.shots.append(path)
        Path(path).write_bytes(b"png")

    def wait_for_timeout(self, timeout_ms: int) -> None:
        pass

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url


LOGIN = "https://app.pathlynks.test/login"


def session_with_fake_page(tmp_path: Path, url: str = LOGIN) -> BrowserSession:
    paths = ProjectPaths("pathlynks", tmp_path)
    s = BrowserSession(make_project(), make_store(tmp_path), tmp_path / "run", paths)
    s._page = FakePage(url)
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


# -- B5 headed by default, own profile -------------------------------------

def test_launch_options_are_headed_by_default_with_a_project_profile(tmp_path: Path) -> None:
    opts = launch_options(make_project(), ProjectPaths("pathlynks", tmp_path))
    assert opts["headless"] is False
    assert opts["user_data_dir"] == str(tmp_path / "profiles" / "pathlynks")
    headless = launch_options(make_project(headed=False), ProjectPaths("pathlynks", tmp_path))
    assert headless["headless"] is True


# -- B6 bounded navigation --------------------------------------------------

def test_destination_outside_allowed_domains_is_refused() -> None:
    project = make_project()
    staging = "https://staging.pathlynks.test/x"
    assert check_destination(project, staging) == "staging.pathlynks.test"
    bad_hosts = ("https://evil.test", "https://notpathlynks.test",
                 "https://evil.test" + chr(92) + "@pathlynks.test", "")
    for bad in bad_hosts:
        with pytest.raises(NavigationRefused):
            check_destination(project, bad)


def test_refusal_message_never_embeds_the_raw_destination(tmp_path: Path) -> None:
    """AT-341: `url` can carry a resolved secret value (AT-076), so the
    refusal message must never build itself from `url` — only from the
    already-extracted host, which is never secret. Holds for every caller,
    not only a secret-bearing one."""
    project = make_project()
    with pytest.raises(NavigationRefused) as excinfo:
        check_destination(project, "https://evil.test/some-distinctive-marker-xyz")
    assert "some-distinctive-marker-xyz" not in str(excinfo.value)
    assert "evil.test" in str(excinfo.value)


def test_goto_refuses_before_touching_the_page(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    with pytest.raises(NavigationRefused):
        s.goto("https://evil.test/login")
    assert s.page.url == "https://app.pathlynks.test/login"


# -- B2/B3 secrets resolved for the CURRENT page host only -------------------

def test_fill_resolves_secret_for_current_page_host_and_tags_the_input(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s.fill("input[name=password]", "{{SECRET:PATHLYNKS_PASSWORD}}", step_order=2)
    assert s.page.filled["input[name=password]"] == PASSWORD
    assert any(MASK_ATTR in js for js in s.page.attrs["input[name=password]"])
    assert s.state.secret_locators == ["input[name=password]"]
    assert PASSWORD not in " ".join(e.path for e in s.state.evidence)


def test_fill_refuses_secret_when_page_has_drifted_off_domain(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path, url="https://evil.test/phish")
    with pytest.raises(Exception, match=re.escape("evil.test")):
        s.fill("input[name=password]", "{{SECRET:PATHLYNKS_PASSWORD}}")
    assert s.page.filled == {}


# -- B7 masked capture -----------------------------------------------------

def test_screenshot_masks_before_capture_and_records_masked_evidence(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    ev = s.screenshot("login-form", step_order=1)
    assert s.page.styles == [MASK_CSS] and MASK_ATTR in MASK_CSS
    assert ev.kind is EvidenceKind.SCREENSHOT and ev.masked is True
    assert ev.path == "01-login-form.png" and (s.state.run_dir / ev.path).exists()


class _FlakyCaptureScreenshotPage(FakePage):
    """AT-036: raises the exact transient CDP error once, then succeeds."""

    def __init__(self, url: str, fail_times: int) -> None:
        super().__init__(url)
        self.fail_times = fail_times
        self.waited_ms: list[int] = []

    def screenshot(self, path: str, full_page: bool = False) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise Exception(
                "Page.screenshot: Protocol error (Page.captureScreenshot): "
                "Unable to capture screenshot"
            )
        super().screenshot(path, full_page)

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.waited_ms.append(timeout_ms)


def test_screenshot_retries_once_on_the_known_transient_protocol_error(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s._page = _FlakyCaptureScreenshotPage(LOGIN, fail_times=1)
    ev = s.screenshot("login-form", step_order=1)
    assert ev.path == "01-login-form.png" and (s.state.run_dir / ev.path).exists()
    assert s.page.waited_ms == [250]


def test_screenshot_gives_up_after_a_second_consecutive_failure(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    s._page = _FlakyCaptureScreenshotPage(LOGIN, fail_times=2)
    with pytest.raises(Exception, match="captureScreenshot"):
        s.screenshot("login-form", step_order=1)


def test_screenshot_does_not_retry_a_different_error(tmp_path: Path) -> None:
    class _OtherErrorPage(FakePage):
        def screenshot(self, path: str, full_page: bool = False) -> None:
            raise Exception("Target page, context or browser has been closed")

    s = session_with_fake_page(tmp_path)
    s._page = _OtherErrorPage(LOGIN)
    with pytest.raises(Exception, match="has been closed"):
        s.screenshot("login-form", step_order=1)


def test_evidence_paths_are_scrubbed(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    ev = s._record(EvidenceKind.DOM, f"body contains {PASSWORD}")
    assert PASSWORD not in ev.path and "PATHLYNKS_PASSWORD" in ev.path


# -- B8 human in the loop --------------------------------------------------

def test_request_human_surfaces_blocked_hitl(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    req = s.request_human("Enter the OTP sent to the test account's email")
    assert req.outcome is Outcome.BLOCKED_HITL and s.state.hitl is req


# -- B9 cleanup scope -------------------------------------------------------

def test_no_process_wide_browser_kill_anywhere_in_the_codebase() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    offenders = [p for p in src.rglob("*.py")
                 if re.search(r"taskkill|pkill|killall|chrome\.exe", p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_close_only_closes_own_context_and_is_idempotent(tmp_path: Path) -> None:
    class Ctx:
        closed = 0

        def close(self) -> None:
            self.closed += 1

    class Pw:
        stopped = 0

        def stop(self) -> None:
            self.stopped += 1

    s = session_with_fake_page(tmp_path)
    ctx, pw = Ctx(), Pw()
    s._context, s._playwright = ctx, pw
    s.close()
    s.close()
    assert (ctx.closed, pw.stopped) == (1, 1) and s._page is None


# -- real browser (skipped when Chromium is not installed) --------------------

def test_real_headless_launch_navigates_a_data_url(tmp_path: Path) -> None:
    pytest.importorskip("playwright")
    project = make_project(headed=False)
    project.allowed_domains.append("example.com")
    paths = ProjectPaths("pathlynks", tmp_path)
    s = BrowserSession(project, make_store(tmp_path), tmp_path / "run", paths)
    try:
        s.start()
    except Exception as exc:  # browser binary missing on this machine
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    try:
        with pytest.raises(NavigationRefused):
            s.goto("https://evil.test")
        ev = s.screenshot("blank")
        assert (s.state.run_dir / ev.path).stat().st_size > 0
    finally:
        s.close()

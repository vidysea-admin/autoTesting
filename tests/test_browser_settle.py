"""BrowserSession.settle(). Contract: qa/contracts/browser-and-secrets.md B5-B9
(same contract as test_browser.py — split out purely to stay under the
300-line design limit once AT-045/AT-046 tests were added there).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_parallel_run import _approval

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.flowspec import ExpectedState
from autotester.schema.project import Project, SecretRef
from autotester.stages.run_budget import RunBudget, RunBudgetExceeded

PASSWORD = "hunter2-trombone-staple"
LOGIN = "https://app.pathlynks.test/login"


def make_project() -> Project:
    return Project(
        slug="pathlynks", name="Pathlynks", base_url=LOGIN,
        allowed_domains=["pathlynks.test"],
        secrets=[SecretRef(key="PATHLYNKS_PASSWORD", domains=["pathlynks.test"])],
    )


def make_store(tmp_path: Path) -> SecretStore:
    env = tmp_path / ".env"
    env.write_text(f"PATHLYNKS_PASSWORD={PASSWORD}\n", encoding="utf-8")
    return SecretStore.load(make_project(), env)


class FakeLocator:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def inner_text(self) -> str:
        return self.page.body_text


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.body_text = ""

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self)

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        pass

    def wait_for_timeout(self, timeout_ms: int) -> None:
        pass


def session_with_fake_page(tmp_path: Path) -> BrowserSession:
    paths = ProjectPaths("pathlynks", tmp_path)
    s = BrowserSession(make_project(), make_store(tmp_path), tmp_path / "run", paths)
    s._page = FakePage(LOGIN)
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


# -- AT-045 settle: bounded, never raises ------------------------------------

def test_settle_calls_wait_for_load_state_then_a_short_grace_wait(tmp_path: Path) -> None:
    calls: list[tuple[str, int]] = []
    s = session_with_fake_page(tmp_path)
    s.page.wait_for_load_state = lambda state, timeout: calls.append((state, timeout))
    s.page.wait_for_timeout = lambda ms: calls.append(("grace", ms))

    s.settle()

    assert calls == [("networkidle", 8000), ("grace", 500)]


def test_settle_still_takes_the_grace_wait_when_network_never_idles(tmp_path: Path) -> None:
    """A page with no post-error network activity at all (a pure client-side
    re-render) never reaches network-idle -- the fixed grace period after it
    is what actually lets the re-render finish before the screenshot."""
    calls: list[tuple[str, int]] = []
    s = session_with_fake_page(tmp_path)

    def _raise(state: str, timeout: int) -> None:
        raise TimeoutError("networkidle never reached")

    s.page.wait_for_load_state = _raise
    s.page.wait_for_timeout = lambda ms: calls.append(("grace", ms))

    s.settle()  # must not raise

    assert calls == [("grace", 500)]


# -- AT-046 settle polls for the step's own declared expected condition -----

def test_settle_polls_for_expected_url_and_returns_the_instant_it_changes(
    tmp_path: Path,
) -> None:
    s = session_with_fake_page(tmp_path)
    ticks: list[int] = []

    def _tick(ms: int) -> None:
        ticks.append(ms)
        s.page.url = "https://app.pathlynks.test/dashboard"

    s.page.wait_for_timeout = _tick

    s.settle(ExpectedState(url="dashboard"))

    assert ticks == [250]  # returned after one poll, not the full bound


def test_settle_polls_for_expected_visible_text_and_returns_the_instant_it_appears(
    tmp_path: Path,
) -> None:
    s = session_with_fake_page(tmp_path)
    s.page.body_text = "Signing in…"
    ticks: list[int] = []

    def _tick(ms: int) -> None:
        ticks.append(ms)
        s.page.body_text = "Invalid credentials"

    s.page.wait_for_timeout = _tick

    s.settle(ExpectedState(visible_text=["Invalid credentials"]))

    assert ticks == [250]


def test_settle_gives_up_after_its_bound_when_expected_never_appears(tmp_path: Path) -> None:
    s = session_with_fake_page(tmp_path)
    ticks: list[int] = []
    s.page.wait_for_timeout = lambda ms: ticks.append(ms)

    s.settle(ExpectedState(visible_text=["never shows up"]), timeout_ms=1000)  # must not hang

    assert ticks == [250, 250, 250, 250]


@pytest.mark.parametrize("phase", ["settle", "poll", "assert", "retry"])
def test_browser_observation_phases_never_swallow_deadline(tmp_path, monkeypatch, phase):
    from autotester.stages import run_budget

    clock = [0.0]
    monkeypatch.setattr(run_budget.time, "monotonic", lambda: clock[0])
    session = session_with_fake_page(tmp_path)
    session.budget = RunBudget(_approval(wall_clock_s=1, max_probes=100))
    page, waits = session.page, []
    def expire(ms):
        assert 0 < ms <= 1000
        waits.append(ms)
        clock[0] = 1.0
    page.wait_for_timeout = expire
    page.wait_for_load_state = lambda state, timeout: expire(timeout)
    def shot(**kwargs):
        assert 0 < kwargs["timeout"] <= 1000
        raise RuntimeError("captureScreenshot transient")
    page.screenshot = shot
    page.add_style_tag = lambda **kw: None
    with pytest.raises(RunBudgetExceeded, match="wall_clock_s"):
        if phase == "settle":
            session.settle()
        elif phase == "poll":
            session.settle(ExpectedState(url="never"))
        elif phase == "assert":
            session.assert_expected(ExpectedState(url="never"))
        else:
            session.screenshot("retry")
    assert len(waits) == 1 and session.budget.stop_reason == "wall_clock_s"


def test_browser_startup_checks_before_and_after_launch(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from playwright import sync_api

    from autotester.stages import run_budget

    clock, launches = [0.0], []
    monkeypatch.setattr(run_budget.time, "monotonic", lambda: clock[0])
    def launch(**kwargs):
        assert 0 < kwargs["timeout"] <= 1000
        launches.append(kwargs["timeout"])
        clock[0] = 1.0
        return SimpleNamespace(pages=[object()])
    driver = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))
    monkeypatch.setattr(sync_api, "sync_playwright", lambda: SimpleNamespace(start=lambda: driver))
    session = session_with_fake_page(tmp_path)
    session.budget = RunBudget(_approval(wall_clock_s=1))
    with pytest.raises(RunBudgetExceeded, match="wall_clock_s"):
        session.start()
    assert launches == [1000]
    with pytest.raises(RunBudgetExceeded, match="wall_clock_s"):
        session.start()
    assert launches == [1000]

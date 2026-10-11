"""AT-888: after ANY case outcome the next case on a shared session starts on a live page.

Fake-session unit tests. The fake context mimics a HEADED persistent Chromium: closing its last
page ends the browser, after which `new_page()` raises "Failed to open a new tab" (measured with
a real headed browser, `.work/repro_at888.py`). The real-browser counterpart is
`test_session_survives_failure_live.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.browser.video import SessionRestoreError
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project


class FakePage:
    def __init__(self, ctx: FakeContext, n: int) -> None:
        self.ctx, self.n, self.closed, self.scripts = ctx, n, False, []
        self.video = None

    def add_init_script(self, script: str) -> None:
        self.scripts.append(script)

    def close(self) -> None:
        if self.ctx.dead:
            raise RuntimeError("Target page, context or browser has been closed")
        self.closed = True
        if not any(not p.closed for p in self.ctx.pages):
            self.ctx.dead = True  # headed Chromium: the last window closing ends the browser

    def is_closed(self) -> bool:
        return self.closed


class FakeContext:
    def __init__(self) -> None:
        self.pages: list[FakePage] = []
        self.dead = False

    def new_page(self) -> FakePage:
        if self.dead:
            raise RuntimeError("BrowserContext.new_page: Failed to open a new tab")
        page = FakePage(self, len(self.pages))
        self.pages.append(page)
        return page

    def close(self) -> None:
        if self.dead:
            raise RuntimeError("TargetClosedError: browser has been closed")
        self.dead = True


class FakePlaywright:
    def stop(self) -> None:
        pass


def _session(tmp_path: Path) -> tuple[BrowserSession, list[FakeContext]]:
    project = Project(slug="at888", name="t", base_url="http://127.0.0.1/",
                      allowed_domains=["127.0.0.1"])
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    session = BrowserSession(project, secrets, tmp_path / "run", ProjectPaths("at888", tmp_path),
                             record_video=True)
    contexts: list[FakeContext] = []

    def start() -> BrowserSession:
        ctx = FakeContext()
        contexts.append(ctx)
        session._playwright, session._context = FakePlaywright(), ctx
        session._page = ctx.new_page()
        return session

    session.start = start  # type: ignore[method-assign]
    start()
    return session, contexts


def _alive(session: BrowserSession) -> bool:
    return session._page is not None and not session._page.closed and not session._context.dead


# What the case did to the browser between begin_case_video and end_case_video.
def _passes(s: BrowserSession) -> None:
    pass


def _fails_assertion(s: BrowserSession) -> None:
    pass  # a FAIL/ERRORED/timeout leaves the page exactly as a pass does: the page object is open


def _closes_own_page(s: BrowserSession) -> None:
    s._page.close()


def _page_crashed(s: BrowserSession) -> None:
    s._page.close = lambda: (_ for _ in ()).throw(RuntimeError("Target crashed"))  # type: ignore


def _opens_a_popup_and_closes_it(s: BrowserSession) -> None:
    popup = s._context.new_page()
    popup.close()


def _browser_dies_mid_case(s: BrowserSession) -> None:
    s._context.dead = True


OUTCOMES: list[Callable[[BrowserSession], None]] = [
    _passes, _fails_assertion, _closes_own_page, _page_crashed, _opens_a_popup_and_closes_it,
    _browser_dies_mid_case,
]
# headed Chromium: a case closing its own last page ends the browser, as a crash does
DIES = {_browser_dies_mid_case, _closes_own_page}


@pytest.mark.parametrize("outcome", OUTCOMES, ids=lambda f: f.__name__)
def test_the_next_case_starts_on_a_live_page_after_any_outcome(
    tmp_path: Path, outcome: Callable[[BrowserSession], None],
) -> None:
    session, contexts = _session(tmp_path)
    for case_id in ("case-1", "case-2", "case-3"):
        session.begin_case_video(case_id)
        assert _alive(session), f"{case_id} did not start on a live page after {outcome.__name__}"
        if case_id == "case-1":
            outcome(session)
        session.end_case_video()
    # a restart happens only when the browser itself died, and then exactly once
    assert len(contexts) == (2 if outcome in DIES else 1)


@pytest.mark.parametrize("outcome", OUTCOMES, ids=lambda f: f.__name__)
def test_a_live_session_is_never_left_without_a_page_after_a_case(
    tmp_path: Path, outcome: Callable[[BrowserSession], None],
) -> None:
    """The reproduced root cause: end_case_video closed the context's LAST page."""
    session, _ = _session(tmp_path)
    session.begin_case_video("case-1")
    outcome(session)
    session.end_case_video()
    if outcome not in DIES:
        assert any(not p.closed for p in session._context.pages)


def test_a_restart_is_a_recorded_event_not_a_silent_retry(tmp_path: Path) -> None:
    session, _ = _session(tmp_path)
    session.begin_case_video("case-1")
    _browser_dies_mid_case(session)
    session.end_case_video()
    session.begin_case_video("case-2")
    events = session.take_session_events()
    assert [e.label for e in events] == ["session-restart"]
    assert "restarted" in events[0].path and "Failed to open a new tab" in events[0].path
    assert session.take_session_events() == []  # drained: reported once, on the case it hit


def test_the_mask_init_script_is_on_the_page_of_every_case_including_after_a_restart(
    tmp_path: Path,
) -> None:
    session, _ = _session(tmp_path)
    for case_id in ("case-1", "case-2"):
        session.begin_case_video(case_id)
        if case_id == "case-1":
            _browser_dies_mid_case(session)
        assert len(session._page.scripts) == 1 and "MutationObserver" in session._page.scripts[0]
        session.end_case_video()


def test_an_unrestorable_session_raises_a_named_error_and_does_not_relaunch_per_case(
    tmp_path: Path,
) -> None:
    session, contexts = _session(tmp_path)
    launches = []

    def failing_start() -> BrowserSession:
        launches.append(1)
        raise OSError("profile locked by another chrome")

    session.begin_case_video("case-1")
    session.end_case_video()
    contexts[0].dead = True
    session.start = failing_start  # type: ignore[method-assign]
    for case_id in ("case-2", "case-3"):
        with pytest.raises(SessionRestoreError, match="profile locked"):
            session.begin_case_video(case_id)
    assert len(launches) == 1  # one restart attempt, then the cause is latched
    assert session.end_case_video() is None  # no case page, no video, no crash


def test_end_case_video_survives_a_browser_that_died_during_the_case(
    tmp_path: Path,
) -> None:
    session, _ = _session(tmp_path)
    session.begin_case_video("case-1")
    _browser_dies_mid_case(session)
    assert session.end_case_video() is None  # page.video is None on the fake; no raise


@pytest.mark.parametrize("which", ["run_and_grade_case", "run_and_grade_case_resilient"])
def test_a_session_restart_travels_on_the_cases_result_through_both_pipeline_paths(
    tmp_path: Path, which: str,
) -> None:
    """The event must reach `RawResult.evidence` (it is what the report and the grader read);
    `run_case` slices evidence from the length AFTER `begin_case_video`, so the pipeline
    attaches it."""
    from test_run_case_pipeline import _case, _project, _session

    from autotester.providers.mock import MockProvider
    from autotester.schema.enums import EvidenceKind, Result
    from autotester.schema.run import Evidence
    from autotester.schema.verdict import Judgment
    from autotester.stages import run_case_pipeline as pipe
    from autotester.store.project_store import ProjectStore

    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    session = _session(tmp_path)
    event = Evidence(kind=EvidenceKind.DOM, path="restarted", label="session-restart")
    session.take_session_events = lambda: [event]  # type: ignore[method-assign]
    judge = MockProvider(responses={"judge": [
        Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1")]})
    result, _ = getattr(pipe, which)(_case(), session, judge, "run_1", store)
    assert result.evidence[0].label == "session-restart"

"""AT-888, real browser: back-to-back cases on ONE shared record_video session.

Local pages only, no credentials. Chromium-gated like every browser test here (skips when the
binary is missing). The headed variant is the original reproduction (a headed persistent
Chromium exits when its last page closes; headless does not) and runs only when
`AUTOTESTER_HEADED_TESTS=1`, because it opens a visible window.
"""

from __future__ import annotations

import contextlib
import functools
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.evidence import MASK_CSS
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project


@functools.cache
def _skip_if_no_chromium() -> None:  # cached: one probe launch per process, not per test
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


@pytest.fixture
def shared_session(tmp_path: Path, serve_dir: Callable[[Path], str], request):
    _skip_if_no_chromium()
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html><body><input id=u><button>x</button></body></html>")
    base = serve_dir(site)
    project = Project(slug="at888", name="t", base_url=base, allowed_domains=["127.0.0.1"],
                      headed=bool(getattr(request, "param", False)))
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    session = BrowserSession(project, secrets, tmp_path / "runs" / "r1",
                             ProjectPaths("at888", tmp_path), record_video=True).start()
    yield session, base, tmp_path / "runs" / "r1"
    with contextlib.suppress(Exception):  # a deliberately killed browser may raise on close
        session.close()


def _run_case(session: BrowserSession, base: str, case_id: str, *, fail: bool = False,
              kill_browser: bool = False) -> str | None:
    session.begin_case_video(case_id)
    try:
        session.goto(f"{base}/index.html")
        masked = session.page.evaluate("css => [...document.querySelectorAll('style')]"
                                       ".some(s => s.textContent === css)", MASK_CSS)
        assert masked, f"{case_id}: mask init script not on the case page"
        if fail:
            with pytest.raises(Exception, match="Timeout"):
                session.page.click("#absent", timeout=400)
        if kill_browser:
            session._context.close()  # the browser is gone mid-case
    except BaseException:
        session.end_case_video()
        raise
    return session.end_case_video()


@pytest.mark.parametrize("fail", [False, True], ids=["first-passes", "first-fails"])
def test_second_and_third_case_run_on_a_live_page_whatever_the_first_did(
    shared_session, fail: bool,
) -> None:
    session, base, run_dir = shared_session
    videos = [_run_case(session, base, cid, fail=(fail and cid == "case-1"))
              for cid in ("case-1", "case-2", "case-3")]
    assert all(v and (run_dir / v).stat().st_size > 0 for v in videos), videos
    assert any(not p.is_closed() for p in session._context.pages)  # a page outlives every case
    assert session.take_session_events() == []  # nothing died, so nothing restarted


def test_a_browser_that_died_mid_case_is_restarted_once_visibly_and_the_next_case_runs(
    shared_session,
) -> None:
    session, base, run_dir = shared_session
    _run_case(session, base, "case-1", kill_browser=True)
    video2 = _run_case(session, base, "case-2")  # asserts the mask script on the restarted page
    events = session.take_session_events()
    assert [e.label for e in events] == ["session-restart"]
    assert video2 and (run_dir / video2).stat().st_size > 0
    _run_case(session, base, "case-3")
    assert session.take_session_events() == []  # restarted once, not per case


@pytest.mark.skipif(os.environ.get("AUTOTESTER_HEADED_TESTS") != "1",
                    reason="opens a visible window; set AUTOTESTER_HEADED_TESTS=1")
@pytest.mark.parametrize("shared_session", [True], indirect=True)
def test_headed_original_reproduction_second_case_no_longer_dies(shared_session) -> None:
    session, base, _ = shared_session
    for cid in ("case-1", "case-2", "case-3"):
        _run_case(session, base, cid, fail=(cid == "case-1"))
    assert session.take_session_events() == []

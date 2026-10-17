"""AT-734: a LOST failure video is a recorded marker, never silence, and never costs the case
its real `RawResult`. Fake-context unit tests (no browser); `end_case_video` runs in the
pipeline's `finally`, so anything it raises replaces the case's outcome (AT-573 class).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_run_case_pipeline import _case, _project

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.browser.video import _ignore_close_errors
from autotester.core.paths import ProjectPaths
from autotester.schema.enums import Outcome
from autotester.schema.run import RawResult
from autotester.stages.run_case_pipeline import observe_case
from autotester.store.project_store import ProjectStore


class FakeVideo:
    def __init__(self, path: Path | None, error: Exception | None = None) -> None:
        self._path, self._error = path, error

    def path(self) -> str:
        if self._error is not None:
            raise self._error
        return str(self._path)


class FakePage:
    def __init__(self, video: FakeVideo | None = None) -> None:
        self.video = video

    def add_init_script(self, script: str) -> None:
        pass

    def close(self) -> None:
        pass


class FakeContext:
    def __init__(self, video: FakeVideo | None) -> None:
        self.video = video

    def new_page(self) -> FakePage:
        return FakePage(self.video)

    def add_init_script(self, script: str) -> None:
        pass


def _session(tmp_path: Path, video: FakeVideo | None) -> BrowserSession:
    paths = ProjectPaths("demo", tmp_path)
    secrets = SecretStore.load(_project(), paths.env_file, strict=False)
    s = BrowserSession(_project(), secrets, tmp_path / "run", paths, record_video=True)
    s._context, s._page = FakeContext(video), FakePage(video)
    s._video_case_id = "case-1"
    s.state.run_dir.mkdir(parents=True, exist_ok=True)
    return s


def _labels(session: BrowserSession) -> list[str | None]:
    return [e.label for e in session.take_session_events()]


def test_a_move_that_raises_does_not_escape_end_case_video_and_marks_the_video_lost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "scratch.webm"
    raw.write_bytes(b"webm")
    session = _session(tmp_path, FakeVideo(raw))

    def deny(self: Path, target: object) -> Path:
        raise PermissionError("[WinError 5] Access is denied")

    monkeypatch.setattr(Path, "replace", deny)
    assert session.end_case_video() is None  # no exception, no half-moved path
    events = session.take_session_events()
    assert [e.label for e in events] == ["video-lost"]
    assert "PermissionError" in events[0].path and "case-1" in events[0].path


def test_a_video_path_that_cannot_be_read_is_marked_lost_not_video_off(tmp_path: Path) -> None:
    session = _session(tmp_path, FakeVideo(None, RuntimeError("Target closed")))
    assert session.end_case_video() is None
    events = session.take_session_events()
    assert [e.label for e in events] == ["video-lost"]
    assert "RuntimeError" in events[0].path


def test_a_session_without_recording_leaves_no_lost_marker(tmp_path: Path) -> None:
    session = _session(tmp_path, FakeVideo(None))
    session.record_video = False
    assert session.end_case_video() is None
    assert _labels(session) == []


def test_a_good_move_returns_the_path_and_marks_nothing(tmp_path: Path) -> None:
    raw = tmp_path / "scratch.webm"
    raw.write_bytes(b"webm")
    session = _session(tmp_path, FakeVideo(raw))
    assert session.end_case_video() == "case-1.webm"
    assert _labels(session) == []


def test_the_real_rawresult_survives_a_lost_video_and_carries_the_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The issue's fixture: the move raises inside the pipeline's `finally`."""
    raw = tmp_path / "scratch.webm"
    raw.write_bytes(b"webm")
    session = _session(tmp_path, FakeVideo(raw))
    session._video_case_id = None  # begin_case_video below sets it
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    real = RawResult(case_id="c1", outcome=Outcome.ASSERTION_FAILED, error="the real failure")

    def deny(self: Path, target: object) -> Path:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "replace", deny)
    scripted, video_rel = observe_case(_case(), session, store, execute=lambda c, s: real)
    assert video_rel is None
    assert scripted.result.outcome is Outcome.ASSERTION_FAILED
    assert scripted.result.error == "the real failure"
    assert "video-lost" in [e.label for e in scripted.result.evidence]


def test_close_guard_swallows_exceptions_but_not_interrupts() -> None:
    with _ignore_close_errors():
        raise RuntimeError("already closed")
    for fatal in (KeyboardInterrupt, SystemExit):
        with pytest.raises(fatal), _ignore_close_errors():
            raise fatal()

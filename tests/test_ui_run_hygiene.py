"""AT-733/AT-734/AT-735: run hygiene -- verified profile wipe, guarded prune,
no silent video swallowing."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from autotester.browser import video as video_mod
from autotester.browser.video import VideoMixin, _ignore_close_errors
from autotester.stages import video_retention
from autotester.ui import run_execution


def test_wipe_removes_a_read_only_profile(tmp_path: Path) -> None:
    profile = tmp_path / "p"
    (profile / "sub").mkdir(parents=True)
    f = profile / "sub" / "Cookies"
    f.write_text("x")
    os.chmod(f, stat.S_IREAD)
    run_execution._wipe_entry_profile(profile)
    assert not profile.exists()


def test_wipe_still_fails_closed_when_profile_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = tmp_path / "p"
    profile.mkdir()
    monkeypatch.setattr(run_execution.shutil, "rmtree", lambda *a, **k: None)
    monkeypatch.setattr(run_execution, "_WIPE_PAUSE_S", 0)
    with pytest.raises(OSError, match="still present"):
        run_execution._wipe_entry_profile(profile)


def test_wipe_retries_a_transient_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = tmp_path / "p"
    profile.mkdir()
    real, calls = run_execution.shutil.rmtree, []

    def flaky(path):
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError("locked")
        real(path)

    monkeypatch.setattr(run_execution.shutil, "rmtree", flaky)
    monkeypatch.setattr(run_execution, "_WIPE_PAUSE_S", 0)
    run_execution._wipe_entry_profile(profile)
    assert len(calls) == 2 and not profile.exists()


def test_prune_failure_does_not_propagate(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    def boom(*_a, **_k):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(video_retention, "prune_old_videos", boom)
    assert video_retention.prune_old_videos_safely(object()) == []  # type: ignore[arg-type]
    assert "prune failed" in caplog.text


def test_launcher_uses_the_guarded_prune() -> None:
    from autotester.stages import run_launcher
    assert run_launcher.prune_old_videos_safely is video_retention.prune_old_videos_safely


class _Page:
    def __init__(self, video) -> None:
        self.video = video

    def close(self) -> None:
        pass


def _session(tmp_path: Path, video) -> SimpleNamespace:
    s = SimpleNamespace(record_video=True, _video_case_id="c1", _page=_Page(video),
                        state=SimpleNamespace(run_dir=tmp_path / "run", evidence_prefix=""),
                        _context=SimpleNamespace(new_page=lambda: _Page(None)),
                        _scrubbed=lambda t: t, video_lost=None)
    s._lose_video = lambda cid, reason: VideoMixin._lose_video(s, cid, reason)
    return s


def test_video_path_failure_is_logged_and_marked_lost(tmp_path: Path, caplog) -> None:
    class V:
        def path(self):
            raise OSError("gone")

    s = _session(tmp_path, V())
    assert VideoMixin.end_case_video(s) is None
    assert s.video_lost and "gone" in s.video_lost
    assert "video lost" in caplog.text


def test_video_move_failure_does_not_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "tmp.webm"
    src.write_text("v")

    class V:
        def path(self):
            return str(src)

    s = _session(tmp_path, V())
    monkeypatch.setattr(video_mod.Path, "replace",
                        lambda *_a, **_k: (_ for _ in ()).throw(PermissionError("locked")))
    assert VideoMixin.end_case_video(s) is None  # the caller's RawResult survives
    assert "move failed" in s.video_lost


def test_video_off_is_not_lost(tmp_path: Path) -> None:
    s = _session(tmp_path, None)
    assert VideoMixin.end_case_video(s) is None
    assert s.video_lost is None


def test_ignore_close_errors_does_not_swallow_interrupts() -> None:
    with _ignore_close_errors():
        raise RuntimeError("closed")
    with pytest.raises(KeyboardInterrupt), _ignore_close_errors():
        raise KeyboardInterrupt

"""F1 (T-197 fix cycle 1): no video derivative or frame outlives the step that needs it.

Contract: qa/contracts/team-video-review.md TV10 ("never beside the source video, never in the
repo") and TV7.3. Every test asserts on the DIRECTORY LISTING under `projects/<slug>/reviews/`
after a real `run_review` with real ffmpeg, not on a mock call. Skipped whole without ffmpeg.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from video_review_fakes import RecordingProvider, item, make_run, reply_of

import autotester.media.redacted as redacted_mod
import autotester.stages.video_review as stage
from autotester.core.paths import ProjectPaths
from autotester.media.frames import frame_name
from autotester.media.probe import ffmpeg_available
from autotester.media.redacted import RedactedFrames, RedactionError, mean_luma
from autotester.providers.base import ProviderError
from autotester.schema.video_review import RedactionWindow
from autotester.stages.video_review import ReviewRefused, run_review

pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")

WIN = RedactionWindow(start_s=60.0, end_s=70.0)
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def white_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("clean") / "source.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=64x48:r=1:d=300",
                    "-c:v", "libx264", "-preset", "veryfast", str(out)],
                   check=True, capture_output=True, timeout=120)
    return out


def entries(paths: ProjectPaths) -> list[str]:
    """Everything (files AND directories) under the project's reviews/ dir, sorted."""
    root = paths.dir / "reviews"
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) if root.exists() else []


class SnapshotProvider(RecordingProvider):
    """Lists reviews/ at every call (what is on disk WHILE the model is being asked) and can
    raise KeyboardInterrupt on its Nth call."""

    def __init__(self, replies, paths: ProjectPaths, *, interrupt_on: int = 0) -> None:
        super().__init__(replies)
        self.proj, self.interrupt_on, self.during = paths, interrupt_on, []

    def judge(self, prompt, schema, images=None, **kw):
        self.during.append(entries(self.proj))
        if self.interrupt_on and self.calls + 1 >= self.interrupt_on:
            raise KeyboardInterrupt
        return super().judge(prompt, schema, images, **kw)


def go(tmp_path: Path, video: Path, make_provider, **kw):
    _, source, paths = make_run(tmp_path)
    provider = make_provider(paths)
    kw.setdefault("pointer_text", "0:00-3:00")
    kw.setdefault("windows", [WIN])
    review = run_review(paths, source, video, provider, None, gate=lambda: None, secrets={}, **kw)
    return paths, provider, review


def replies(n: int = 20):
    return [reply_of([item(time_s=0.5)])] * n


def test_a_successful_redacted_run_leaves_only_the_stored_review(white_video, tmp_path):
    paths, provider, r = go(tmp_path, white_video, lambda p: SnapshotProvider(replies(), p))
    assert r.status == "ok" and provider.calls >= 3
    assert entries(paths) == [f"{r.id}.json"]
    source_bytes = white_video.read_bytes()
    for listing in provider.during:                       # while the model was being called
        assert f"{r.id}/redacted.mp4" in listing
        assert all(not e.endswith((".mp4", ".mov", ".mkv", ".webm")) or e.endswith(
            "redacted.mp4") for e in listing)
    for f in (paths.dir / "reviews").rglob("*"):
        assert not f.is_file() or f.read_bytes() != source_bytes


def test_a_run_with_no_windows_copies_no_video_and_leaves_no_frames(white_video, tmp_path):
    paths, provider, r = go(tmp_path, white_video, lambda p: SnapshotProvider(replies(), p),
                            windows=[])
    assert r.status == "ok"
    assert entries(paths) == [f"{r.id}.json"]
    assert provider.during and not any(e.endswith(".mp4") for ls in provider.during for e in ls)


def test_a_failed_blackout_check_leaves_nothing_behind(white_video, tmp_path, monkeypatch):
    """The blackout is a no-op (plain copy): the unredacted copy must not stay on disk."""
    monkeypatch.setattr(redacted_mod, "redact_video",
                        lambda video, _w, out: (out.parent.mkdir(parents=True, exist_ok=True),
                                                shutil.copyfile(video, out), out)[2])
    p = RecordingProvider(replies())
    _, source, paths = make_run(tmp_path)
    with pytest.raises(ReviewRefused, match="redaction"):
        run_review(paths, source, white_video, p, None, gate=lambda: None, secrets={},
                   pointer_text="0:00-3:00", windows=[WIN])
    assert p.calls == 0 and entries(paths) == []


def test_ffmpeg_dying_midway_leaves_nothing_behind(white_video, tmp_path, monkeypatch):
    real, seen = redacted_mod.extract_frame, []

    def flaky(video, t, out):
        seen.append(t)
        if len(seen) > 8:                       # past the 3 blackout samples, mid frame-cutting
            raise OSError("ffmpeg vanished")
        return real(video, t, out)

    monkeypatch.setattr(redacted_mod, "extract_frame", flaky)
    _, source, paths = make_run(tmp_path)
    with pytest.raises(OSError, match="vanished"):
        run_review(paths, source, white_video, RecordingProvider(replies()), None,
                   gate=lambda: None, secrets={}, pointer_text="0:00-3:00", windows=[WIN])
    assert entries(paths) == []


def test_frames_that_cannot_be_cut_leave_only_the_stored_review(white_video, tmp_path,
                                                                monkeypatch):
    real, seen = redacted_mod.extract_frame, []

    def failing(video, t, out):
        seen.append(t)
        return real(video, t, out) if len(seen) <= 3 else False

    monkeypatch.setattr(redacted_mod, "extract_frame", failing)
    paths, _, r = go(tmp_path, white_video, lambda p: RecordingProvider(replies()))
    assert entries(paths) in ([], [f"{r.id}.json"])


def test_a_provider_error_midway_leaves_only_the_stored_review(white_video, tmp_path):
    paths, provider, r = go(tmp_path, white_video, lambda p: RecordingProvider(
        [reply_of([item(time_s=0.5)]), ProviderError("boom"), *replies()]))
    assert provider.calls == 2 and r.status != "ok"
    assert entries(paths) == [f"{r.id}.json"]


def test_a_spend_cap_stop_midway_leaves_only_the_stored_review(white_video, tmp_path):
    paths, provider, r = go(tmp_path, white_video, lambda p: RecordingProvider(replies()),
                            max_cost_usd=0.5, cost_of=lambda p: p.calls * 0.3)
    assert r.status == "partial" and provider.calls == 2
    assert entries(paths) == [f"{r.id}.json"]


def test_ctrl_c_midway_leaves_nothing_behind(white_video, tmp_path):
    _, source, paths = make_run(tmp_path)
    p = SnapshotProvider(replies(), paths, interrupt_on=2)
    with pytest.raises(KeyboardInterrupt):
        run_review(paths, source, white_video, p, None, gate=lambda: None, secrets={},
                   pointer_text="0:00-3:00", windows=[WIN])
    assert p.calls == 1 and any(f.endswith("redacted.mp4") for f in p.during[-1])
    assert entries(paths) == []


def test_refresh_and_crash_leftovers_do_not_pile_up(white_video, tmp_path):
    paths, _, first = go(tmp_path, white_video, lambda p: RecordingProvider(replies()))
    work = paths.review_work_dir(first.id)
    (work / "frames").mkdir(parents=True)
    (work / "redacted.mp4").write_bytes(b"stale derivative")
    (work / "frames" / "00000001.png").write_bytes(b"stale frame")
    _, again, second = go(tmp_path, white_video, lambda p: RecordingProvider(replies()),
                          refresh=True)
    assert second.id == first.id and again.calls >= 1
    assert entries(paths) == [f"{first.id}.json"]
    paths.review_path(first.id).unlink()                        # a crash: no stored review
    (work / "frames").mkdir(parents=True)
    (work / "frames" / "00000002.png").write_bytes(b"left by a killed run")
    go(tmp_path, white_video, lambda p: RecordingProvider(replies()))
    assert entries(paths) == [f"{first.id}.json"]


def test_a_failed_constructor_removes_its_own_derivative_and_stills(white_video, tmp_path,
                                                                    monkeypatch):
    work = tmp_path / "work"
    monkeypatch.setattr(redacted_mod, "mean_luma", lambda _p: 255.0)   # blackout "fails"
    with pytest.raises(RedactionError):
        RedactedFrames(white_video, work, [WIN])
    assert [p for p in work.rglob("*") if p.is_file()] == []

    def interrupted(_png):
        raise KeyboardInterrupt

    monkeypatch.setattr(redacted_mod, "mean_luma", interrupted)
    with pytest.raises(KeyboardInterrupt):
        RedactedFrames(white_video, work, [WIN])
    assert [p for p in work.rglob("*") if p.is_file()] == []


class LumaProvider(RecordingProvider):
    """Measures, at call time, the brightness of every still it is handed (what it RECEIVED)."""

    def __init__(self, replies) -> None:
        super().__init__(replies)
        self.seen: list[tuple[float, float | None]] = []

    def judge(self, prompt, schema, images=None, **kw):
        for p in images or []:
            t = int(Path(p).stem) / 1000
            if 55 <= t <= 75:
                self.seen.append((t, mean_luma(Path(p))))
        return super().judge(prompt, schema, images, **kw)


def test_the_provider_receives_black_stills_even_if_a_window_frame_were_asked_for(
        white_video, tmp_path, monkeypatch):
    """Defence in depth (TV7.3): force the planner's own window filter off, so frames INSIDE the
    window are requested; what the provider is handed for them must be black, which only holds
    when they were cut from the redacted copy and not from the original."""
    monkeypatch.setattr(stage, "in_any", lambda _t, _w: False)
    _, provider, r = go(tmp_path, white_video, lambda p: LumaProvider(replies()))
    inside = [(t, luma) for t, luma in provider.seen if WIN.start_s <= t <= WIN.end_s]
    outside = [(t, luma) for t, luma in provider.seen if not WIN.start_s <= t <= WIN.end_s]
    assert inside and outside and r.status == "ok"
    assert all(luma is not None and luma < 10 for _, luma in inside)
    assert all(luma is not None and luma > 200 for _, luma in outside)


@pytest.mark.parametrize("rel", [
    "redacted.mp4", f"frames/{frame_name(61.0)}", "verify_0_1.png", "frames/stray.jpg", "x.mov"])
def test_every_work_dir_artifact_is_gitignored_in_the_real_repo(rel):
    paths = ProjectPaths("demo", REPO)
    target = paths.review_work_dir("rv_abc123") / rel
    _assert_ignored(target)


@pytest.mark.parametrize("ext", ["json", "md", "html"])
def test_the_stored_review_and_its_exports_are_gitignored_in_the_real_repo(ext):
    stored = ProjectPaths("demo", REPO).review_path("rv_abc123")
    _assert_ignored(stored.with_suffix(f".{ext}"))


def _assert_ignored(path: Path) -> None:
    done = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q",
                           path.relative_to(REPO).as_posix()], capture_output=True, timeout=30)
    assert done.returncode == 0, f"{path.relative_to(REPO)} is not ignored by .gitignore"

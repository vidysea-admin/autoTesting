"""TV7 (pure parts, real ffmpeg): the redacted copy really hides the window, and only it is cut.

Contract: qa/contracts/team-video-review.md TV7 (3). Skipped whole when ffmpeg is absent, like
`test_media_real_ffmpeg.py`. R65: paths use pathlib and a drive-letter tmp dir.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from autotester.media.probe import ffmpeg_available
from autotester.media.redacted import (
    RedactedFrames,
    RedactionError,
    mean_luma,
    redact_video,
    verify_blackout,
)
from autotester.schema.video_review import RedactionWindow

pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")

WIN = RedactionWindow(start_s=1.0, end_s=2.0)


@pytest.fixture(scope="module")
def bright_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """4 s, 64x64, 1 fps pure white video with a 440 Hz tone: a reviewer's recording of a
    bright screen with narration, so blackout and mute are both measurable."""
    out = tmp_path_factory.mktemp("rv") / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=64x64:r=5:d=4",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac",
         "-shortest", str(out)],
        check=True, capture_output=True, timeout=60)
    return out


def _frame(video: Path, t: float, png: Path) -> Path:
    from autotester.media.frames import extract_frame

    assert extract_frame(video, t, png)
    return png


def test_frames_inside_the_window_change_and_outside_do_not(bright_video, tmp_path):
    """A reviewer blanks 1-2 s: the copy is black there, still white elsewhere."""
    copy = redact_video(bright_video, [WIN], tmp_path / "copy.mp4")
    inside = mean_luma(_frame(copy, 1.5, tmp_path / "in.png"))
    before = mean_luma(_frame(copy, 0.5, tmp_path / "b.png"))
    after = mean_luma(_frame(copy, 3.0, tmp_path / "a.png"))
    original = mean_luma(_frame(bright_video, 1.5, tmp_path / "o.png"))
    assert original is not None and original > 200            # the source really was bright
    assert inside is not None and inside < 10                 # frames CHANGED inside the window
    assert before is not None and before > 200 and after is not None and after > 200


def test_a_no_op_blackout_is_a_failure(bright_video, tmp_path):
    """A copy that did not actually hide the window (a plain copy of the source) is refused."""
    noop = tmp_path / "noop.mp4"
    noop.write_bytes(bright_video.read_bytes())
    with pytest.raises(RedactionError):
        verify_blackout(noop, [WIN], tmp_path)
    verify_blackout(redact_video(bright_video, [WIN], tmp_path / "ok.mp4"), [WIN], tmp_path)


def test_audio_inside_the_window_is_muted(bright_video, tmp_path):
    """The tone is audible outside the window and silent inside it (mute, not just blackout)."""
    copy = redact_video(bright_video, [WIN], tmp_path / "copy.mp4")

    def mean_volume(video: Path, start: float, dur: float) -> float:
        err = subprocess.run(
            ["ffmpeg", "-ss", str(start), "-t", str(dur), "-i", str(video), "-vn",
             "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60).stderr
        m = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", err)
        assert m, err[-300:]
        return float("-inf") if m.group(1) == "-inf" else float(m.group(1))

    assert mean_volume(copy, 1.2, 0.6) < -60
    assert mean_volume(copy, 2.6, 1.0) > -40


def test_frames_handed_out_come_from_the_copy_and_sit_under_the_work_dir(bright_video, tmp_path):
    """The Provider is handed PNG paths under the review's work dir, cut from the redacted copy."""
    frames = RedactedFrames(bright_video, tmp_path / "work", [WIN])
    png = frames.frame(0.5)
    assert png is not None and (tmp_path / "work") in png.parents
    assert bright_video not in png.parents and png != bright_video
    assert frames.origin == tmp_path / "work" / "redacted.mp4"
    hidden = frames.frame(1.5)       # callers never ask for it (TV7); if they did it is black
    assert hidden is not None and mean_luma(hidden) < 10


def test_no_windows_means_frames_from_the_source_and_no_copy(bright_video, tmp_path):
    frames = RedactedFrames(bright_video, tmp_path / "work", [])
    assert frames.origin == bright_video and not (tmp_path / "work" / "redacted.mp4").exists()
    assert frames.frame(0.5) is not None


def test_run_review_end_to_end_hands_the_provider_only_redacted_frames(bright_video, tmp_path):
    """Real ffmpeg through `run_review`: window 1-2 s is skipped, every frame sent is a PNG
    under the review work dir, none is the source, and the frames are cut from the copy."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from video_review_fakes import RecordingProvider, item, make_run, reply_of

    from autotester.stages.video_review import run_review

    _, source, paths = make_run(tmp_path)
    p = RecordingProvider([reply_of([item(time_s=0.5, source_id=source.id)])] * 5,
                          forbidden=[bright_video])
    r = run_review(paths, source, bright_video, p, None, gate=lambda: None,
                   pointer_text="0:00-0:03", windows=[WIN])
    assert r.status == "ok" and p.calls >= 1
    assert p.frame_times and not any(1.0 <= t <= 2.0 for t in p.frame_times)
    work = paths.review_work_dir(r.id)
    assert all(work in x.parents for x in p.paths)
    assert (work / "redacted.mp4").is_file()
    assert any(s <= 1.0 and e >= 2.0 for s, e in r.not_reviewed)

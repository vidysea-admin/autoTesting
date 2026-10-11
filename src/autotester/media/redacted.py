"""The redacted derivative of a recording, and the frames cut from it (TV7).

Redaction windows (`[start_s, end_s]`) are blanked in the video and muted in the audio of a
COPY. Every frame a model is shown is cut from that copy, never from the original, and the copy
is checked to really be black inside each window: a blackout that is a no-op is a failure
(`RedactionError`), not a quiet success.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Protocol

from autotester.media.frames import extract_frame, frame_name, is_complete_png
from autotester.media.probe import probe
from autotester.schema.video_review import RedactionWindow

BLACK_LUMA = 10
"""Mean luma (0-255) at or under which a frame counts as blacked out."""
ENCODE_TIMEOUT_S = 900.0
PROBE_TIMEOUT_S = 60.0


class RedactionError(RuntimeError):
    """The derivative could not be made, or did not hide what the window says it hides."""


class FrameSource(Protocol):
    """Where a review's frames come from: a path to a still at second `t_s`, or None."""

    def frame(self, t_s: float) -> Path | None: ...


def _enable(windows: list[RedactionWindow]) -> str:
    return "+".join(f"between(t,{w.start_s:g},{w.end_s:g})" for w in windows)


def has_audio(video: Path) -> bool:
    try:
        raw = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_type", "-print_format", "json", str(video)],
            check=True, capture_output=True, text=True, timeout=PROBE_TIMEOUT_S).stdout
        return bool(json.loads(raw).get("streams"))
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


def redact_video(video: Path, windows: list[RedactionWindow], out: Path) -> Path:
    """Write the derivative of `video` with every window blacked out and muted."""
    out.parent.mkdir(parents=True, exist_ok=True)
    en = _enable(windows)
    cmd = ["ffmpeg", "-y", "-i", str(video), "-vf",
           f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='{en}'"]
    if has_audio(video):
        cmd += ["-af", f"volume=enable='{en}':volume=0"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=ENCODE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        out.unlink(missing_ok=True)
        raise RedactionError(f"could not write the redacted copy: {type(exc).__name__}") from exc
    return out


def mean_luma(png: Path) -> float | None:
    """Mean brightness of a still (0 black .. 255 white), or None when unreadable."""
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(png), "-vf", "scale=1:1,format=gray",
             "-f", "rawvideo", "-"],
            check=True, capture_output=True, timeout=PROBE_TIMEOUT_S).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return float(raw[0]) if raw else None


def _samples(w: RedactionWindow, duration: float) -> list[float]:
    """Start, middle and end of the part of `w` inside the recording (inset 0.1 s off the edges
    so a keyframe boundary cannot read as a gap). Empty when the window is past the end."""
    if w.start_s >= duration:
        return []
    lo, hi = w.start_s, min(w.end_s, duration)
    inset = min(0.1, (hi - lo) / 2)
    return [lo + inset, (lo + hi) / 2, hi - inset]


def verify_blackout(derivative: Path, windows: list[RedactionWindow], scratch: Path) -> None:
    """Raise `RedactionError` unless the copy is black at the start, middle and end of every
    window. A frame that cannot be read is a refusal, never a skip: only a window wholly past
    the end of the recording is skipped, because there is nothing there to hide (F5, TV7.3)."""
    duration = probe(derivative)[0]
    if duration <= 0:
        raise RedactionError("could not read the redacted copy to check the blackout")
    for i, w in enumerate(windows):
        for j, t in enumerate(_samples(w, duration)):
            still = scratch / f"verify_{i}_{j}.png"
            if not extract_frame(derivative, t, still):
                raise RedactionError(
                    f"could not read the copy at {t:g}s to check redaction window "
                    f"{w.start_s:g}-{w.end_s:g}s")
            luma = mean_luma(still)
            still.unlink(missing_ok=True)
            if luma is None or luma > BLACK_LUMA:
                raise RedactionError(
                    f"redaction window {w.start_s:g}-{w.end_s:g}s is not blacked out in the "
                    f"copy (at {t:g}s)")


class RedactedFrames:
    """Frames for one review, cut from the redacted copy (or the source when nothing is redacted).

    `windows` empty -> the source itself is the frame origin; the model still only ever sees
    PNG files under `work_dir`, never a video path."""

    def __init__(self, video: Path, work_dir: Path, windows: list[RedactionWindow]) -> None:
        self.work_dir = work_dir
        self.windows = windows
        self.origin = video
        if windows:
            self.origin = redact_video(video, windows, work_dir / "redacted.mp4")
            verify_blackout(self.origin, windows, work_dir)

    def frame(self, t_s: float) -> Path | None:
        out = self.work_dir / "frames" / frame_name(t_s)
        if is_complete_png(out) or extract_frame(self.origin, t_s, out):
            return out
        return None

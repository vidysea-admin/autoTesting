"""Shared fakes for the video-review tests: a recording provider, fake frames, a run helper.

No model call is ever real. `RecordingProvider` records every frame time and path it is handed
and refuses any path under a forbidden prefix (the unredacted-original rule, TV7).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autotester.core.paths import ProjectPaths
from autotester.media.frames import frame_name
from autotester.providers.base import Provider, ProviderError
from autotester.schema.enums import SourceKind
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.project import Source
from autotester.schema.video_review import ReplyItem, ReviewReply, VideoReview
from autotester.stages.video_review import run_review

SRC = "src_test"
DURATION = 600.0


class RecordingProvider(Provider):
    id = "fake"

    def __init__(self, replies: list[Any] | None = None, *, forbidden: list[Path] | None = None,
                 log: list[str] | None = None) -> None:
        super().__init__()
        self.replies = list(replies or [])
        self.forbidden = forbidden or []
        self.log = log if log is not None else []
        self.calls = 0
        self.prompts: list[str] = []
        self.paths: list[Path] = []
        self.frame_times: list[float] = []

    def available(self) -> bool:
        return True

    def judge(self, prompt: str, schema: type, images: list[Path] | None = None, *,
              prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        self.log.append("judge")
        for p in images or []:
            assert not any(f in Path(p).parents or Path(p) == f for f in self.forbidden), p
        self.calls += 1
        self.prompts.append(prompt)
        self.paths += [Path(p) for p in images or []]
        self.frame_times += [int(Path(p).stem) / 1000 for p in images or []]
        self.record("judge", 10, 10)
        reply = self.replies.pop(0) if self.replies else reply_of([])
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeFrames:
    """A FrameSource that writes a tiny file per requested second under `work_dir/frames`."""

    log: list[str] | None = None

    def __init__(self, video: Path, work_dir: Path, windows: list[Any]) -> None:
        self.work_dir, self.windows = work_dir, windows
        if FakeFrames.log is not None:
            FakeFrames.log.append("redact")

    def frame(self, t_s: float) -> Path | None:
        out = self.work_dir / "frames" / frame_name(t_s)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake-png")
        return out


def item(**over: Any) -> ReplyItem:
    base = {"time_s": 10, "screen": "Login", "seen": "Button looks disabled",
            "suggestion": "Check the state", "severity": "S2", "source_id": SRC,
            "origin": "visual"}
    return ReplyItem(**{**base, **over})


def reply_of(items: list[ReplyItem], summary: str = "A user logs in.") -> ReviewReply:
    return ReviewReply(summary=summary, items=items)


def transcript(*segs: tuple[float, float, str], engine: str = "sidecar") -> Transcript:
    return Transcript(source_id=SRC, engine=engine,
                      segments=[TranscriptSegment(start=a, end=b, text=t) for a, b, t in segs])


def make_run(tmp_path: Path) -> tuple[Path, Source, ProjectPaths]:
    """(video, source, paths) for a fake recording and a fresh project dir."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    video = tmp_path / "rec.mp4"
    video.write_bytes(b"not-a-real-video-but-nonempty")
    source = Source(id=SRC, project="p", kind=SourceKind.VIDEO, path="rec.mp4")
    return video, source, ProjectPaths("p", tmp_path / "root")


def run(tmp_path: Path, provider: Provider, tx: Transcript | None = None, **kw: Any
        ) -> VideoReview:
    video, source, paths = make_run(tmp_path)
    kw.setdefault("gate", lambda: None)
    kw.setdefault("secrets", {})
    kw.setdefault("probe_fn", lambda _p: (DURATION, 640, 360))
    kw.setdefault("frames_fn", FakeFrames)
    return run_review(paths, source, video, provider, tx, **kw)


__all__ = ["DURATION", "SRC", "FakeFrames", "ProviderError", "RecordingProvider", "item",
           "make_run", "reply_of", "run", "transcript"]

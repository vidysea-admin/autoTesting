"""Shared by the TA4/5/10/12/13/14 tests: upload through the app's own doors, then run the
review stage on the registered source with the REAL approval gate and the recording provider.

The model Provider, the frame source and the media probe are the named seams (no ffmpeg, no
network); the gate, the approval check and the stage are the repo's own.
"""

from __future__ import annotations

import io
import zipfile
from functools import partial
from pathlib import Path

from rig import HTML, SLUG, World
from run_approval_fixture import grant_live_case_approval
from video_review_fakes import DURATION, FakeFrames
from zip_fixtures import add_member, video

from autotester.cli_video_review import build_gate
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Source
from autotester.stages.video_review import preview_review, run_review

UPLOAD = f"/projects/{SLUG}/sources/upload"


def make_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        add_member(archive, "intro.mp4", video("intro"))
        add_member(archive, "checkout.mp4", video("checkout"))
        add_member(archive, "notes.md", b"# checkout notes\nPay then confirm.\n")
        add_member(archive, "../escape.mp4", video("hostile"))
    return buf.getvalue()


def upload(world: World, who: str, name: str, data: bytes):
    return world.users[who].post(UPLOAD, data={"label": "demo"}, headers=HTML,
                                 files={"recording": (name, data, "application/zip")})


def upload_video(world: World, who: str = "dev", tag: str = "checkout") -> Source:
    """`who` adds one recording through the Add-videos route; returns the registered source."""
    resp = world.users[who].post(
        f"/projects/{SLUG}/sources/upload", data={"label": tag}, headers=HTML,
        files={"recording": (f"{tag}.mp4", video(tag), "video/mp4")})
    assert resp.status_code in (200, 303), resp.text[:300]
    return next(s for s in world.store().list_sources() if s.label == tag)


def grant_review(world: World, *, actions: int = 500) -> None:
    grant_live_case_approval(world.store(), project=SLUG, target=world.provider.id,
                             max_actions=actions, run_kind=ApprovalKind.VIDEO_REVIEW)


def review(world: World, source: Source, pointer_text: str = ""):
    """Run (or be refused by) the review of `source` as the CLI/route would: real gate."""
    store = world.store()
    path = Path(source.path or "")
    path = path if path.is_absolute() else store.paths.dir / path
    assert path.is_file(), path
    probe = lambda _p: (DURATION, 640, 360)   # noqa: E731 - the media probe seam
    plan_fn = partial(preview_review, path, pointer_text, [], provider_label="fake",
                      probe_fn=probe)
    gate = build_gate(store, SLUG, world.provider, plan_fn, lambda: None)
    return run_review(store.paths, source, path, world.provider, None, gate=gate, secrets={},
                      pointer_text=pointer_text, probe_fn=probe, frames_fn=FakeFrames)

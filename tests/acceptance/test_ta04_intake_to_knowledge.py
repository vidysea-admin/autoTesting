"""TA4: intake becomes knowledge from both doors, with no approval step. `dev` uploads a zip (two
videos, one document, one hostile member) and pastes a Drive link served by the fake DriveClient;
every member is accounted for, each source carries uploader, time and origin, the same bytes add
nothing, and `tester` / `pending` are refused. The FlowSpec-DRAFT and "Another possibility" row
is xfail(strict) (T-169): it needs a model-backed video analysis with no offline route."""

from __future__ import annotations

import time

import pytest
from review_support import make_zip, upload
from rig import HTML, SLUG, World
from zip_fixtures import video

UPLOAD = f"/projects/{SLUG}/sources/upload"
DRIVE = f"/projects/{SLUG}/sources/drive"


def test_the_zip_accounts_for_every_member_and_each_source_has_provenance(world: World) -> None:
    resp = upload(world, "dev", "clips.zip", make_zip())
    assert resp.status_code in (200, 303), resp.text[:300]
    sources = world.store().list_sources()
    names = " ".join(str(s.path) for s in sources)
    assert len(sources) >= 2 and "escape" not in names
    for source in sources:
        assert source.uploaded_by == "dev@team.test" and source.uploaded_at is not None
        assert source.origin is not None
    for member in ("intro.mp4", "checkout.mp4", "notes.md", "escape.mp4"):
        assert member in resp.text            # the outcome table names every member


def test_the_same_bytes_added_again_register_nothing_new(world: World) -> None:
    data = make_zip()
    upload(world, "dev", "clips.zip", data)
    first = {s.sha256 for s in world.store().list_sources()}
    upload(world, "dev", "clips.zip", data)
    assert {s.sha256 for s in world.store().list_sources()} == first
    assert len(world.store().list_sources()) == len(first)


def test_the_drive_door_registers_a_source_with_its_origin_and_no_live_call(world: World) -> None:
    world.drive.add("drive-file-1", video("fromdrive"), name="walkthrough.mp4")
    resp = world.users["dev"].post(DRIVE, data={"link": "https://drive.google.com/file/d/"
                                                "drive-file-1/view"}, headers=HTML)
    assert resp.status_code in (200, 303), resp.text[:300]
    deadline = time.time() + 10
    while not world.drive.opened and time.time() < deadline:
        time.sleep(0.1)
    time.sleep(0.5)
    assert world.drive.opened == ["drive-file-1"]
    drive_sources = [s for s in world.store().list_sources()
                     if s.origin is not None and "drive" in str(s.origin).lower()]
    assert len(drive_sources) == 1 and drive_sources[0].uploaded_by == "dev@team.test"
    assert world.egress.blocked == []


@pytest.mark.parametrize("who", ["tester", "pending"])
def test_tester_and_pending_cannot_upload(world: World, who: str) -> None:
    before = world.snapshot()
    resp = upload(world, who, "clips.zip", make_zip())
    assert resp.status_code in (302, 303, 403, 404)
    assert world.store().list_sources() == []
    assert world.snapshot() == before


@pytest.mark.xfail(strict=True, reason=(
    "blocked on T-169 (model-backed video analysis): turning an intake source into "
    "DRAFT flows (TV9) and an 'Another possibility' report item (RC10) needs the "
    "model-backed video analysis (ffmpeg plus a Provider); no offline route exists on "
    "master"))
def test_tv9_the_flowspec_holds_draft_flows_with_source_id_and_no_approval_step(
        world: World) -> None:
    upload(world, "dev", "clips.zip", make_zip())
    source = world.store().list_sources()[0]
    resp = world.users["dev"].post(f"/projects/{SLUG}/sources/{source.id}/analyze", headers=HTML)
    assert resp.status_code in (200, 303)
    spec = world.store().load_flowspec()
    assert spec is not None and any(f.source_id == source.id for f in spec.flows)

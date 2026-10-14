"""TA5: a pointer review of an intake source returns a traced confirm-list. The source arrives
through the Add-videos route (registered by `dev`) and the review is run for `admin`; the model
Provider is the recording fake. With the per-use approval missing the provider makes zero calls.
The live-UI "Run review" button has no route on master, so that row is xfail(strict) (T-169)."""

from __future__ import annotations

import re

import pytest
from review_support import grant_review, review, upload_video
from rig import HTML, SLUG, World
from video_review_fakes import DURATION, item, reply_of

from autotester.stages.video_review import ReviewRefused

POINTERS = "1:00 | checkout total\n3:00-4:00\n~8:00 | the footer"


def test_a_review_of_an_intake_source_is_traced_to_seconds_inside_the_video(world: World) -> None:
    source = upload_video(world, "dev")
    assert source.uploaded_by == "dev@team.test"         # registered by someone other than admin
    found = [item(source_id=source.id, time_s=62, seen="total is wrong"),
             item(source_id=source.id, time_s=200, seen="label cut off")]
    world.provider.replies = [reply_of(found)] * 40
    grant_review(world)
    result = review(world, source, POINTERS)
    assert result.status == "ok" and result.summary
    assert 0 <= len(result.items) <= 5 and result.items
    assert all(0 <= i.time_s <= DURATION for i in result.items)
    assert world.provider.calls > 0
    assert world.provider.paths and all(p.suffix == ".png" or p.exists()
                                        for p in world.provider.paths)
    assert world.egress.blocked == []


def test_with_the_approval_missing_the_provider_is_never_called(world: World) -> None:
    source = upload_video(world, "dev")
    with pytest.raises(ReviewRefused, match=r"video_review|approv"):
        review(world, source, POINTERS)
    assert world.provider.calls == 0


def test_an_approval_too_small_for_the_plan_is_refused_with_zero_calls(world: World) -> None:
    source = upload_video(world, "dev")
    grant_review(world, actions=1)
    with pytest.raises(ReviewRefused):
        review(world, source, POINTERS)
    assert world.provider.calls == 0


def test_a_tester_with_access_sees_the_video_and_has_no_run_review_control(world: World) -> None:
    source = upload_video(world, "dev")
    page = f"/projects/{SLUG}/videos/{source.id}"
    tester = world.users["tester"]
    assert tester.post(page + "/request-access").status_code == 200
    pending = world.users["dev"].get("/access-requests", headers=HTML).text
    rid = re.search(r"/access-requests/(\d+)/approve", pending)
    assert rid, pending[:300]
    assert world.users["dev"].post(f"/access-requests/{rid.group(1)}/approve").status_code == 303
    assert tester.get(page + "/media").status_code == 200
    assert tester.post(page + "/review", data={"pointers": POINTERS}).status_code in (403, 404, 405)
    assert world.provider.calls == 0
    assert "Run review" not in tester.get(page, headers=HTML).text


@pytest.mark.xfail(strict=True, reason=(
    "blocked on T-169 (proposal-review UI): there is no 'Run review' route or screen "
    "on master (the review runs from `autotester ingest review` only; T-201/T-199 added "
    "no such route, and T-206 is tests-only, no src change); the contract row's own "
    "assertions are the four passing tests above"))
def test_admin_runs_the_review_from_the_source_page(world: World) -> None:
    source = upload_video(world, "dev")
    resp = world.users["admin"].post(f"/projects/{SLUG}/videos/{source.id}/review",
                                     data={"pointers": POINTERS})
    assert resp.status_code in (200, 303)

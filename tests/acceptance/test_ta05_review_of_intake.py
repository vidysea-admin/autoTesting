"""TA5: a pointer review of an intake source returns a traced confirm-list. The source arrives
through the Add-videos route (registered by `dev`) and the review is run for `admin`; the model
Provider is the recording fake. With the per-use approval missing the provider makes zero calls.
The live-UI "Run review" button has no route on master, so that row is xfail(strict) (T-169)."""

from __future__ import annotations

import pytest
from review_support import grant_review, review, upload_video
from rig import SLUG, World
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


@pytest.mark.xfail(strict=True, reason=(
    "blocked on T-169 (proposal-review UI): there is no 'Run review' route or screen "
    "on master (the review runs from `autotester ingest review` only); a UI route "
    "belongs to a later unit"))
def test_admin_runs_the_review_from_the_source_page(world: World) -> None:
    source = upload_video(world, "dev")
    resp = world.users["admin"].post(f"/projects/{SLUG}/videos/{source.id}/review",
                                     data={"pointers": POINTERS})
    assert resp.status_code in (200, 303)

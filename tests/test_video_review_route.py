"""TA5 / TV7: the "Run review" button on the video page (POST .../videos/{id}/review).

The route reuses `stages.video_review.run_review` and the CLI's `build_gate`; the model Provider,
the media probe and the frame source are the named seams (no ffmpeg, no network).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from portal_support import SLUG, World, build_world
from run_approval_fixture import grant_live_case_approval
from video_review_fakes import DURATION, FakeFrames, RecordingProvider, item, reply_of

from autotester.schema.enums import ApprovalKind
from autotester.stages.video_review_store import stored_reviews
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_video_review as route

POINTERS = "1:00 | checkout total\n~8:00 | the footer"
HTML = {"accept": "text/html"}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    return build_world(tmp_path, monkeypatch)


@pytest.fixture()
def provider(monkeypatch: pytest.MonkeyPatch) -> RecordingProvider:
    prov = RecordingProvider()
    monkeypatch.setattr(route, "provider_factory", lambda _store: prov)
    monkeypatch.setattr(route, "probe_fn", lambda _p: (DURATION, 640, 360))
    monkeypatch.setattr(route, "frames_fn", FakeFrames)
    return prov


def _grant(world: World, actions: int = 500) -> None:
    grant_live_case_approval(ProjectStore(SLUG, world.root), project=SLUG, target="fake",
                             max_actions=actions, run_kind=ApprovalKind.VIDEO_REVIEW)


def _url(world: World) -> str:
    return world.page() + "/review"


def _fill(prov: RecordingProvider, world: World) -> None:
    prov.replies = [reply_of([item(source_id=world.vid, time_s=62, seen="total is wrong")])] * 40


def test_admin_runs_a_review_and_the_page_shows_it(world: World, provider) -> None:
    _grant(world)
    _fill(provider, world)
    resp = world.users["admin"].post(_url(world), data={"pointers": POINTERS})
    assert resp.status_code == 303 and resp.headers["location"].startswith(world.page())
    assert provider.calls > 0
    assert len(stored_reviews(ProjectStore(SLUG, world.root).paths, world.vid)) == 1
    page = world.users["dev"].get(world.page())
    assert "total is wrong" in page.text and "1:02" in page.text
    assert "Run review" in page.text and "for='review-pointers'" in page.text


def test_with_the_approval_missing_the_provider_is_never_called(world: World, provider) -> None:
    resp = world.users["admin"].post(_url(world), data={"pointers": POINTERS})
    assert resp.status_code == 403 and "approv" in resp.text.lower()
    assert provider.calls == 0


def test_an_approval_too_small_for_the_plan_makes_zero_calls(world: World, provider) -> None:
    _grant(world, actions=1)
    resp = world.users["admin"].post(_url(world), data={"pointers": POINTERS})
    assert resp.status_code == 403 and provider.calls == 0


def test_bad_pointers_are_refused_whole_with_zero_calls(world: World, provider) -> None:
    _grant(world)
    resp = world.users["admin"].post(_url(world), data={"pointers": "12:30-12:00"})
    assert resp.status_code == 400 and "Nothing was sent to a model" in resp.text
    assert provider.calls == 0


def test_a_secret_in_the_pointers_never_reaches_the_provider(
        world: World, provider, monkeypatch: pytest.MonkeyPatch) -> None:
    _grant(world)
    _fill(provider, world)
    class Vault:
        def scrub_values(self) -> dict[str, str]:
            return {"APP_PASSWORD": "hunter2hunter2"}

    monkeypatch.setattr(route.SecretStore, "load", lambda *_a, **_k: Vault())
    world.users["admin"].post(_url(world), data={"pointers": "1:00 | typed hunter2hunter2 in"})
    assert all("hunter2hunter2" not in p for p in provider.prompts)


def test_the_tester_with_the_video_shared_reads_the_review_and_has_no_run_control(
        world: World, provider) -> None:
    _grant(world)
    _fill(provider, world)
    world.users["admin"].post(_url(world), data={"pointers": POINTERS})
    from autotester.stages import video_access as access
    access.set_share(SLUG, world.vid, "tester@team.test", True, "dev@team.test")
    page = world.users["tester"].get(world.page())
    assert page.status_code == 200 and "total is wrong" in page.text
    assert "Run review" not in page.text and "review-pointers" not in page.text
    calls = provider.calls
    assert world.users["tester"].post(_url(world), data={"pointers": ""}).status_code == 403
    assert provider.calls == calls


def test_401_anonymous_and_404_unknown_or_unseen(world: World, provider) -> None:
    from portal_support import anonymous
    assert anonymous().post(_url(world), data={"pointers": ""}).status_code == 401
    admin = world.users["admin"]
    assert admin.post(world.page("nope") + "/review", data={"pointers": ""}).status_code == 404
    assert world.users["tester"].post(_url(world), data={"pointers": ""}).status_code == 404
    assert world.users["nogroup"].post(_url(world), data={"pointers": ""}).status_code in (403, 404)
    assert provider.calls == 0

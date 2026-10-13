"""T-198b TP1 (the bytes are behind the membership check) and TP4 (route-by-route permissions).

Scenario source: a Tester opens the direct URL of a video nobody shared with them and must get
the request-access page, no player and no byte of the file, on the page, a full GET and a Range
GET; revoking the share stops the very next request on a live cookie.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from auth_harness import app_routes, user_id
from portal_support import SENTINEL, SLUG, World, add_video, anonymous, build_world, email

from autotester.auth import accounts, policy
from autotester.auth.access import set_relation
from autotester.schema.auth import CATALOGUE, ProjectRelation, RouteRule
from autotester.stages.video_access import media_path

HTML, JSON = {"accept": "text/html"}, {"accept": "application/json"}
ALLOWED = ("admin", "sub", "dev")
SIGNED_IN_DENIED = ("dev2", "tester", "tester2")


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    return build_world(tmp_path, monkeypatch)


def _media(w: World) -> str:
    return w.page() + "/media"


def test_tp1_members_get_the_player_and_the_bytes(world: World) -> None:
    for name in ALLOWED:
        who = world.users[name]
        page = who.get(world.page(), headers=HTML)
        assert page.status_code == 200 and "<video" in page.text, name
        full = who.get(_media(world))
        assert full.status_code == 200 and full.content.startswith(SENTINEL), name
        part = who.get(_media(world), headers={"Range": "bytes=0-9"})
        assert part.status_code == 206 and part.content == SENTINEL[:10], name


@pytest.mark.parametrize("name", SIGNED_IN_DENIED)
def test_tp1_a_signed_in_non_member_gets_request_access_and_no_bytes(
        world: World, name: str) -> None:
    who = world.users[name]
    page = who.get(world.page(), headers=HTML)
    assert page.status_code == 404 and "Request access" in page.text
    assert "<video" not in page.text and b"SENTINEL" not in page.content
    for headers in ({}, {"Range": "bytes=0-9"}, {"Range": "bytes=0-"}):
        denied = who.get(_media(world), headers=headers)
        assert denied.status_code == 404, (name, headers)
        assert b"SENTINEL" not in denied.content


def test_tp1_a_signed_up_user_in_no_group_reaches_nothing(world: World) -> None:
    who = world.users["nogroup"]
    for path in (world.page(), _media(world)):
        denied = who.get(path, headers=HTML)
        assert denied.status_code == 403 and b"SENTINEL" not in denied.content


def test_tp1_anonymous_is_sent_to_sign_in_and_gets_no_bytes(world: World) -> None:
    anon = anonymous()
    page = anon.get(world.page(), headers=HTML)
    assert page.status_code == 302 and page.headers["location"].startswith("/auth/login?next=/")
    media = anon.get(_media(world), headers={"Range": "bytes=0-9"})
    assert media.status_code == 401 and b"SENTINEL" not in media.content


def _share(world: World, who: str, target: str, change: str = "add") -> int:
    return world.users[who].post(world.page() + "/shares", data={
        "email": email(target), "change": change}).status_code


def test_tp1_a_share_opens_the_video_and_removing_it_stops_the_next_request(
        world: World) -> None:
    tester = world.users["tester"]
    assert tester.get(_media(world)).status_code == 404
    assert _share(world, "dev", "tester") == 303
    assert tester.get(_media(world)).content.startswith(SENTINEL)
    assert tester.get(world.page(), headers=HTML).status_code == 200
    assert _share(world, "dev", "tester", "remove") == 303
    assert tester.get(_media(world)).status_code == 404  # same live cookie, next request
    assert b"SENTINEL" not in tester.get(_media(world),
                                         headers={"Range": "bytes=0-9"}).content


def test_tp1_unassigning_and_disabling_stop_the_next_request(world: World) -> None:
    sub, tester = world.users["sub"], world.users["tester"]
    assert sub.get(_media(world)).status_code == 200
    set_relation(SLUG, user_id(email("sub")), ProjectRelation.ASSIGNED, False)
    assert sub.get(_media(world)).status_code == 404
    _share(world, "dev", "tester")
    assert tester.get(_media(world)).status_code == 200
    accounts.set_disabled(user_id(email("tester")), True)
    assert tester.get(_media(world)).status_code in {302, 401}


@pytest.mark.parametrize("vid", ["%2e%2e%2fx", "..%5cx", "nosuchvideo", "a" * 200])
def test_tp1_a_traversal_or_unknown_id_returns_nothing(world: World, vid: str) -> None:
    for name in ("admin", "tester"):
        got = world.users[name].get(f"/projects/{SLUG}/videos/{vid}/media")
        assert got.status_code == 404 and b"SENTINEL" not in got.content


def test_tp1_a_recorded_path_outside_the_project_is_never_served(world: World) -> None:
    outside = world.root / "outside-secret.mp4"
    outside.write_bytes(b"OUTSIDE-SECRET")
    hostile = add_video(world.root, email("dev"), "hostile")
    store_row = hostile.model_copy(update={"path": "../../outside-secret.mp4"})
    assert media_path(SLUG, store_row) is None
    assert media_path(SLUG, hostile.model_copy(update={"path": None})) is None


def test_tp1_a_video_with_no_recorded_uploader_matches_only_admin(world: World) -> None:
    orphan = add_video(world.root, None, "orphan")
    page = world.page(orphan.id) + "/media"
    assert world.users["admin"].get(page).status_code == 200
    assert world.users["dev"].get(page).status_code == 404


# -- TP4 ----------------------------------------------------------------------------------

PORTAL_ROUTES = [key for key in policy.PORTAL_POLICY]


def test_tp4_every_portal_route_is_declared_and_served() -> None:
    served = set(app_routes())
    assert PORTAL_ROUTES and all(route in served for route in PORTAL_ROUTES)
    assert [r for r in served if r not in policy.ROUTE_POLICY] == []
    for route in PORTAL_ROUTES:
        assert policy.ROUTE_POLICY[route] == policy.PORTAL_POLICY[route]


def test_tp4_no_portal_route_declares_a_key_outside_the_catalogue() -> None:
    for route, rule in policy.PORTAL_POLICY.items():
        assert isinstance(rule, RouteRule)
        assert rule.kind in {"key", "project", "video"} and rule.key in CATALOGUE, route


def _fill(path: str, w: World) -> str:
    return re.sub(r"\{(\w+)[^}]*\}", lambda m: {
        "slug": SLUG, "video_id": w.vid, "comment_id": "999", "request_id": "999",
        "token": "t" * 40}[m.group(1)], path)


def test_tp4_a_video_rule_route_is_absent_for_whoever_may_not_view_it(world: World) -> None:
    """Every `video`/`project` rule route, called directly, never through the UI."""
    for (method, template), rule in policy.PORTAL_POLICY.items():
        if rule.kind != "video":
            continue
        path = _fill(template, world)
        for name in SIGNED_IN_DENIED:
            got = world.users[name].request(method, path, headers=JSON)
            assert got.status_code == 404, (method, template, name, got.status_code)
        assert anonymous().request(method, path, headers=JSON).status_code == 401
        assert world.users["nogroup"].request(method, path, headers=JSON).status_code == 403


def test_tp4_a_tester_with_a_share_can_read_and_comment_but_not_share_or_promote(
        world: World) -> None:
    _share(world, "dev", "tester")
    tester = world.users["tester"]
    base = world.page()
    assert tester.get(base + "/comments", headers=JSON).status_code == 200
    assert tester.post(base + "/comments", data={"at_s": "3", "text": "hi"}).status_code == 303
    assert tester.post(base + "/share-link").status_code == 403
    assert tester.post(base + "/shares", data={"email": email("tester2")}).status_code == 403
    assert tester.post(base + "/comments/1/promote").status_code == 404  # no project access


def test_tp4_access_requests_are_for_approvers_only(world: World) -> None:
    for name in ("admin", "sub", "dev", "dev2"):
        assert world.users[name].get("/access-requests", headers=HTML).status_code == 200
    for name in ("tester", "tester2"):
        assert world.users[name].get("/access-requests", headers=JSON).status_code == 403
    assert world.users["nogroup"].get("/access-requests", headers=JSON).status_code == 403
    assert anonymous().get("/access-requests", headers=JSON).status_code == 401


def test_tp4_the_shared_list_shows_only_what_the_account_may_open(world: World) -> None:
    other = add_video(world.root, email("dev2"), "other", label="Other dev video")
    _share(world, "dev", "tester")
    tester_page = world.users["tester"].get("/shared", headers=HTML).text
    assert "Checkout demo" in tester_page and "Other dev video" not in tester_page
    assert other.id not in tester_page
    assert "Access requests" not in tester_page  # an approver's link is not shown to a tester
    assert "Access requests" in world.users["dev"].get("/shared", headers=HTML).text

"""TA2 (CRITICAL): nothing happens before access. A whole-surface sweep of every state-changing
Group 10 route as anonymous, as `pending`, and with a forged Origin leaves the data root
byte-identical and every seam log empty; a signed-in `dev` sweep must CHANGE it (the diff can
see a change). Then each placed user's next click reaches a page and `other` stays absent."""

from __future__ import annotations

import re

import pytest
from auth_harness import app_routes
from rig import HTML, OTHER, SLUG, World, with_origin

SKIP = ("/auth/", "/docs", "/openapi", "/redoc", "/healthz", "/onboard")
BODY = {"name": "x", "label": "x", "text": "x", "at_s": "1", "link": "https://drive.test/x",
        "email": "x@team.test", "to": "mallory@evil.test"}


def group10_posts() -> list[str]:
    """Every POST route except sign-in/sign-up/logout (AU-owned) with ids filled in."""
    paths = []
    for method, path in app_routes():
        if method != "POST" or path.startswith(SKIP):
            continue
        filled = re.sub(r"\{slug\}", SLUG, path)
        filled = re.sub(r"\{(token|action|group_id|user_id|request_id|video_id|comment_id|"
                        r"issue_id|case_id|crawl_id|source_id|key|run_id)[^}]*\}", "x1", filled)
        paths.append(filled)
    return sorted(set(paths))


def sweep(client, paths: list[str], **headers) -> None:
    for path in paths:
        client.post(path, data=BODY, headers={**HTML, **headers}, follow_redirects=False)


def test_the_sweep_covers_the_group_10_surface() -> None:
    paths = group10_posts()
    assert len(paths) >= 25
    for needle in ("/test", "/sources/upload", "/sources/drive", "/share-link",
                   "/request-access", "/comments", "/run", "/access-requests/"):
        assert any(needle in p for p in paths), needle


def test_anonymous_pending_and_forged_origin_change_nothing(world: World) -> None:
    paths = group10_posts()
    before, seams = world.snapshot(), world.seam_calls()
    sweep(world.anonymous(), paths)
    sweep(world.users["pending"], paths)
    sweep(world.users["dev"], paths, origin="https://evil.example")      # forged Origin
    assert world.snapshot() == before
    assert world.seam_calls() == seams
    assert not list((world.root / "projects" / SLUG).glob("runs/*"))
    assert world.seam_calls()["outbox"] == []


def test_the_pending_account_sees_only_sign_in_and_waiting_screens(world: World) -> None:
    pending = world.users["pending"]
    page = pending.get("/", headers=HTML)
    assert page.status_code in (302, 303, 403)
    if page.status_code in (302, 303):
        assert "/auth/waiting" in page.headers["location"]
    assert pending.get(f"/projects/{SLUG}", headers=HTML).status_code in (302, 303, 403, 404)
    assert pending.get("/auth/waiting", headers=HTML).status_code == 200


def test_profile_is_readable_but_pending_cannot_save_before_placement(world: World) -> None:
    before = world.snapshot()
    pending = world.users["pending"]
    assert pending.get("/profile", headers=HTML).status_code == 200
    response = pending.post("/profile", data={"email_run_reports": "on"}, headers=HTML)
    assert response.status_code == 403
    assert world.snapshot() == before
    assert not (world.root / ".work" / "notification_prefs").exists()
    assert world.users["dev"].post(
        "/profile", data={"email_run_reports": "on"}, headers=HTML).status_code == 303
    assert " checked" in world.users["dev"].get("/profile", headers=HTML).text


def test_a_signed_in_dev_sweep_does_change_the_data_root(world: World) -> None:
    """Sabotage guard: the same diff goes red on the 'changed' side for a permitted user."""
    before = world.snapshot()
    world.users["dev"].post(f"/projects/{SLUG}/test", headers=HTML)
    assert world.snapshot() != before


@pytest.mark.parametrize("role", ["dev", "subadmin", "tester"])
def test_next_click_reaches_the_default_page_and_other_stays_absent(
        world: World, role: str) -> None:
    user = world.users[role]
    assert user.get("/", headers=HTML).status_code == 200
    stub = user.get(f"/projects/{SLUG}", headers=HTML).status_code
    assert stub == (404 if role == "tester" else 200)      # a tester gets in by share + approval
    assert user.get(f"/projects/{OTHER}", headers=HTML).status_code == 404
    assert with_origin(user).post(f"/projects/{OTHER}/test", headers=HTML).status_code == 404

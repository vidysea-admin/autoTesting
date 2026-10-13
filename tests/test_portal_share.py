"""T-198b TP3: the share link is non-guessable, needs sign-in, and carries no capability.

Scenario source: a developer creates a link and pastes it to a tester; the link must lead a
signed-out visitor to sign-in, a signed-in non-member to the request-access page (never the
bytes), and a member to the player; once revoked it behaves like a link that never existed.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from portal_support import SLUG, World, anonymous, build_world, email

from autotester.auth import db
from autotester.stages import video_access as access

HTML = {"accept": "text/html"}
LINK = re.compile(r"value='[^']*?/v/([A-Za-z0-9_-]+)'")


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    return build_world(tmp_path, monkeypatch)


def _make_link(world: World, who: str = "dev") -> str:
    resp = world.users[who].post(world.page() + "/share-link")
    assert resp.status_code == 200
    found = LINK.search(resp.text)
    assert found, resp.text
    return found.group(1)


def test_tp3_the_token_is_long_random_and_unique_per_link(world: World) -> None:
    token = _make_link(world)
    assert len(token) >= 43 and re.fullmatch(r"[A-Za-z0-9_-]+", token)  # 32 bytes = 256 bits
    assert world.vid not in token and SLUG not in token
    seen = {access.create_link(SLUG, f"v{n}", "dev@team.test") for n in range(1000)}
    assert len(seen) == 1000 and token not in seen


def test_tp3_only_the_token_hash_is_stored(world: World) -> None:
    token = _make_link(world)
    with db.reading() as conn:
        rows = [tuple(r) for r in conn.execute("SELECT * FROM video_links")]
    assert rows and all(token not in str(cell) for row in rows for cell in row)
    assert token.encode() not in db.auth_db_path().read_bytes()


def test_tp3_possessing_the_url_grants_nothing(world: World) -> None:
    token = _make_link(world)
    anon = anonymous().get(f"/v/{token}", headers=HTML)
    assert anon.status_code == 302 and anon.headers["location"].startswith("/auth/login")
    tester = world.users["tester"]
    got = tester.get(f"/v/{token}", headers=HTML)
    assert got.status_code == 404 and "Request access" in got.text
    assert "<video" not in got.text and "Checkout demo" not in got.text
    assert tester.get(world.page() + "/media").status_code == 404
    member = world.users["admin"].get(f"/v/{token}", headers=HTML)
    assert member.status_code == 303 and member.headers["location"] == world.page()


def _shape(text: str, token: str) -> str:
    return text.replace(token, "TOKEN")


def test_tp3_a_revoked_or_unknown_token_answers_like_any_unknown_video(world: World) -> None:
    token = _make_link(world)
    assert world.users["dev"].post(world.page() + "/share-link/revoke").status_code == 303
    tester, admin = world.users["tester"], world.users["admin"]
    revoked = tester.get(f"/v/{token}", headers=HTML)
    unknown = tester.get("/v/" + "z" * len(token), headers=HTML)
    assert revoked.status_code == unknown.status_code == 404
    assert _shape(revoked.text, token) == _shape(unknown.text, "z" * len(token))
    assert admin.get(f"/v/{token}", headers=HTML).status_code == 404  # even a member: no link
    for odd in (token[:-5], token + "x" * 200, "a b", "%2e%2e", "%00"):
        got = tester.get(f"/v/{odd}", headers=HTML)
        assert got.status_code == 404 and "<video" not in got.text, odd


def test_tp3_a_new_link_replaces_the_old_one(world: World) -> None:
    first, second = _make_link(world), _make_link(world)
    assert first != second
    assert access.resolve_link(first) is None and access.resolve_link(second) is not None


def test_tp3_only_a_holder_of_video_share_can_create_or_revoke(world: World) -> None:
    world.users["dev"].post(world.page() + "/shares", data={"email": email("tester")})
    for name, status in (("tester", 403), ("dev2", 404), ("nogroup", 403)):
        for tail in ("/share-link", "/share-link/revoke", "/shares"):
            got = world.users[name].post(world.page() + tail, data={"email": email("tester2")})
            assert got.status_code == status, (name, tail)
    assert access.live_link_since(SLUG, world.vid) is None
    assert _make_link(world, "sub") and _make_link(world, "admin")


def test_tp3_the_token_never_reaches_a_log_or_the_audit_file(
        world: World, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    token = _make_link(world)
    world.users["tester"].get(f"/v/{token}", headers=HTML)
    world.users["tester"].post(f"/v/{token}/request-access")
    world.users["dev"].post(world.page() + "/share-link/revoke")
    audit = (world.root / ".work" / "audit.jsonl").read_text(encoding="utf-8")
    assert token not in audit and "/v/{token}" in audit
    ours = [r.getMessage() for r in caplog.records if not r.name.startswith("httpx")]
    assert all(token not in line for line in ours)  # the server's lines; the client's are not


def test_tp3_deleting_the_video_or_project_removes_its_links(world: World) -> None:
    token = _make_link(world)
    access.purge_video(SLUG, world.vid)
    assert access.resolve_link(token) is None
    other = access.create_link(SLUG, "keepme", "dev@team.test")
    access.purge_project_videos(SLUG)
    assert access.resolve_link(other) is None

"""T-198b TP2 (timestamped comments) and TP6 (promote a comment to a pointer).

Scenario source: a developer and a shared tester comment at seconds of a recording; a comment
that is a script must stay text on every page; a comment at 754 s promoted by the project's
owner becomes the pointer `12:34 | ...` the review's parser accepts, and the comment stays.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from portal_support import SLUG, World, add_video, build_world, email

from autotester.stages import video_comments as comments
from autotester.stages.video_pointers import parse_pointers

HTML, JSON = {"accept": "text/html"}, {"accept": "application/json"}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    return build_world(tmp_path, monkeypatch)


def _post(world: World, who: str, at_s: str, text: str, **extra: str) -> int:
    return world.users[who].post(world.page() + "/comments", data={
        "at_s": at_s, "text": text, **extra}).status_code


def _listed(world: World, who: str = "dev", vid: str | None = None) -> list[dict]:
    resp = world.users[who].get(world.page(vid) + "/comments", headers=JSON)
    assert resp.status_code == 200
    return resp.json()["comments"]


@pytest.mark.parametrize("at_s, ok", [
    ("-0.001", False), ("0", True), ("120", True), ("120.001", False), ("nan", False),
    ("inf", False), ("-inf", False), ("abc", False), ("", False), ("1e999", False),
    ("12.5", True)])
def test_tp2_the_second_must_be_inside_the_video(world: World, at_s: str, ok: bool) -> None:
    got = _post(world, "dev", at_s, "look here")
    assert got == (303 if ok else 400), at_s
    assert len(_listed(world)) == (1 if ok else 0)


@pytest.mark.parametrize("text, ok", [("", False), ("   ", False), ("x", True),
                                      ("y" * 2000, True), ("y" * 2001, False),
                                      ("  padded  ", True)])
def test_tp2_the_text_is_one_to_2000_characters_after_trim(
        world: World, text: str, ok: bool) -> None:
    assert _post(world, "dev", "1", text) == (303 if ok else 400)
    if text.strip() == "padded":
        assert _listed(world)[0]["text"] == "padded"


def test_tp2_a_source_without_a_known_duration_takes_any_finite_nonnegative_second(
        world: World) -> None:
    open_ended = add_video(world.root, email("dev"), "open", duration=None)
    page = world.page(open_ended.id)
    post = world.users["dev"].post
    assert post(page + "/comments", data={"at_s": "99999", "text": "late"}).status_code == 303
    assert post(page + "/comments", data={"at_s": "-1", "text": "early"}).status_code == 400
    assert post(page + "/comments", data={"at_s": "nan", "text": "n"}).status_code == 400


def test_tp2_the_author_comes_from_the_session_never_the_body(world: World) -> None:
    assert _post(world, "dev", "5", "mine", author="admin@team.test", email="x@y.z") == 303
    assert [c["author"] for c in _listed(world)] == [email("dev")]


def test_tp2_a_tester_comments_on_a_shared_video_and_on_no_other(world: World) -> None:
    other = add_video(world.root, email("dev"), "unshared", label="Unshared")
    world.users["dev"].post(world.page() + "/shares", data={"email": email("tester")})
    assert _post(world, "tester", "3", "seen") == 303
    refused = world.users["tester"].post(world.page(other.id) + "/comments",
                                         data={"at_s": "1", "text": "no"})
    assert refused.status_code == 404
    assert _listed(world, "admin", other.id) == []
    assert [c["author"] for c in _listed(world, "dev")] == [email("tester")]


def test_tp2_a_script_comment_is_text_on_the_page(world: World) -> None:
    _post(world, "dev", "4", "<script>alert(1)</script>")
    _post(world, "dev", "5", '"><img src=x onerror=alert(2)>')
    page = world.users["dev"].get(world.page(), headers=HTML).text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)" not in page and "<img src=x" not in page
    assert "&lt;img src=x onerror=alert(2)&gt;" in page
    assert _listed(world)[0]["text"] == "<script>alert(1)</script>"  # data, as stored


def test_tp2_a_comment_second_is_a_seek_target_for_every_viewer(world: World) -> None:
    _post(world, "dev", "75", "check out")
    world.users["dev"].post(world.page() + "/shares", data={"email": email("tester")})
    for name in ("dev", "tester", "admin"):
        page = world.users[name].get(world.page(), headers=HTML).text
        assert "data-seek='75'" in page and "check out" in page and "id='player'" in page


def test_tp2_only_the_author_edits_and_the_edit_is_marked(world: World) -> None:
    _post(world, "dev", "2", "first")
    cid = _listed(world)[0]["id"]
    base = world.page() + f"/comments/{cid}"
    assert world.users["admin"].post(base + "/edit", data={"text": "hijack"}).status_code == 403
    assert world.users["dev"].post(base + "/edit", data={"text": ""}).status_code == 400
    assert world.users["dev"].post(base + "/edit", data={"text": "second"}).status_code == 303
    row = _listed(world)[0]
    assert row["text"] == "second" and row["edited"] is True
    assert "(edited)" in world.users["dev"].get(world.page(), headers=HTML).text


def test_tp2_delete_is_the_authors_or_a_holder_of_comment_create_at_all(world: World) -> None:
    world.users["dev"].post(world.page() + "/shares", data={"email": email("tester")})
    _post(world, "tester", "1", "t-one")
    _post(world, "tester", "2", "t-two")
    first, second = (c["id"] for c in _listed(world))
    base = world.page() + "/comments"
    assert world.users["dev"].post(f"{base}/{first}/delete").status_code == 403  # not the author
    assert world.users["tester"].post(f"{base}/{first}/delete").status_code == 303
    assert world.users["admin"].post(f"{base}/{second}/delete").status_code == 303
    assert _listed(world) == []
    assert world.users["admin"].post(f"{base}/99999/delete").status_code == 404


def test_tp2_comment_controls_the_viewer_cannot_use_are_not_rendered(world: World) -> None:
    world.users["dev"].post(world.page() + "/shares", data={"email": email("tester")})
    _post(world, "dev", "9", "dev note")
    tester = world.users["tester"].get(world.page(), headers=HTML).text
    assert "dev note" in tester and "/delete" not in tester and "/promote" not in tester
    assert "Create a new share link" not in tester
    assert "/promote" in world.users["dev"].get(world.page(), headers=HTML).text


def _promote(world: World, who: str, cid: int, vid: str | None = None) -> int:
    return world.users[who].post(world.page(vid) + f"/comments/{cid}/promote").status_code


def test_tp6_promoting_a_comment_gives_the_pointer_the_parser_accepts(world: World) -> None:
    long = add_video(world.root, email("dev"), "long", duration=900.0)
    world.users["dev"].post(world.page(long.id) + "/comments",
                            data={"at_s": "754", "text": "cart total looks wrong"})
    cid = _listed(world, "dev", long.id)[0]["id"]
    assert _promote(world, "dev", cid, long.id) == 303
    assert _promote(world, "dev", cid, long.id) == 303  # again: still one pointer
    text = comments.pointer_text(SLUG, long.id)
    assert text == "12:34 | cart total looks wrong"
    parsed = parse_pointers(text, 900.0)
    assert parsed.errors == [] and [(p.kind, p.start_s, p.text) for p in parsed.parsed] == [
        ("time", 754.0, "cart total looks wrong")]
    assert len(_listed(world, "dev", long.id)) == 1  # the comment stays
    assert _listed(world, "dev", long.id)[0]["promoted"] is True


def test_tp6_a_user_without_project_edit_creates_nothing(world: World) -> None:
    world.users["dev"].post(world.page() + "/shares", data={"email": email("tester")})
    _post(world, "dev", "7", "note")
    cid = _listed(world)[0]["id"]
    assert _promote(world, "tester", cid) in {403, 404}
    assert _promote(world, "dev2", cid) in {403, 404}
    assert comments.pointer_text(SLUG, world.video.id) == ""
    assert _promote(world, "sub", cid) == 303 and comments.pointer_text(SLUG, world.vid)


@pytest.mark.parametrize("at_s, text", [
    (10.0, "x" * 600), (120.0, "at the very end"), (3.0, "12:34 looks like a time"),
    (3.0, "line one\nline two | pipes | here"), (0.0, "|"), (59.9, "é" * 700)])
def test_tp6_a_comment_that_cannot_parse_as_typed_is_kept_as_text_never_dropped(
        at_s: float, text: str) -> None:
    line = comments.pointer_line(at_s, text, 120.0)
    assert line.strip() and not parse_pointers(line, 120.0).errors

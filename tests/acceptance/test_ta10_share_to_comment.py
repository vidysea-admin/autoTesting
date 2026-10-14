"""TA10: share, request access, approve, comment, and the promoted comment reaches the review.
`tester` opens dev's share link, sees the request-access page and never the bytes; dev (the owner)
approves; the tester watches and comments at second 42; admin promotes the comment to a pointer
and the next review run includes it."""

from __future__ import annotations

import re

from review_support import grant_review, review, upload_video
from rig import HTML, SLUG, World

from autotester.stages import video_comments as comments

LINK = re.compile(r"/v/([A-Za-z0-9_-]+)")
REQUEST = re.compile(r"/access-requests/(\d+)/approve")


def _setup(world: World):
    source = upload_video(world, "dev")
    page = f"/projects/{SLUG}/videos/{source.id}"
    made = world.users["dev"].post(page + "/share-link", headers=HTML)
    assert made.status_code == 200
    token = LINK.search(made.text)
    assert token, made.text[:400]
    return source, page, token.group(1)


def test_the_testers_whole_loop_and_the_comment_reaches_the_review(world: World) -> None:
    source, page, token = _setup(world)
    tester = world.users["tester"]
    opened = tester.get(f"/v/{token}", headers=HTML)
    assert opened.status_code == 404 and "Request access" in opened.text
    assert "<video" not in opened.text
    assert tester.get(page + "/media").status_code == 404           # never the bytes
    assert tester.post(page + "/request-access").status_code == 200

    pending = world.users["dev"].get("/access-requests", headers=HTML).text
    rid = REQUEST.search(pending)
    assert rid, pending[:400]
    assert tester.post(f"/access-requests/{rid.group(1)}/approve").status_code in (403, 404)
    assert world.users["dev"].post(f"/access-requests/{rid.group(1)}/approve").status_code == 303
    assert tester.get(page + "/media").status_code == 200           # next click shows the video

    assert tester.post(page + "/comments", data={"at_s": "42", "text": "price is wrong here"}
                       ).status_code == 303
    for who in ("dev", "admin"):
        listed = world.users[who].get(page + "/comments").json()["comments"]
        assert [(c["at_s"], c["author"]) for c in listed] == [(42.0, "tester@team.test")]
    assert world.users["pending"].get(page + "/comments").status_code in (302, 303, 403, 404)

    cid = listed[0]["id"]
    assert world.users["admin"].post(page + f"/comments/{cid}/promote").status_code == 303
    assert world.users["admin"].get(page + "/comments").json()["comments"][0]["promoted"] is True
    pointer_text = comments.pointer_text(SLUG, source.id)
    assert "price is wrong here" in pointer_text

    grant_review(world)
    result = review(world, source, pointer_text)
    assert result.status == "ok"
    assert any("price is wrong here" in prompt for prompt in world.provider.prompts)


def test_a_tester_cannot_approve_their_own_request_nor_make_a_link(world: World) -> None:
    _source, page, _token = _setup(world)
    tester = world.users["tester"]
    assert tester.post(page + "/share-link").status_code in (403, 404)
    assert tester.post(page + "/request-access").status_code == 200
    assert tester.get(page + "/media").status_code == 404

"""T-198b TP5: the request-access flow; a developer approves access to their own videos.

Scenario source: Tester-B opens the direct URL of a video Dev-A uploaded, asks for access, Dev-A
approves it from the Access requests page and B gets in; Dev-C (another developer) cannot
approve it; a sub-admin of that project and an admin can; a decline gives no share.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import account, login, user_id
from portal_support import SLUG, World, build_world, email

from autotester.auth import accounts, db, groups
from autotester.auth.access import set_relation
from autotester.delivery import email as mail
from autotester.schema.auth import ProjectRelation
from autotester.stages import video_access as access
from autotester.stages import video_requests as requests

HTML = {"accept": "text/html"}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    return build_world(tmp_path, monkeypatch)


def _ask(world: World, who: str = "tester") -> int:
    return world.users[who].post(world.page() + "/request-access").status_code


def _pending(world: World) -> list:
    with db.reading() as conn:
        return [tuple(r) for r in conn.execute(
            "SELECT id, requester FROM access_requests WHERE status = 'pending' ORDER BY id")]


def _rid(world: World, who: str) -> int:
    return next(i for i, r in _pending(world) if r == email(who))


def _decide(world: World, who: str, rid: int, verb: str = "approve") -> int:
    return world.users[who].post(f"/access-requests/{rid}/{verb}").status_code


def _opens(world: World, who: str) -> bool:
    return world.users[who].get(world.page() + "/media").status_code == 200


def test_tp5_asking_records_the_requester_from_the_session_once(world: World) -> None:
    assert _ask(world) == 200 and _ask(world) == 200 and _ask(world) == 200
    assert _pending(world) == [(1, email("tester"))]
    page = world.users["tester"].get(world.page(), headers=HTML)
    assert page.status_code == 404 and "waiting for a decision" in page.text


def test_tp5_the_request_page_names_roles_not_emails(world: World) -> None:
    page = world.users["tester"].get(world.page(), headers=HTML).text
    assert "uploaded the video" in page and "sub-admin" in page and "admin" in page
    assert "@team.test" not in page.replace(email("tester"), "")


def test_tp5_the_uploader_approves_and_the_requester_gets_in_exactly_once(world: World) -> None:
    _ask(world)
    assert not _opens(world, "tester")
    rid = _rid(world, "tester")
    listed = world.users["dev"].get("/access-requests", headers=HTML).text
    assert email("tester") in listed
    assert _decide(world, "dev", rid) == 303
    assert _decide(world, "dev", rid) == 303 and _decide(world, "dev", rid) == 303
    assert _opens(world, "tester")
    assert access.shared_emails(SLUG, world.vid) == frozenset({email("tester")})
    with db.reading() as conn:
        assert conn.execute("SELECT COUNT(*) FROM video_shares").fetchone()[0] == 1
    page = world.users["tester"].get("/shared", headers=HTML).text
    assert "approved" in page


def test_tp5_another_developer_cannot_approve_or_decline_it(world: World) -> None:
    _ask(world)
    rid = _rid(world, "tester")
    for verb in ("approve", "decline"):
        assert _decide(world, "dev2", rid, verb) == 404
    assert not _opens(world, "tester") and _pending(world)
    assert email("tester") not in world.users["dev2"].get("/access-requests", headers=HTML).text


def test_tp5_a_sub_admin_of_the_project_and_an_admin_may_approve(world: World) -> None:
    _ask(world, "tester")
    _ask(world, "tester2")
    assert _decide(world, "sub", _rid(world, "tester")) == 303 and _opens(world, "tester")
    assert _decide(world, "admin", _rid(world, "tester2")) == 303 and _opens(world, "tester2")


def test_tp5_a_sub_admin_cannot_act_outside_assigned_projects(world: World) -> None:
    _ask(world)
    set_relation(SLUG, user_id(email("sub")), ProjectRelation.ASSIGNED, False)
    assert _decide(world, "sub", _rid(world, "tester")) == 404 and not _opens(world, "tester")


def test_tp5_declining_records_the_decision_and_shares_nothing(world: World) -> None:
    _ask(world)
    rid = _rid(world, "tester")
    assert _decide(world, "dev", rid, "decline") == 303
    assert not _opens(world, "tester") and access.shared_emails(SLUG, world.vid) == frozenset()
    assert "declined" in world.users["tester"].get("/shared", headers=HTML).text
    assert _decide(world, "dev", rid, "approve") == 303  # a decided request cannot be flipped
    assert not _opens(world, "tester")


def test_tp5_the_requester_cannot_approve_their_own_request(world: World) -> None:
    groups.create_group("Approver", ["access.approve@all", "video.view@shared"])
    uid = account("picky@team.test")
    accounts.set_user_groups(uid, [g.id for g in groups.list_groups() if g.name == "Approver"])
    picky = login("picky@team.test")
    assert picky.post(world.page() + "/request-access").status_code == 200
    rid = next(i for i, r in _pending(world) if r == "picky@team.test")
    assert picky.post(f"/access-requests/{rid}/approve").status_code == 404
    assert picky.get(world.page() + "/media").status_code == 404
    assert access.shared_emails(SLUG, world.vid) == frozenset()


def test_tp5_the_approvers_are_the_uploader_the_sub_admin_and_admins(world: World) -> None:
    res = access.video_resource(SLUG, world.vid)
    assert res is not None
    assert requests.approvers(res, email("tester")) == sorted(
        [email("admin"), email("dev"), email("sub")])


def test_tp5_an_unknown_video_gets_the_same_answer_and_stores_nothing(world: World) -> None:
    known = world.users["tester"].post(world.page() + "/request-access")
    other = world.users["tester"].post(world.page("nosuchvideo") + "/request-access")
    assert known.status_code == other.status_code == 200 and known.text == other.text
    assert _pending(world) == [(1, email("tester"))]


def test_tp5_the_notification_mail_carries_a_link_and_nothing_else() -> None:
    sent: list[tuple[str, str]] = []

    class Fake:
        outcome = None

        def send(self, to, message, *, key):
            sent.append((to.address, message.body + message.subject))

    count = requests.notify_approvers(["dev@team.test", "admin@team.test"],
                                      "https://at.example/access-requests", transport=Fake())
    assert count == 2 and {a for a, _ in sent} == {"dev@team.test", "admin@team.test"}
    assert all("https://at.example/access-requests" in body for _, body in sent)
    assert all("Checkout" not in body for _, body in sent)


def test_tp5_no_mail_is_attempted_when_smtp_is_not_configured() -> None:
    assert requests.notify_approvers(["dev@team.test"], "https://at.example/", environ={}) == 0


def test_tp5_a_failing_mail_transport_never_blocks_the_request(
        world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(mail.ENV_HOST, "127.0.0.1")
    monkeypatch.setenv(mail.ENV_PORT, "1")
    monkeypatch.setenv(mail.ENV_FROM, "at@localhost.test")
    monkeypatch.setenv(mail.ENV_TLS, "none")
    assert _ask(world) == 200 and _pending(world)


def test_tp5_a_video_page_for_a_member_does_not_offer_the_request(world: World) -> None:
    assert _ask(world, "dev") == 303  # asking when you already have access goes to the video
    assert _pending(world) == []

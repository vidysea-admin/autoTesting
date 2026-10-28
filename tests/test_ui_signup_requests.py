"""Signup requests: an account with no group is listed for admins on /access-requests, who
approve it into a group or decline it; admins are notified on signup; /admin/users flags it.

Bug source (Umesh 2026-10-28, live): a person signed up, saw "waiting for an administrator",
and the administrator never saw a request anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, group_id, login, user_id

from autotester.auth import accounts, groups
from autotester.ui import routes_auth

HTML = {"accept": "text/html"}
WAITING = "New accounts waiting"
NEWBIE = "newbie@team.test"


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    return root


def _approve(uid: int) -> str:
    return f"/access-requests/accounts/{uid}/approve"


def _decline(uid: int) -> str:
    return f"/access-requests/accounts/{uid}/decline"


def _actions(root: Path) -> list[dict]:
    path = root / ".work" / "audit.jsonl"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if "action" in r]


def test_sr1_admin_sees_a_groupless_account_in_a_waiting_section(root: Path) -> None:
    account(NEWBIE)
    page = login(ADMIN).get("/access-requests", headers=HTML)
    assert page.status_code == 200 and WAITING in page.text and NEWBIE in page.text
    assert "name='group_id'" in page.text and "Tester" in page.text
    assert _approve(user_id(NEWBIE)) in page.text and _decline(user_id(NEWBIE)) in page.text


def test_sr1_grouped_and_disabled_accounts_are_not_listed(root: Path) -> None:
    account("grouped@team.test", "tester")
    off = account("off@team.test")
    accounts.set_disabled(off, True)
    text = login(ADMIN).get("/access-requests", headers=HTML).text
    assert "grouped@team.test" not in text and "off@team.test" not in text


def test_sr2_the_section_is_for_people_who_manage_users_only(root: Path) -> None:
    account(NEWBIE)
    reviewer = groups.create_group("Reviewers", ["access.approve@all"])
    uid = account("reviewer@team.test")
    accounts.set_user_groups(uid, [reviewer.id])
    c = login("reviewer@team.test")
    page = c.get("/access-requests", headers=HTML)
    assert page.status_code == 200 and WAITING not in page.text and NEWBIE not in page.text
    assert c.post(_approve(user_id(NEWBIE)), data={"group_id": group_id("tester")}
                  ).status_code == 403
    assert c.post(_decline(user_id(NEWBIE))).status_code == 403
    assert accounts.get_user(user_id(NEWBIE)).groups == []


def test_sr3_approve_adds_the_chosen_group_and_is_audited(root: Path) -> None:
    uid = account(NEWBIE)
    resp = login(ADMIN).post(_approve(uid), data={"group_id": group_id("tester")})
    assert resp.status_code == 303 and resp.headers["location"] == "/access-requests"
    assert accounts.get_user(uid).groups == ["Tester"]
    assert {"actor": ADMIN, "target": NEWBIE, "action": "signup.approve"} in [
        {k: r[k] for k in ("actor", "target", "action")} for r in _actions(root)]
    assert NEWBIE not in login(ADMIN).get("/access-requests", headers=HTML).text


def test_sr3_approve_without_a_group_or_with_an_unknown_one_changes_nothing(
        root: Path) -> None:
    uid = account(NEWBIE)
    c = login(ADMIN)
    assert c.post(_approve(uid)).status_code == 400
    assert c.post(_approve(uid), data={"group_id": "9999"}).status_code == 400
    assert c.post(_approve(uid), data={"group_id": "x"}).status_code == 400
    assert accounts.get_user(uid).groups == []


def test_sr4_decline_disables_the_account_and_is_audited(root: Path) -> None:
    uid = account(NEWBIE)
    resp = login(ADMIN).post(_decline(uid))
    assert resp.status_code == 303 and accounts.get_user(uid).disabled is True
    assert "signup.decline" in [r["action"] for r in _actions(root)]
    refused = client().post("/auth/login", data={"email": NEWBIE, "password": PASSWORD})
    assert refused.status_code == 401
    assert NEWBIE not in login(ADMIN).get("/access-requests", headers=HTML).text


def test_sr5_an_account_that_already_has_a_group_is_not_touched(root: Path) -> None:
    uid = account("member@team.test", "tester")
    c = login(ADMIN)
    assert c.post(_approve(uid), data={"group_id": group_id("developer")}).status_code == 400
    assert c.post(_decline(uid)).status_code == 400
    user = accounts.get_user(uid)
    assert user.groups == ["Tester"] and user.disabled is False
    assert c.post(_decline(99999)).status_code == 404


def test_sr5_a_decided_request_cannot_be_decided_again(root: Path) -> None:
    uid = account(NEWBIE)
    c = login(ADMIN)
    assert c.post(_approve(uid), data={"group_id": group_id("tester")}).status_code == 303
    assert c.post(_approve(uid), data={"group_id": group_id("developer")}).status_code == 400
    assert accounts.get_user(uid).groups == ["Tester"]


def test_sr6_a_manager_cannot_approve_into_admin_or_beyond_their_own_rights(
        root: Path) -> None:
    uid = account(NEWBIE)
    managers = groups.create_group("People", ["users.manage", "access.approve@all"])
    mid = account("people@team.test")
    accounts.set_user_groups(mid, [managers.id])
    c = login("people@team.test")
    assert c.post(_approve(uid), data={"group_id": group_id("admin")}).status_code == 403
    assert c.post(_approve(uid), data={"group_id": group_id("developer")}).status_code == 403
    assert accounts.get_user(uid).groups == []
    assert "signup.approve.refused" in [r["action"] for r in _actions(root)]


def test_sr7_a_cross_site_decision_is_refused(root: Path) -> None:
    uid = account(NEWBIE)
    c = login(ADMIN)
    bad = {"origin": "http://evil.test"}
    assert c.post(_approve(uid), data={"group_id": group_id("tester")},
                  headers=bad).status_code == 403
    assert c.post(_decline(uid), headers=bad).status_code == 403
    user = accounts.get_user(uid)
    assert user.groups == [] and user.disabled is False


def test_sr8_the_users_page_flags_waiting_accounts(root: Path) -> None:
    account(NEWBIE)
    account("member@team.test", "tester")
    off = account("off@team.test")
    accounts.set_disabled(off, True)
    rows = login(ADMIN).get("/admin/users", headers=HTML).text.split("<tr>")
    by_email = {e: next(r for r in rows if e in r) for e in (NEWBIE, "member@team.test",
                                                              "off@team.test", ADMIN)}
    assert "Waiting" in by_email[NEWBIE]
    for other in ("member@team.test", "off@team.test", ADMIN):
        assert "Waiting" not in by_email[other]


def test_sr9_signing_up_without_a_group_notifies_the_user_managers_with_a_link(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")   # hosted: a signup joins no group
    managers = groups.create_group("People", ["users.manage"])
    account("people@team.test")
    accounts.set_user_groups(user_id("people@team.test"), [managers.id])
    off = account("gone@team.test", "admin")
    accounts.set_disabled(off, True)
    sent: list[tuple[list[str], str, dict]] = []
    monkeypatch.setattr(routes_auth, "notify_approvers",
                        lambda emails, link, **kw: sent.append((emails, link, kw)) or len(emails))
    resp = client().post("/auth/signup", data={"email": NEWBIE, "password": PASSWORD})
    assert resp.status_code == 303 and len(sent) == 1
    emails, link, kw = sent[0]
    assert emails == [ADMIN, "people@team.test"]       # sorted, enabled holders only
    assert link.endswith("/access-requests")
    assert NEWBIE not in json.dumps(kw)                 # the mail names no one, only a link


def test_sr9_a_notification_failure_never_blocks_the_signup(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")

    def boom(*_a: object, **_k: object) -> int:
        raise OSError("smtp down")

    monkeypatch.setattr(routes_auth, "notify_approvers", boom)
    resp = client().post("/auth/signup", data={"email": NEWBIE, "password": PASSWORD})
    assert resp.status_code == 303 and accounts.find_user(NEWBIE) is not None


def test_sr9_the_default_mail_is_unchanged_for_video_requests() -> None:
    from autotester.stages import video_requests as requests
    sent: list[str] = []

    class Fake:
        outcome = None

        def send(self, to, message, *, key):
            sent.append(message.subject + "|" + message.body)

    requests.notify_approvers(["a@team.test"], "https://at.example/x", transport=Fake())
    requests.notify_approvers(["a@team.test"], "https://at.example/x", transport=Fake(),
                              subject="AutoTester: a new account is waiting",
                              body="A new account is waiting.\nOpen: {link}\n")
    assert sent == [
        "AutoTester: someone asked for access to a video|Someone asked for access to a video "
        "you can approve.\nOpen the requests page: https://at.example/x\n",
        "AutoTester: a new account is waiting|A new account is waiting.\n"
        "Open: https://at.example/x\n"]

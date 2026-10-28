"""signup-requests-f1: review follow-ups on the signup-request flow (F1 id parsing, F2 who is
mailed) plus the concurrency and session guarantees the first unit only asserted in prose.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, group_id, login, user_id

from autotester.auth import accounts, groups
from autotester.ui import routes_auth

NEWBIE = "newbie@team.test"
HTML = {"accept": "text/html"}


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    return root


def _approve(uid: int | str) -> str:
    return f"/access-requests/accounts/{uid}/approve"


def _decline(uid: int | str) -> str:
    return f"/access-requests/accounts/{uid}/decline"


# --- F1: a malformed id is a 400/4xx, never a 500 ---------------------------------------
BAD_IDS = ["²", "٣", "9" * 30, str(2**63), str(2**64), "-1", " 1", "1_0", "1.5",
           "0x1", "", "1e3"]


@pytest.mark.parametrize("raw", BAD_IDS)
def test_f1_malformed_group_id_is_refused_with_400_and_changes_nothing(
        root: Path, raw: str) -> None:
    uid = account(NEWBIE)
    c = login(ADMIN)
    c.raise_server_exceptions = False
    resp = c.post(_approve(uid), data={"group_id": raw})
    assert resp.status_code == 400, (raw, resp.status_code)
    assert accounts.get_user(uid).groups == []


def test_f1_the_refusal_is_audited_like_any_other(root: Path) -> None:
    uid = account(NEWBIE)
    c = login(ADMIN)
    c.raise_server_exceptions = False
    assert c.post(_approve(uid), data={"group_id": "9" * 30}).status_code == 400
    rows = (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")
    assert "signup.approve.refused" in rows


@pytest.mark.parametrize("uid", ["9" * 30, str(2**63), "0", "-5", "٣"])
def test_f1_a_malformed_user_id_in_the_path_is_never_a_500(root: Path, uid: str) -> None:
    c = login(ADMIN)
    c.raise_server_exceptions = False
    for path in (_approve(uid), _decline(uid)):
        resp = c.post(path, data={"group_id": group_id("tester")})
        assert resp.status_code in (400, 404, 422), (path, resp.status_code)


def test_f1_the_admin_users_page_shares_the_same_bounded_parser(root: Path) -> None:
    uid = account(NEWBIE)
    c = login(ADMIN)
    c.raise_server_exceptions = False
    for raw in ("9" * 30, "²", "٣"):
        resp = c.post(f"/admin/users/{uid}/groups", data={"group_id": raw})
        assert resp.status_code == 400, (raw, resp.status_code)
    assert accounts.get_user(uid).groups == []


# --- F2: only people who can open /access-requests are mailed ---------------------------
def _mailed(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")   # hosted: a signup joins no group
    sent: list[list[str]] = []
    monkeypatch.setattr(routes_auth, "notify_approvers",
                        lambda emails, link, **kw: sent.append(list(emails)) or len(emails))
    return sent


def _member(email: str, name: str, permissions: list[str]) -> None:
    group = groups.create_group(name, permissions)
    accounts.set_user_groups(account(email), [group.id])


def test_f2_a_users_manage_only_holder_is_not_mailed(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _mailed(monkeypatch)
    _member("manage-only@team.test", "ManageOnly", ["users.manage"])
    _member("both@team.test", "Both", ["users.manage", "access.approve@all"])
    _member("own@team.test", "Own", ["users.manage", "access.approve@own"])
    _member("approve-only@team.test", "ApproveOnly", ["access.approve@all"])
    resp = client().post("/auth/signup", data={"email": NEWBIE, "password": PASSWORD})
    assert resp.status_code == 303
    assert sent == [[ADMIN, "both@team.test", "own@team.test"]]


def test_f2_the_mailed_link_opens_for_every_recipient(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _mailed(monkeypatch)
    _member("both@team.test", "Both", ["users.manage", "access.approve@all"])
    client().post("/auth/signup", data={"email": NEWBIE, "password": PASSWORD})
    for email in sent[0]:
        assert login(email).get("/access-requests", headers=HTML).status_code == 200


def test_f2_a_users_manage_only_holder_can_still_decide_but_is_not_mailed(
        root: Path) -> None:
    """Documented limit: they act through /admin/users (Waiting pill), not /access-requests."""
    _member("manage-only@team.test", "ManageOnly", ["users.manage"])
    c = login("manage-only@team.test")
    assert "Waiting" not in c.get("/admin/users", headers=HTML).text
    uid = account(NEWBIE)
    assert "Waiting" in c.get("/admin/users", headers=HTML).text
    assert uid in [u.id for u in accounts.list_waiting()]


# --- concurrency and sessions -----------------------------------------------------------
def _race(calls: list) -> list[int]:
    gate, codes = threading.Barrier(len(calls)), [0] * len(calls)

    def run(i: int) -> None:
        gate.wait(timeout=10)
        codes[i] = calls[i]().status_code

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(calls))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return codes


def test_race_two_admins_approving_one_account_decide_it_exactly_once(root: Path) -> None:
    uid = account(NEWBIE)
    second = account("admin2@team.test", "admin")
    assert second
    one, two = login(ADMIN), login("admin2@team.test")
    tester, developer = group_id("tester"), group_id("developer")
    codes = _race([lambda: one.post(_approve(uid), data={"group_id": tester}),
                   lambda: two.post(_approve(uid), data={"group_id": developer})])
    assert sorted(codes) == [303, 400], codes
    assert len(accounts.get_user(uid).groups) == 1


def test_race_approve_against_decline_leaves_one_consistent_outcome(root: Path) -> None:
    uid = account(NEWBIE)
    account("admin2@team.test", "admin")
    one, two = login(ADMIN), login("admin2@team.test")
    codes = _race([lambda: one.post(_approve(uid), data={"group_id": group_id("tester")}),
                   lambda: two.post(_decline(uid))])
    assert sorted(codes) == [303, 400], codes
    user = accounts.get_user(uid)
    assert bool(user.groups) != user.disabled      # approved xor declined, never both


def test_a_declined_account_s_existing_session_stops_working(root: Path) -> None:
    uid = account(NEWBIE)
    session = login(NEWBIE)
    assert session.get("/auth/waiting", headers=HTML).status_code == 200   # signed in, waiting
    assert login(ADMIN).post(_decline(uid)).status_code == 303
    assert session.get("/auth/waiting", headers=HTML).status_code == 302   # sent to sign in
    assert session.get("/auth/check").status_code == 401
    assert user_id(NEWBIE) == uid

"""D-109 claim admin: while Admin/CEO has no member a signed-in account may claim it,
first claim wins, AUTOTESTER_FIRST_ADMIN_EMAIL narrows who (auth.md AU6/AU7/AU9/AU17)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login

from autotester.auth import accounts

JSON = {"accept": "application/json"}
_CLAIM = "/auth/claim-admin"


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _hosted_no_admin(monkeypatch: pytest.MonkeyPatch, *emails: str) -> list[int]:
    """A hosted server with no shell: signups join no group, so nobody is admin."""
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")
    ids = [accounts.signup(e, PASSWORD).id for e in emails]
    assert all(accounts.get_user(i).groups == [] for i in ids)
    return ids


def _actions(root: Path) -> list[str]:
    path = root / ".work" / "audit.jsonl"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]
    return [r["action"] for r in rows if "action" in r]


def test_d109_c1_hosted_first_user_sees_claim_button_and_claims_admin(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (uid,) = _hosted_no_admin(monkeypatch, "first@team.test")
    c = login("first@team.test")
    page = c.get("/auth/waiting")
    assert "Claim admin" in page.text
    assert f"action='{_CLAIM}'" in page.text and "method='post'" in page.text
    done = c.post(_CLAIM)
    assert done.status_code == 303 and done.headers["location"] == "/"
    assert accounts.get_user(uid).groups == ["Admin/CEO"]
    assert c.get("/admin/users").status_code == 200   # the account now has access


def test_d109_c1_cross_site_claim_is_refused_like_every_auth_post(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (uid,) = _hosted_no_admin(monkeypatch, "first@team.test")
    c = login("first@team.test")
    resp = c.post(_CLAIM, headers={"origin": "http://evil.test"})
    assert resp.status_code == 403
    assert accounts.get_user(uid).groups == []


def test_d109_c2_two_simultaneous_claims_make_exactly_one_admin(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ids = _hosted_no_admin(monkeypatch, "a@team.test", "b@team.test")
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def go(uid: int) -> None:
        barrier.wait()
        try:
            accounts.claim_admin(uid)
            outcomes.append("won")
        except accounts.AccountError:
            outcomes.append("refused")

    threads = [threading.Thread(target=go, args=(i,)) for i in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["refused", "won"]
    assert sorted(len(accounts.get_user(i).groups) for i in ids) == [0, 1]


def test_d109_c3_once_an_admin_exists_there_is_no_button_and_no_claim(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)                       # local first signup: Admin/CEO now has a member
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")
    late = accounts.signup("late@team.test", PASSWORD).id
    c = login("late@team.test")
    assert "Claim admin" not in c.get("/auth/waiting").text
    assert c.post(_CLAIM).status_code == 403
    assert accounts.get_user(late).groups == []
    assert "admin.claim_refused" in _actions(root)


def test_d109_c3_anonymous_and_disabled_accounts_cannot_claim(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (uid,) = _hosted_no_admin(monkeypatch, "first@team.test")
    assert client().post(_CLAIM, headers=JSON).status_code == 401
    c = login("first@team.test")
    with pytest.raises(accounts.AccountError):    # the function itself also refuses
        _disable_raw(uid)
        accounts.claim_admin(uid)
    assert c.post(_CLAIM, headers=JSON).status_code == 401   # its sessions ended with it
    assert accounts.get_user(uid).groups == []


def _disable_raw(uid: int) -> None:
    from autotester.auth import db
    with db.transaction() as conn:
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (uid,))


def test_d109_c4_with_first_admin_email_only_that_address_may_claim(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    early, boss = _hosted_no_admin(monkeypatch, "early@team.test", "boss@team.test")
    monkeypatch.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", " Boss@Team.TEST ")
    e = login("early@team.test")
    assert "Claim admin" not in e.get("/auth/waiting").text
    assert e.post(_CLAIM).status_code == 403 and accounts.get_user(early).groups == []
    b = login("boss@team.test")
    assert "Claim admin" in b.get("/auth/waiting").text
    assert b.post(_CLAIM).status_code == 303
    assert accounts.get_user(boss).groups == ["Admin/CEO"]


def test_d109_c4_local_server_unset_email_any_signed_in_account_may_claim(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (uid,) = _hosted_no_admin(monkeypatch, "any@team.test")
    monkeypatch.delenv("UVICORN_HOST")      # the same data, served locally
    c = login("any@team.test")
    assert "Claim admin" in c.get("/auth/waiting").text
    assert c.post(_CLAIM).status_code == 303
    assert accounts.get_user(uid).groups == ["Admin/CEO"]


def test_d109_c5_every_claim_attempt_is_audited_without_secrets(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _hosted_no_admin(monkeypatch, "first@team.test", "second@team.test")
    assert login("first@team.test").post(_CLAIM).status_code == 303
    assert login("second@team.test").post(_CLAIM).status_code == 403
    assert _actions(root).count("admin.claim") == 1
    assert _actions(root).count("admin.claim_refused") == 1
    assert PASSWORD not in (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")

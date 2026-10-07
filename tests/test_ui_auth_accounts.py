"""T-204 accounts: open signup with zero access, the atomic first admin, admin actions
on any account, last-admin protection and the break-glass CLI (auth.md AU6-AU9)."""

from __future__ import annotations

import re
import threading
from pathlib import Path

import pytest
from auth_harness import (
    ADMIN,
    PASSWORD,
    account,
    app_routes,
    client,
    gate_on,
    group_id,
    login,
    project,
)
from typer.testing import CliRunner

from autotester.auth import accounts, groups
from autotester.auth.access import resource_for, set_owner
from autotester.auth.db import LastAdmin
from autotester.cli import app as cli_app

JSON = {"accept": "application/json"}
_OPEN = {("GET", "/auth/login"), ("POST", "/auth/login"), ("GET", "/auth/signup"),
         ("POST", "/auth/signup"), ("GET", "/healthz"), ("POST", "/auth/logout"),
         ("GET", "/auth/waiting")}


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _routes() -> list[tuple[str, str]]:
    return [(m, re.sub(r"\{[^}]+\}", "x1", p)) for m, p in app_routes()]


def test_au6_signup_normalizes_and_validates(root: Path) -> None:
    account(ADMIN)
    c = client()
    for bad in ({"email": "not-an-email", "password": PASSWORD},
                {"email": "a@team.test", "password": "short"},
                {"email": "a@team.test", "password": "x" * 129}):
        assert c.post("/auth/signup", data=bad).status_code == 400
    ok = c.post("/auth/signup", data={"email": "  New@Team.TEST ", "password": PASSWORD})
    assert ok.status_code == 303 and ok.headers["location"] == "/auth/waiting"
    assert accounts.find_user("new@team.test") is not None


def test_au6_duplicate_signup_leaves_the_account_alone(root: Path) -> None:
    account(ADMIN)
    resp = client().post("/auth/signup", data={"email": ADMIN, "password": "other-password-9"})
    assert resp.status_code == 400
    login(ADMIN)  # the old password still works


def test_au6_zero_permission_account_reaches_only_waiting_and_logout(root: Path) -> None:
    account(ADMIN)
    account("new@team.test")
    c = login("new@team.test")
    waiting = c.get("/auth/waiting")
    assert waiting.status_code == 200 and "administrator" in waiting.text.lower()
    assert ADMIN not in waiting.text
    for method, path in _routes():
        if (method, path) in _OPEN:
            continue
        resp = c.request(method, path, headers=JSON)
        assert resp.status_code == 403, (method, path, resp.status_code)


def test_au7_first_signup_is_admin_later_ones_get_nothing(root: Path) -> None:
    assert accounts.signup(ADMIN, PASSWORD).groups == ["Admin/CEO"]
    assert accounts.signup("second@team.test", PASSWORD).groups == []


def test_au7_two_simultaneous_first_signups_make_one_admin(root: Path) -> None:
    barrier = threading.Barrier(2)
    made: list[list[str]] = []

    def go(email: str) -> None:
        barrier.wait()
        made.append(accounts.signup(email, PASSWORD).groups)

    threads = [threading.Thread(target=go, args=(f"u{i}@team.test",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(made) == [[], ["Admin/CEO"]]


def test_au7_first_admin_email_pins_who_becomes_admin(root: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", "boss@team.test")
    assert accounts.signup("early@team.test", PASSWORD).groups == []
    assert accounts.signup("boss@team.test", PASSWORD).groups == ["Admin/CEO"]


def _act(c, uid: int, action: str, **form: object):
    return c.post(f"/admin/users/{uid}/{action}", data=form)


def test_au8_admin_disables_enables_renames_and_regroups(root: Path) -> None:
    account(ADMIN)
    uid = account("t@team.test", "tester")
    admin, member = login(ADMIN), login("t@team.test")
    assert admin.get("/admin/users").status_code == 200
    assert _act(admin, uid, "disable").status_code == 303
    assert member.get("/", headers=JSON).status_code == 401
    assert client().post("/auth/login", data={"email": "t@team.test",
                                              "password": PASSWORD}).status_code == 401
    assert _act(admin, uid, "enable").status_code == 303
    assert _act(admin, uid, "name", display_name="Tess").status_code == 303
    assert accounts.get_user(uid).display_name == "Tess"
    assert _act(admin, uid, "groups", group_id=[group_id("developer")]).status_code == 303
    assert accounts.get_user(uid).groups == ["Developer"]


def test_au8_password_reset_revokes_sessions(root: Path) -> None:
    account(ADMIN)
    uid = account("t@team.test", "tester")
    member = login("t@team.test")
    assert _act(login(ADMIN), uid, "password", password="brand-new-pass-1").status_code == 303
    assert member.get("/", headers=JSON).status_code == 401
    login("t@team.test", "brand-new-pass-1")


def test_au8_delete_keeps_audit_and_unowns_projects(root: Path) -> None:
    account(ADMIN)
    uid = account("d@team.test", "developer")
    project(root, "mine")
    set_owner("mine", uid)
    admin = login(ADMIN)
    assert _act(admin, uid, "delete").status_code == 303
    assert accounts.get_user(uid) is None
    assert resource_for("mine").owner_email is None
    assert "d@team.test" in (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")


def test_au8_non_admin_gets_403_on_every_account_route(root: Path) -> None:
    account(ADMIN)
    uid = account("d@team.test", "developer")
    dev = login("d@team.test")
    assert dev.get("/admin/users").status_code == 403
    for action in ("groups", "disable", "enable", "delete", "password", "name"):
        assert _act(dev, uid, action, password="x" * 12).status_code == 403
    assert accounts.get_user(uid).groups == ["Developer"]


def test_au9_last_admin_cannot_be_locked_out(root: Path) -> None:
    uid = account(ADMIN)
    admin = login(ADMIN)
    for action, form in (("disable", {}), ("delete", {}), ("groups", {"group_id": []})):
        assert _act(admin, uid, action, **form).status_code == 400
    admin_group = groups.get_group(group_id("admin"))
    kept = [p for p in admin_group.permissions if p != "users.manage"]
    with pytest.raises(LastAdmin):
        groups.update_group(admin_group.id, admin_group.name, kept, None)
    with pytest.raises(LastAdmin):
        groups.delete_group(admin_group.id)
    me = accounts.get_user(uid)
    assert not me.disabled and me.groups == ["Admin/CEO"]
    assert "users.manage" in groups.get_group(admin_group.id).permissions


def test_au9_a_second_admin_lifts_the_guard(root: Path) -> None:
    uid = account(ADMIN)
    account("two@team.test", "admin")
    assert _act(login(ADMIN), uid, "disable").status_code == 303


def test_cli_bootstrap_admin_creates_then_resets(root: Path) -> None:
    runner = CliRunner()
    made = runner.invoke(cli_app, ["auth", "bootstrap-admin", "--email", "ops@team.test",
                                   "--password-stdin"], input=PASSWORD + "\n")
    assert made.exit_code == 0 and "created" in made.output
    account("x@team.test")
    assert accounts.find_user("ops@team.test").groups == ["Admin/CEO"]
    reset = runner.invoke(cli_app, ["auth", "bootstrap-admin", "--email", "ops@team.test",
                                    "--password-stdin"], input="another-pass-12\n")
    assert reset.exit_code == 0 and "reset" in reset.output
    assert PASSWORD not in made.output + reset.output
    login("ops@team.test", "another-pass-12")
    weak = runner.invoke(cli_app, ["auth", "bootstrap-admin", "--email", "w@team.test",
                                   "--password-stdin"], input="short\n")
    assert weak.exit_code == 2

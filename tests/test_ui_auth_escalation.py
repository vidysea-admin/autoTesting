"""T-204 fix cycle 1, part 2: no privilege escalation through users.manage / groups.manage
(P5, Umesh's safe default), the fixed first admin (D-074 (d)), nav and access-page
visibility, checkbox names, and a table pinning every route policy row.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, gate_on, group_id, login, project, team, user_id
from typer.testing import CliRunner

from autotester.auth import accounts, groups, policy
from autotester.auth.access import set_owner, set_relation
from autotester.auth.config import check_startup
from autotester.cli import app as cli_app
from autotester.schema.auth import ProjectRelation, all_permissions

JSON = {"accept": "application/json"}
HTML = {"accept": "text/html"}


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _delegate(*perms: str) -> tuple[int, int]:
    """A non-admin 'Ops' account holding exactly `perms` (the checkers' scenario)."""
    account(ADMIN)
    ops = groups.create_group("Ops", list(perms))
    uid = account("ops@team.test")
    accounts.set_user_groups(uid, [ops.id])
    return uid, ops.id


# -- P5: you can only grant what you hold, and only an admin touches Admin/CEO ------------

def test_p5_groups_manage_cannot_tick_users_manage_or_settings_into_its_own_group(
        root: Path) -> None:
    """groups.manage self-granting: Ops ticks settings.manage / users.manage / credentials.view
    into the group it belongs to. Each is refused (403), nothing is stored."""
    _, ops_id = _delegate("groups.manage")
    ops = login("ops@team.test")
    for perm in ("settings.manage", "users.manage", "credentials.view", "groups.manage"):
        resp = ops.post(f"/admin/groups/{ops_id}", data={
            "name": "Ops", "permission": ["groups.manage", perm]})
        if perm == "groups.manage":
            assert resp.status_code == 303  # already held: no new grant
            continue
        assert resp.status_code == 403, perm
    assert groups.get_group(ops_id).permissions == ["groups.manage"]


def test_p5_a_new_group_cannot_carry_more_than_its_creator_holds(root: Path) -> None:
    _delegate("groups.manage", "project.view@shared")
    ops = login("ops@team.test")
    assert ops.post("/admin/groups", data={"name": "Peek", "permission": "report.view@all"}
                    ).status_code == 403
    assert ops.post("/admin/groups", data={"name": "Wider", "permission": "project.view@all"}
                    ).status_code == 403
    assert ops.post("/admin/groups", data={"name": "Same", "permission": "project.view@shared"}
                    ).status_code == 303


def test_p5_admin_still_grants_everything(root: Path) -> None:
    account(ADMIN)
    admin = login(ADMIN)
    resp = admin.post("/admin/groups", data={"name": "Own", "permission": [
        "project.view@own", "settings.manage", "users.manage"]})
    assert resp.status_code == 303  # an @all holder covers @own, and an admin may grant keys


def test_p5_users_manage_cannot_add_itself_to_admin(root: Path) -> None:
    uid, _ = _delegate("users.manage")
    ops = login("ops@team.test")
    resp = ops.post(f"/admin/users/{uid}/groups", data={
        "group_id": [group_id("admin")]})
    assert resp.status_code == 403
    assert accounts.get_user(uid).groups == ["Ops"]


def test_p5_users_manage_cannot_hand_out_a_group_it_does_not_cover(root: Path) -> None:
    """users.manage alone adds a Tester to Developer: Developer holds more than Ops does."""
    _delegate("users.manage")
    victim = account("v@team.test")
    ops = login("ops@team.test")
    resp = ops.post(f"/admin/users/{victim}/groups", data={"group_id": [group_id("developer")]})
    assert resp.status_code == 403 and accounts.get_user(victim).groups == []


def test_p5_users_manage_cannot_reset_disable_or_delete_an_admin(root: Path) -> None:
    """The last admin's password reset by users.manage was the checkers' takeover path."""
    _delegate("users.manage")
    admin_id = user_id(ADMIN)
    ops = login("ops@team.test")
    for action, form in (("password", {"password": "attacker-pass-1"}), ("disable", {}),
                         ("delete", {}), ("groups", {"group_id": []})):
        assert ops.post(f"/admin/users/{admin_id}/{action}", data=form).status_code == 403, action
    login(ADMIN)  # the old password still works, the account is intact
    assert accounts.get_user(admin_id).groups == ["Admin/CEO"]


def test_p5_only_admin_edits_or_deletes_the_admin_group(root: Path) -> None:
    _delegate("groups.manage", "users.manage")
    ops = login("ops@team.test")
    admin_gid = group_id("admin")
    stolen = ops.post(f"/admin/groups/{admin_gid}", data={
        "name": "Admin/CEO", "permission": ["users.manage"], "members_shown": "1",
        "member_id": [user_id("ops@team.test"), user_id(ADMIN)]})
    assert stolen.status_code == 403
    assert ops.post(f"/admin/groups/{admin_gid}/delete", data={"confirm": "yes"}
                    ).status_code == 403
    assert groups.get_group(admin_gid).member_ids == [user_id(ADMIN)]


def test_p5_users_manage_still_manages_ordinary_accounts(root: Path) -> None:
    _delegate("users.manage", "project.view@shared")
    tester = account("t@team.test", "tester")
    ops = login("ops@team.test")
    assert ops.post(f"/admin/users/{tester}/disable").status_code == 303
    assert ops.post(f"/admin/users/{tester}/password", data={"password": "new-pass-12345"}
                    ).status_code == 303
    assert ops.post(f"/admin/users/{tester}/groups", data={"group_id": [group_id("tester")]}
                    ).status_code == 303  # Tester's ticks are all held by Ops


def test_p5_last_admin_protection_still_holds_for_an_admin(root: Path) -> None:
    uid = account(ADMIN)
    admin = login(ADMIN)
    assert admin.post(f"/admin/users/{uid}/delete").status_code == 400


# -- D-074 (d): the first admin is a fixed email on a hosted / non-loopback server --------

def test_d074_hosted_without_a_first_admin_email_promotes_nobody(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    assert accounts.signup("early@team.test", PASSWORD).groups == []
    assert accounts.signup("second@team.test", PASSWORD).groups == []


def test_d074_the_cli_creates_the_first_admin_when_hosted(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    made = CliRunner().invoke(cli_app, ["auth", "bootstrap-admin", "--email", "ops@team.test",
                                        "--password-stdin"], input=PASSWORD + "\n")
    assert made.exit_code == 0
    assert accounts.find_user("ops@team.test").groups == ["Admin/CEO"]


def test_d074_a_non_loopback_bind_also_promotes_nobody(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")
    assert accounts.signup("early@team.test", PASSWORD).groups == []


def test_d074_hosted_with_the_fixed_email_promotes_only_that_address(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    monkeypatch.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", "boss@team.test")
    assert accounts.signup("early@team.test", PASSWORD).groups == []
    assert accounts.signup("boss@team.test", PASSWORD).groups == ["Admin/CEO"]


def test_d074_loopback_dev_keeps_first_account_admin(root: Path) -> None:
    assert accounts.signup("dev@team.test", PASSWORD).groups == ["Admin/CEO"]


def test_d074_startup_warns_on_a_hosted_server_with_no_first_admin_email(
        root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    check_startup()
    warning = capsys.readouterr().err
    assert "AUTOTESTER_FIRST_ADMIN_EMAIL" in warning and "bootstrap-admin" in warning
    monkeypatch.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", "boss@team.test")
    check_startup()
    assert "bootstrap-admin" not in capsys.readouterr().err
    monkeypatch.delenv("AUTOTESTER_HOSTED")
    monkeypatch.delenv("AUTOTESTER_FIRST_ADMIN_EMAIL")
    check_startup()  # loopback dev: nothing to warn about
    assert "bootstrap-admin" not in capsys.readouterr().err


# -- B P7: links and pages follow the permission ------------------------------------------

def test_au25_nav_links_the_account_cannot_use_are_not_rendered(root: Path) -> None:
    users = team()
    shown = {name: c.get("/", headers=HTML).text for name, c in users.items()}
    for href in ("/onboard", "/live", "/settings/providers"):
        assert f'href="{href}"' in shown["admin"], href
    assert 'href="/onboard"' in shown["dev"] and 'href="/live"' in shown["dev"]
    assert "/settings/providers" not in shown["dev"]
    for name in ("tester", "sub"):  # a tester holds none; a sub-admin has live.view only
        assert "/onboard" not in shown[name] and "/settings/providers" not in shown[name], name
    assert "/live" not in shown["tester"]
    assert "New project" not in shown["tester"] and "New project" in shown["dev"]


def test_au13_the_access_page_lists_team_emails_only_to_those_who_manage_access(
        root: Path) -> None:
    users = team()
    project(root, "mine")
    set_owner("mine", user_id("dev@team.test"))
    set_relation("mine", user_id("sub@team.test"), ProjectRelation.ASSIGNED, True)
    set_relation("mine", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    assert users["tester"].get("/projects/mine/access").status_code == 403
    for name in ("dev", "sub", "admin"):
        page = users[name].get("/projects/mine/access")
        assert page.status_code == 200 and "tester@team.test" in page.text, name


def test_au26_every_permission_checkbox_has_a_label_and_a_name(root: Path) -> None:
    account(ADMIN)
    page = login(ADMIN).get("/admin/groups").text
    boxes = re.findall(r"<input type='checkbox' id='(perm-[^']+)' name='permission' "
                       r"value='([^']+)' aria-label='([^']+)'", page)
    assert {value for _, value, _ in boxes} == set(all_permissions())
    for box_id, value, name in boxes:
        assert f"<label for='{box_id}'" in page
        assert name.startswith(value.split("@")[0].replace(".", " ")), value


# -- B P3: every route policy row is pinned -----------------------------------------------

_P = "/projects/{slug}"
EXPECTED: dict[tuple[str, str], tuple[str, str | None]] = {
    **{("GET", p): ("public", None) for p in ("/auth/login", "/auth/signup", "/healthz")},
    **{("POST", p): ("public", None) for p in ("/auth/login", "/auth/signup")},
    ("POST", "/auth/logout"): ("session", None), ("GET", "/auth/waiting"): ("session", None),
    ("GET", "/favicon.ico"): ("member", None), ("GET", "/"): ("member", None),
    ("GET", "/onboard"): ("key", "project.create"), ("POST", "/onboard"): ("key", "project.create"),
    ("GET", "/live"): ("key", "live.view"),
    **{("GET", p): ("key", "settings.manage") for p in (
        "/settings/providers", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc")},
    ("POST", "/settings/providers"): ("key", "settings.manage"),
    ("GET", "/admin/users"): ("key", "users.manage"),
    ("POST", "/admin/users/{user_id}/{action}"): ("key", "users.manage"),
    **{(m, p): ("key", "groups.manage") for m, p in (
        ("GET", "/admin/groups"), ("POST", "/admin/groups"), ("GET", "/admin/groups/{group_id}"),
        ("POST", "/admin/groups/{group_id}"), ("POST", "/admin/groups/{group_id}/delete"))},
    **{("GET", _P + t): ("project", "project.view") for t in (
        "", "/cases/new", "/cases", "/edit", "/flowspec", "/requests", "/sources",
        "/product-map", "/flow-diagram", "/crawls", "/crawls/{crawl_id}",
        "/crawls/{crawl_id}/report.xlsx", "/issues", "/issues.xlsx",
        "/issues/{issue_id}/pin", "/env", "/access")},
    **{("GET", _P + t): ("project", "report.view") for t in (
        "/runs/{run_id}", "/report", "/report.xlsx", "/report.html")},
    ("GET", _P + "/runs/{run_id}/videos/{video_path:path}"): ("project", "video.view"),
    ("GET", _P + "/frames/{source_id}/{name:path}"): ("project", "video.view"),
    **{("POST", _P + t): ("project", "project.edit") for t in (
        "/cases", "/cases/{case_id}/rename", "/cases/{case_id}/delete", "/edit", "/login-case",
        "/flowspec/approve", "/flowspec/request-edit", "/cases/generate",
        "/crawls/{crawl_id}/merge", "/issues/{issue_id}/pin", "/sources",
        "/sources/{source_id}/analyze", "/env/url")},
    ("POST", _P + "/sources/upload"): ("project", "video.upload"),
    **{("POST", _P + t): ("project", "project.run") for t in ("/run", "/explore",
                                                                "/crawl-approval")},
    **{("POST", _P + t): ("project", "credentials.edit") for t in (
        "/secrets", "/secrets/{key}/delete", "/env", "/env/add")},
    ("POST", _P + "/access"): ("project", "project.view"),
}


def test_au14_every_policy_row_requires_exactly_its_pinned_key() -> None:
    """A row quietly downgraded (/onboard to member, /openapi.json to member, the credentials
    group to project.view) must turn this red: the policy table is the whole defence on
    routes whose handler does not re-check."""
    actual = {row: (rule.kind, rule.key.value if rule.key else None)
              for row, rule in policy.ROUTE_POLICY.items()}
    assert actual == EXPECTED

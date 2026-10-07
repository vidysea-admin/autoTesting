"""T-204 groups and permissions: additive checkbox groups, seeding once, the single
`authorize()` and its scopes, visibility without existence leaks, and default deny for
routes (qa/contracts/auth.md AU10-AU14)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from auth_harness import (
    ADMIN,
    account,
    app_routes,
    gate_on,
    group_id,
    login,
    project,
    team,
    user_id,
)

from autotester.auth import accounts, db, groups, policy
from autotester.auth.access import authorize, set_owner, set_relation
from autotester.auth.defaults import DEFAULT_GROUPS
from autotester.schema.auth import PermissionKey, Principal, ProjectRelation, ResourceRef
from autotester.ui.app import app

JSON = {"accept": "application/json"}
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


# -- AU12: one function; table over the four default groups x relations ----------

ME = "me@team.test"
RELATIONS = {
    "owner": ResourceRef(project_slug="p", owner_email=ME),
    "assigned": ResourceRef(project_slug="p", owner_email="x@t.test", assignees=frozenset({ME})),
    "shared": ResourceRef(project_slug="p", owner_email="x@t.test", shared_with=frozenset({ME})),
    "none": ResourceRef(project_slug="p", owner_email="x@t.test"),
    "legacy": ResourceRef(project_slug="p"),
}
EXPECT_VIEW = {"admin": set(RELATIONS), "sub-admin": {"assigned"},
               "developer": {"owner", "shared"}, "tester": {"shared"}}
EXPECT_EDIT = {"admin": set(RELATIONS), "sub-admin": {"assigned"},
               "developer": {"owner"}, "tester": set()}


@pytest.mark.parametrize("seed", list(DEFAULT_GROUPS))
@pytest.mark.parametrize("relation", list(RELATIONS))
def test_au12_scope_table(seed: str, relation: str) -> None:
    who = Principal(user_id=1, email=ME, permissions=frozenset(DEFAULT_GROUPS[seed][1]))
    res = RELATIONS[relation]
    assert authorize(who, PermissionKey.PROJECT_VIEW, res) == (relation in EXPECT_VIEW[seed])
    assert authorize(who, PermissionKey.PROJECT_EDIT, res) == (relation in EXPECT_EDIT[seed])
    assert authorize(who, PermissionKey.CREDENTIALS_VIEW) == (seed == "admin")


def test_au12_no_route_compares_group_names() -> None:
    patterns = [arg for name, _ in DEFAULT_GROUPS.values() for arg in ("-e", name)]
    found = subprocess.run(["git", "grep", "--untracked", "-n", "-w", "-F", *patterns,
                            "--", str(SRC / "ui")], capture_output=True, text=True)
    assert found.stdout == ""


# -- AU10 / AU11 ------------------------------------------------------------------

def test_au10_union_and_untick(root: Path) -> None:
    account(ADMIN)
    a = groups.create_group("Viewers", ["live.view"])
    b = groups.create_group("Settings", ["settings.manage"])
    uid = account("u@team.test")
    accounts.set_user_groups(uid, [a.id, b.id])
    c = login("u@team.test")
    assert c.get("/live", headers=JSON).status_code == 200
    assert c.get("/settings/providers", headers=JSON).status_code == 200
    admin = login(ADMIN)
    resp = admin.post(f"/admin/groups/{a.id}", data={"name": "Viewers", "permission": []})
    assert resp.status_code == 303
    assert c.get("/live", headers=JSON).status_code == 403
    assert c.get("/settings/providers", headers=JSON).status_code == 200


@pytest.mark.parametrize("bad", ["users.manage@own", "made.up", "project.view@everyone"])
def test_au10_unknown_key_or_scope_stores_nothing(root: Path, bad: str) -> None:
    account(ADMIN)
    gid = group_id("tester")
    before = groups.get_group(gid)
    resp = login(ADMIN).post(f"/admin/groups/{gid}",
                             data={"name": "Tester", "permission": ["live.view", bad]})
    assert resp.status_code == 400
    assert groups.get_group(gid) == before
    assert login(ADMIN).post("/admin/groups", data={"name": "X", "permission": [bad]}
                             ).status_code == 400
    assert "X" not in {g.name for g in groups.list_groups()}


def test_au10_form_is_labelled_checkboxes(root: Path) -> None:
    account(ADMIN)
    page = login(ADMIN).get(f"/admin/groups/{group_id('tester')}").text
    assert page.count("type='checkbox'") + page.count('type="checkbox"') >= 19
    assert "<label" in page


def test_au10_delete_in_use_group_warns_first(root: Path) -> None:
    account(ADMIN)
    uid = account("u@team.test", "tester")
    admin = login(ADMIN)
    gid = group_id("tester")
    warn = admin.post(f"/admin/groups/{gid}/delete")
    assert warn.status_code == 200 and "1" in warn.text
    assert groups.get_group(gid) is not None
    assert admin.post(f"/admin/groups/{gid}/delete", data={"confirm": "yes"}).status_code == 303
    assert groups.get_group(gid) is None
    assert accounts.get_user(uid).groups == []


def test_au10_group_edit_route_cannot_escalate(root: Path) -> None:
    """Security mutant target: a developer, and a groups.manage holder without
    users.manage, both try to put themselves into Admin/CEO through the group form."""
    account(ADMIN)
    admin_gid = group_id("admin")
    editors = groups.create_group("Editors", ["groups.manage"])
    ed = account("ed@team.test")
    accounts.set_user_groups(ed, [editors.id])
    dev = account("dev@team.test", "developer")
    before = groups.get_group(admin_gid)
    for email, uid in (("dev@team.test", dev), ("ed@team.test", ed)):
        login(email).post(f"/admin/groups/{admin_gid}", data={
            "name": before.name, "permission": before.permissions, "members_shown": "1",
            "member_id": [uid, *before.member_ids]})
        assert uid not in groups.get_group(admin_gid).member_ids, email
    assert login("dev@team.test").post(f"/admin/groups/{admin_gid}", data={
        "name": before.name, "permission": before.permissions}).status_code == 403


def test_au11_seeded_once_edits_survive_restart(root: Path) -> None:
    account(ADMIN)
    seeded = {g.seed: sorted(g.permissions) for g in groups.list_groups()}
    assert seeded == {s: sorted(p) for s, (_, p) in DEFAULT_GROUPS.items()}
    tester = group_id("tester")
    groups.update_group(tester, "Tester", ["live.view"], None)
    groups.delete_group(group_id("developer"))
    db._READY.clear()  # a restart: the next connect re-runs init
    after = {g.seed: g.permissions for g in groups.list_groups()}
    assert after.get("tester") == ["live.view"] and "developer" not in after


# -- AU13: visibility and existence ----------------------------------------------

def test_au13_four_users_two_projects(root: Path) -> None:
    project(root, "alpha")
    project(root, "beta")
    users = team()
    set_owner("alpha", user_id("dev@team.test"))
    set_relation("alpha", user_id("sub@team.test"), ProjectRelation.ASSIGNED, True)
    set_relation("beta", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    sees = {"admin": {"alpha", "beta"}, "sub": {"alpha"}, "dev": {"alpha"},
            "tester": {"beta"}}
    for name, c in users.items():
        home = c.get("/").text
        for slug in ("alpha", "beta"):
            direct = c.get(f"/projects/{slug}")
            if slug in sees[name]:
                assert direct.status_code == 200 and f"/projects/{slug}" in home, (name, slug)
            else:
                missing = c.get("/projects/nope")
                assert direct.status_code == 404 == missing.status_code, (name, slug)
                assert direct.text.replace(slug, "") == missing.text.replace("nope", "")
                assert f"/projects/{slug}'" not in home and f'/projects/{slug}"' not in home


def test_au13_visible_without_the_action_is_403(root: Path) -> None:
    project(root, "beta")
    users = team()
    set_relation("beta", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    assert users["tester"].post("/projects/beta/run", headers=JSON).status_code == 403


# -- AU14: default deny ------------------------------------------------------------

def test_au14_every_route_has_a_policy_row() -> None:
    served = app_routes()
    assert len(served) > 60
    assert [pair for pair in served if pair not in policy.ROUTE_POLICY] == []


def test_au14_an_undeclared_route_is_refused(root: Path) -> None:
    account(ADMIN)

    @app.get("/zz-undeclared")
    def _undeclared() -> dict[str, bool]:
        return {"reached": True}

    try:
        assert ("GET", "/zz-undeclared") not in policy.ROUTE_POLICY
        assert login(ADMIN).get("/zz-undeclared", headers=JSON).status_code == 403
    finally:
        app.router.routes[:] = [r for r in app.router.routes
                                if getattr(r, "path", "") != "/zz-undeclared"]

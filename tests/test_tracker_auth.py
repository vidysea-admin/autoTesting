"""T-199 TB7: the tracker behind T-204's login gate -- scope table over the four default groups,
not-found without scope, 403 on the assignee edit without project.edit, no session -> refused."""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import ADMIN, client, gate_on, project, team, user_id
from bug_loop_fixture import event, seed

from autotester.auth import policy
from autotester.auth.access import set_owner, set_relation
from autotester.core.paths import ProjectPaths
from autotester.schema.auth import PermissionKey as K
from autotester.schema.auth import ProjectRelation
from autotester.schema.tracked_bug import EventKind
from autotester.store.bug_store import BugStore
from autotester.ui.routes_tracker import router

JSON = {"accept": "application/json"}
EMAIL = {"sub": "sub@team.test", "dev": "dev@team.test", "tester": "tester@team.test"}
LIST = "/projects/demo/tracker"
VIEW = {"admin": {"own", "assigned", "shared", "none"}, "sub": {"assigned"},
        "dev": {"own", "shared"}, "tester": {"shared"}}
EDIT = {"admin": {"own", "assigned", "shared", "none"}, "sub": {"assigned"},
        "dev": {"own"}, "tester": set()}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    users = team()
    for slug in ("demo", "other"):
        project(root, slug)
    store = BugStore(ProjectPaths("demo", root).dir)
    store.apply(event(EventKind.FAIL, 1,
                      seed_obj=seed("case_aaaaaaaaaaaa", "C1", "Checkout fails")))
    return users, next(iter(store.bugs())), root


def _relate(relation: str) -> None:
    """Put the dev, sub and tester users in `relation` to project demo."""
    dev, sub, tester = (user_id(EMAIL[n]) for n in ("dev", "sub", "tester"))
    if relation == "own":
        set_owner("demo", dev)
    elif relation == "assigned":
        set_relation("demo", sub, ProjectRelation.ASSIGNED, True)
    elif relation == "shared":
        set_relation("demo", tester, ProjectRelation.SHARED, True)
        set_relation("demo", dev, ProjectRelation.SHARED, True)


@pytest.mark.parametrize("relation", ["own", "assigned", "shared", "none"])
@pytest.mark.parametrize("who", ["admin", "sub", "dev", "tester"])
def test_scope_table_list_evidence_and_assignee_edit(world, who: str, relation: str) -> None:
    users, key, root = world
    _relate(relation)
    c = users[who]
    visible = c.get(LIST, headers=JSON)
    export = c.get(LIST + "/export.csv", headers=JSON)
    detail = c.get(f"{LIST}/{key}", headers=JSON)
    posted = c.post(f"{LIST}/{key}/assignee", data={"assignee": "priya"}, headers=JSON)
    if relation in VIEW[who]:
        assert visible.status_code == export.status_code == detail.status_code == 200
        assert "Checkout fails" in visible.text
    else:  # AU13: the same 404 as a project that does not exist, on every route
        assert visible.status_code == export.status_code == detail.status_code == 404
    store = BugStore(ProjectPaths("demo", root).dir)
    if relation in EDIT[who]:
        assert posted.status_code == 303
        assert store.get(key).assignee == "priya"
    else:
        assert posted.status_code == (403 if relation in VIEW[who] else 404)
        assert store.get(key).assignee is None  # value unchanged


def test_edit_form_only_shown_to_a_holder_of_project_edit(world) -> None:
    users, key, _root = world
    _relate("shared")
    assert "name='assignee'" not in users["tester"].get(f"{LIST}/{key}").text
    assert "name='assignee'" in users["admin"].get(f"{LIST}/{key}").text


def test_assignee_edit_accepts_free_text_clears_and_records_the_actor(world) -> None:
    users, key, root = world
    admin = users["admin"]
    admin.post(f"{LIST}/{key}/assignee", data={"assignee": "  vendor contact  "})
    store = BugStore(ProjectPaths("demo", root).dir)
    assert store.get(key).assignee == "vendor contact"
    assert store.history(key)[-1].actor == f"user:{ADMIN}"
    admin.post(f"{LIST}/{key}/assignee", data={"assignee": ""})
    assert store.get(key).assignee is None
    assert admin.post(f"{LIST}/{key}/assignee", data={"assignee": "x" * 200}).status_code == 400
    assert admin.post(f"{LIST}/nope/assignee", data={"assignee": "a"}).status_code == 404


def test_no_session_is_refused_including_the_evidence_link(world) -> None:
    _users, key, _root = world
    anon = client()
    for path in (LIST, f"{LIST}/{key}", LIST + "/export.xlsx", "/projects/demo/runs/run1"):
        assert anon.get(path, headers=JSON).status_code == 401
        assert anon.get(path, headers={"accept": "text/html"}).status_code == 302
    assert anon.post(f"{LIST}/{key}/assignee", data={"assignee": "a"},
                     headers=JSON).status_code == 401


def test_tracker_routes_are_guarded_in_the_central_policy() -> None:
    served = {(m, r.path) for r in router.routes for m in r.methods}
    assert served
    for pair in served:
        rule = policy.ROUTE_POLICY[pair]
        assert rule.kind == "project"
        assert rule.key is (K.PROJECT_EDIT if pair[0] == "POST" else K.REPORT_VIEW)


def test_unknown_project_never_leaks_for_a_signed_in_user(world) -> None:
    users, _key, _root = world
    assert users["dev"].get("/projects/ghost/tracker", headers=JSON).status_code == 404


def test_project_page_links_the_tracker_only_for_report_view_holders(world) -> None:
    users, _key, _root = world
    _relate("shared")  # tester and dev hold report.view on demo; sub has no relation
    link = "href='/projects/demo/tracker'"
    assert link in users["tester"].get("/projects/demo").text
    assert link in users["admin"].get("/projects/demo").text
    assert link not in users["sub"].get("/projects/demo").text


def test_tracker_filter_selects_have_accessible_names(world) -> None:
    from test_ui_onboard_a11y import unlabelled_controls
    users, _key, _root = world
    page = users["admin"].get(LIST).text
    assert page.count("<select") == 2
    assert unlabelled_controls(page) == []

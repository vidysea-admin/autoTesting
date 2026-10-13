"""TT1 (CRITICAL): the Test button is authenticated, authorised, Origin-checked, and a refusal
leaves no trace -- no queue entry, no run directory, no browser, no grader call.

Scenarios: an anonymous visitor, a Tester who may only read, a Developer pressing on someone
else's project, a cross-origin page riding a valid session, a mistyped slug, a stray GET; then
the four default groups against their own / assigned / shared / unrelated project.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import ADMIN, account, client, gate_on, team, user_id
from team_run_fakes import FakeQueue, listing, patch_run_world, runnable_project

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.ui import routes_team_run

HTML = {"accept": "text/html"}


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    counters = patch_run_world(monkeypatch)
    queue = FakeQueue()
    monkeypatch.setattr(routes_team_run, "get_queue", lambda: queue)
    runnable_project(root, "alpha", approved=True)
    runnable_project(root, "beta", approved=True)
    return root, counters, queue


def _no_trace(root, counters, queue, before) -> None:
    assert listing(root) == before            # no run dir, no queue file, no approval row
    assert queue.entries == [] and queue.submitted == []
    assert counters.sessions == 0 and counters.graded == 0


def test_anonymous_press_goes_to_login_and_leaves_no_trace(world) -> None:
    root, counters, queue = world
    account(ADMIN)
    before = listing(root)
    resp = client().post("/projects/alpha/test", headers=HTML)
    assert resp.status_code == 302 and resp.headers["location"].startswith("/auth/login")
    _no_trace(root, counters, queue, before)


def test_a_signed_in_user_without_project_run_gets_403_naming_it(world) -> None:
    root, counters, queue = world
    users = team()
    set_relation("alpha", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    before = listing(root)
    resp = users["tester"].post("/projects/alpha/test", headers=HTML)
    assert resp.status_code == 403 and "project.run" in resp.text
    _no_trace(root, counters, queue, before)


def test_a_project_the_user_cannot_see_is_the_same_404_as_a_missing_one(world) -> None:
    root, counters, queue = world
    users = team()
    set_owner("alpha", user_id("dev@team.test"))      # beta belongs to nobody the dev knows
    before = listing(root)
    hidden = users["dev"].post("/projects/beta/test", headers=HTML)
    missing = users["dev"].post("/projects/nope/test", headers=HTML)
    assert hidden.status_code == 404 == missing.status_code
    assert hidden.text.replace("beta", "") == missing.text.replace("nope", "")
    _no_trace(root, counters, queue, before)


def test_a_cross_origin_post_with_a_valid_session_is_refused_by_the_origin_guard(world) -> None:
    root, counters, queue = world
    users = team()
    before = listing(root)
    resp = users["admin"].post("/projects/alpha/test", headers={"origin": "https://evil.example"})
    assert resp.status_code == 403
    _no_trace(root, counters, queue, before)


def test_an_unknown_slug_is_404_even_for_an_admin(world) -> None:
    root, counters, queue = world
    users = team()
    before = listing(root)
    assert users["admin"].post("/projects/nope/test", headers=HTML).status_code == 404
    _no_trace(root, counters, queue, before)


def test_a_get_to_the_press_route_changes_nothing(world) -> None:
    root, counters, queue = world
    users = team()
    before = listing(root)
    assert users["admin"].get("/projects/alpha/test", headers=HTML).status_code == 405
    assert client().get("/projects/alpha/test", headers=HTML).status_code == 302
    _no_trace(root, counters, queue, before)


def test_the_handler_checks_permission_before_anything_else_even_without_the_login_gate(
        world, monkeypatch: pytest.MonkeyPatch) -> None:
    """The route is safe on its own: called with the gate's decision removed, a principal with
    no project.run is still refused before the queue is touched."""
    from fastapi import HTTPException

    from autotester.auth.context import CURRENT_PRINCIPAL
    from autotester.schema.auth import Principal

    _root, _counters, queue = world
    account(ADMIN)
    who = Principal(user_id=99, email="nobody@team.test",
                    permissions=frozenset({"project.view@all"}))
    token = CURRENT_PRINCIPAL.set(who)
    try:
        with pytest.raises(HTTPException) as refused:
            routes_team_run.press_test("alpha")
    finally:
        CURRENT_PRINCIPAL.reset(token)
    assert refused.value.status_code == 403 and "project.run" in refused.value.detail
    assert queue.submitted == []


# group x project relation -> the status a press gets (303 = queued, 403 = seen but not allowed,
# 404 = not visible); the default groups of auth.md AU11
TABLE = {
    "admin": {"own": 303, "assigned": 303, "shared": 303, "other": 303},
    "sub": {"own": 404, "assigned": 303, "shared": 404, "other": 404},
    "dev": {"own": 303, "assigned": 404, "shared": 403, "other": 404},
    "tester": {"own": 404, "assigned": 404, "shared": 403, "other": 404},
}
RELATION = {"own": None, "assigned": ProjectRelation.ASSIGNED, "shared": ProjectRelation.SHARED}


@pytest.mark.parametrize("group", sorted(TABLE))
def test_default_groups_against_own_assigned_shared_and_unrelated_projects(
        world, group: str) -> None:
    root, counters, queue = world
    users = team()
    uid = user_id(f"{group}@team.test")
    for relation, expected in TABLE[group].items():
        slug = f"{group}-{relation}".replace("_", "-")
        runnable_project(root, slug, approved=True)
        if relation == "own":
            set_owner(slug, uid)
        elif relation != "other":
            set_relation(slug, uid, RELATION[relation], True)
        got = users[group].post(f"/projects/{slug}/test", headers=HTML)
        assert got.status_code == expected, (group, relation, got.status_code)
        if expected == 303:
            assert got.headers["location"].startswith(f"/projects/{slug}/test/")
        else:
            assert slug not in {e.project for e in queue.entries}
            if expected == 403:
                assert "project.run" in got.text
    assert counters.sessions == 0 and counters.graded == 0     # a press queues, never runs

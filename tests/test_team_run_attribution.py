"""TT3: a run is attributable to the person who pressed Test -- from the session, never the request.

Scenarios: two teammates press Test on one project; each queue entry, saved `Run` and report
header names its own presser; a request that carries `requested_by` / `user` / `email` / `owner`
in its query or body cannot name someone else; a run.json written before this unit still loads.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import gate_on, login, team, user_id
from team_run_fakes import patch_run_world, runnable_project

from autotester.auth.access import set_owner
from autotester.schema.enums import Trigger
from autotester.schema.run import Run
from autotester.schema.team_enums import RunVia
from autotester.ui.run_queue import get_queue

HTML = {"accept": "text/html"}
GOLDEN = Path(__file__).parent / "golden" / "run_pre_t205.json"
FORGED = {"requested_by": "mallory@evil.test", "user": "mallory@evil.test",
          "email": "mallory@evil.test", "owner": "mallory@evil.test"}


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    patch_run_world(monkeypatch)        # the autouse inline queue runs the job inside the press
    users = team()
    store = runnable_project(root, "alpha", approved=True)
    set_owner("alpha", user_id("dev@team.test"))
    return users, store


def _press(client, **extra) -> str:
    resp = client.post("/projects/alpha/test", headers=HTML, params=extra, data=extra)
    assert resp.status_code == 303, resp.text
    return resp.headers["location"].rsplit("/", 1)[1]


def test_two_teammates_each_get_their_own_name_on_entry_run_and_report(world) -> None:
    users, store = world
    first = _press(users["dev"])
    second = _press(users["admin"])
    assert first != second
    entries = {e.id: e for e in get_queue().snapshot("alpha")}
    assert entries[first].requested_by == "dev@team.test"
    ids = {"dev@team.test": user_id("dev@team.test"), "admin@team.test": user_id("admin@team.test")}
    assert ids["dev@team.test"] != ids["admin@team.test"]
    assert entries[first].requested_by_id == ids["dev@team.test"]
    assert entries[second].requested_by_id == ids["admin@team.test"]
    assert entries[second].requested_by == "admin@team.test"
    for run_id, who in ((first, "dev@team.test"), (second, "admin@team.test")):
        run = store.load_run(run_id)
        assert run is not None
        assert (run.requested_by, run.via, run.trigger) == (
            who, RunVia.TEAM_BUTTON, Trigger.MANUAL)
        assert run.requested_at is not None and run.requested_by_id == ids[who]
        assert entries[run_id].via is RunVia.TEAM_BUTTON and entries[run_id].trigger == "button"
        page = users["admin"].get(f"/projects/alpha/runs/{run_id}").text
        assert f"Started by <strong>{who}</strong> (user #{ids[who]})" in page
        assert "with the Test button" in page


def test_a_forged_requested_by_in_the_query_or_body_is_ignored(world) -> None:
    users, store = world
    run_id = _press(users["dev"], **FORGED)
    run = store.load_run(run_id)
    assert run is not None and run.requested_by == "dev@team.test"
    assert run.requested_by_id == user_id("dev@team.test")
    assert get_queue().snapshot("alpha")[0].requested_by == "dev@team.test"
    assert "mallory" not in users["dev"].get(f"/projects/alpha/runs/{run_id}").text


def test_a_run_json_written_before_this_unit_still_loads() -> None:
    run = Run.model_validate_json(GOLDEN.read_text(encoding="utf-8"))
    assert (run.requested_by, run.requested_by_id) == (None, None)
    assert run.requested_at is None and run.via is None
    assert run.trigger is Trigger.MANUAL


def test_a_report_with_no_recorded_presser_has_no_started_by_line(world) -> None:
    _users, store = world
    store.save_run(Run(id="run-old", project="alpha"))
    assert "Started by" not in login("admin@team.test").get("/projects/alpha/runs/run-old").text

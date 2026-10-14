"""TA6: the Test button runs the real queue and launcher and the report reaches the right people,
once. Rows (a), (b), (e) run today; the mail rows (c), (d) and the "Email me run reports" tick are
recorded as DEFERRED rows in the runbook (D-092/D-093), not tests."""

from __future__ import annotations

import pytest
from rig import CANARY_SECRET, CRED_KEY, HTML, SLUG, World, press

from autotester.schema.enums import Trigger
from autotester.schema.team_enums import RunVia
from autotester.ui import run_queue


def _held_queue(monkeypatch: pytest.MonkeyPatch) -> list:
    jobs: list = []
    monkeypatch.setattr("autotester.ui.run_queue._QUEUE", run_queue.RunQueue(
        spawn=jobs.append, runner=run_queue._registered_runner))
    return jobs


def test_a_one_request_attributed_to_dev_and_a_second_press_returns_it(
        world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    jobs = _held_queue(monkeypatch)
    first = press(world, "dev")
    second = press(world, "dev")
    other_user = press(world, "admin")           # same project, another person: same request
    assert first == second == other_user
    [entry] = run_queue.get_queue().snapshot(SLUG)
    assert entry.requested_by == "dev@team.test" and entry.trigger == "button"
    for job in jobs:
        job()
    assert len(list((world.store().paths.runs_dir).glob("run-*"))) == 1


def test_b_the_run_goes_through_the_one_launcher_and_the_report_opens_for_the_right_people(
        world: World) -> None:
    run_id = press(world, "dev")
    run = world.store().load_run(run_id)
    assert run is not None
    assert (run.trigger, run.via, run.requested_by) == (
        Trigger.MANUAL, RunVia.TEAM_BUTTON, "dev@team.test")
    assert world.graded_log == [f"{run_id}:FAIL"]
    assert world.counters.graded == 1
    for who in ("dev", "admin"):
        page = world.users[who].get(f"/projects/{SLUG}/runs/{run_id}", headers=HTML)
        assert page.status_code == 200
    tester = world.users["tester"].get(f"/projects/{SLUG}/runs/{run_id}", headers=HTML)
    assert tester.status_code in (403, 404)
    pending = world.users["pending"].get(f"/projects/{SLUG}/runs/{run_id}", headers=HTML)
    assert pending.status_code != 200


def test_e_a_missing_credential_pair_refuses_naming_the_credentials_and_leaves_no_run(
        world: World) -> None:
    (world.root / ".env").write_text("", encoding="utf-8")        # the declared key has no value
    before = world.snapshot()
    resp = world.users["dev"].post(f"/projects/{SLUG}/test")
    assert resp.status_code == 400
    assert CRED_KEY in resp.text and "Credentials page" in resp.text
    assert CANARY_SECRET not in resp.text
    assert world.snapshot() == before
    assert world.counters.sessions == 0 and world.counters.graded == 0


def test_tt7_the_inbox_lists_the_report_for_dev_and_admin_but_not_tester(world: World) -> None:
    run_id = press(world, "dev")
    for role in ("dev", "admin"):
        page = world.users[role].get("/inbox", headers=HTML)
        assert page.status_code == 200 and run_id in page.text, role
    seen = world.users["tester"].get("/inbox", headers=HTML)
    assert run_id not in seen.text

"""TT5 (CRITICAL): the button enqueues and never bypasses the queue.

Scenarios: two teammates press Test on one project (one entry, the same page); three projects
against a cap of 2 (never more than 2 running, never two of one project); a press never starts
a browser or the launcher from the request; the button's own files hold no cap logic.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from auth_harness import gate_on, team, user_id
from team_run_fakes import FakeQueue, patch_run_world, runnable_project

from autotester.auth.access import set_owner
from autotester.schema.run_queue import QueueEntry, QueueStatus
from autotester.stages import run_launcher
from autotester.ui import routes_team_run, run_queue
from autotester.ui.run_queue import RunQueue

HTML = {"accept": "text/html"}
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester" / "ui"


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    counters = patch_run_world(monkeypatch)
    users = team()
    for slug in ("alpha", "beta", "gamma"):
        runnable_project(root, slug, approved=True)
        set_owner(slug, user_id("dev@team.test"))

    def never(*args, **kwargs):
        raise AssertionError("a press must not start the launcher from the request")

    monkeypatch.setattr(run_launcher, "launch_run", never)
    return users, counters, monkeypatch


def test_a_second_press_returns_the_existing_request_not_a_second_entry(world) -> None:
    users, counters, monkeypatch = world
    queue = FakeQueue()
    monkeypatch.setattr(routes_team_run, "get_queue", lambda: queue)
    first = users["dev"].post("/projects/alpha/test", headers=HTML)
    second = users["admin"].post("/projects/alpha/test", headers=HTML)      # someone else
    assert first.status_code == second.status_code == 303
    assert first.headers["location"] == second.headers["location"]
    assert len(queue.entries) == 1 and len(queue.submitted) == 1
    queue.start_next()                                  # now `running`: still the same request
    third = users["dev"].post("/projects/alpha/test", headers=HTML)
    assert third.headers["location"] == first.headers["location"] and len(queue.entries) == 1
    queue.finish(queue.entries[0].id)                   # finished: a new press is a new request
    fourth = users["dev"].post("/projects/alpha/test", headers=HTML)
    assert fourth.headers["location"] != first.headers["location"] and len(queue.entries) == 2
    assert counters.sessions == 0


def test_three_projects_against_a_cap_of_two_never_exceed_it(world) -> None:
    users, counters, monkeypatch = world
    jobs: list[Callable[[], None]] = []
    seen: list[tuple[int, int]] = []

    def runner(entry: QueueEntry) -> None:
        snap = run_queue.get_queue().snapshot()
        running = [e for e in snap if e.status is QueueStatus.RUNNING]
        seen.append((len(running), len({e.project for e in running})))

    queue = RunQueue(limit=lambda: 2, runner=runner, spawn=jobs.append)
    monkeypatch.setattr(run_queue, "_QUEUE", queue)
    for slug in ("alpha", "beta", "gamma"):
        assert users["dev"].post(f"/projects/{slug}/test", headers=HTML).status_code == 303
    states = sorted(e.status.value for e in queue.snapshot())
    assert states == ["queued", "running", "running"]
    while jobs:
        jobs.pop(0)()
    assert seen and all(n <= 2 and n == distinct for n, distinct in seen)
    assert {e.status for e in queue.snapshot()} == {QueueStatus.DONE}
    assert counters.sessions == 0 and counters.graded == 0       # the fake runner ran nothing real


def test_the_button_files_hold_no_cap_logic_and_no_way_to_start_a_run() -> None:
    for name in ("routes_team_run.py", "team_run_view.py"):
        text = (SRC / name).read_text(encoding="utf-8")
        assert "max_concurrent_runs" not in text, name
        assert "set_runner" not in text and "_registered_runner" not in text, name

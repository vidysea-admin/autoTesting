"""TT2: the Test button is a request, not a run -- 303 at once, a status page that follows the
persisted queue entry (queued with its place, running, done / failed / refused / interrupted),
readable without the worker, and a button shown only to someone who may press it.

Scenarios: a developer presses Test while another project holds the only run slot, watches the
page, reloads it after the server object was rebuilt; a gate refusing at start; a worker that
crashed; a server restart in the middle of a run.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from auth_harness import gate_on, team, user_id
from team_run_fakes import patch_run_world, runnable_project

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.run import Run
from autotester.schema.run_queue import QueueEntry
from autotester.store.project_store import ProjectStore
from autotester.ui import run_queue
from autotester.ui.run_queue import RunQueue, RunRefused

HTML = {"accept": "text/html"}
WORDS = {"queued": "Position in the line", "running": "The run is in progress",
         "done": "Open the report", "failed": "stopped on an error",
         "refused": "A gate said no", "interrupted": "server stopped"}


def wait_for(check: Callable[[], bool], what: str, seconds: float = 5.0) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for {what}")


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    counters = patch_run_world(monkeypatch)
    users = team()
    gates = {slug: (threading.Event(), threading.Event()) for slug in ("alpha", "beta")}

    def runner(entry: QueueEntry) -> None:          # blocks until the test lets it finish
        started, release = gates[entry.project]
        started.set()
        assert release.wait(5), "the test never released this run"

    def make() -> RunQueue:
        return RunQueue(limit=lambda: 1, runner=runner,
                        spawn=lambda job: threading.Thread(target=job, daemon=True).start(),
                        path=lambda: root / ".work" / "queue-test.json")

    queue = make()
    monkeypatch.setattr(run_queue, "_QUEUE", queue)
    for slug in gates:
        runnable_project(root, slug, approved=True)
        set_owner(slug, user_id("dev@team.test"))
    return users["dev"], users, gates, counters, make, monkeypatch


def _status(client, location: str) -> str:
    resp = client.get(location, headers=HTML)
    assert resp.status_code == 200, resp.text
    return resp.text


def test_a_press_returns_at_once_and_the_page_follows_queued_running_done(world) -> None:
    dev, _users, gates, counters, make, monkeypatch = world
    first = dev.post("/projects/beta/test", headers=HTML)          # takes the only slot
    wait_for(gates["beta"][0].is_set, "beta to start")

    began = time.perf_counter()
    second = dev.post("/projects/alpha/test", headers=HTML)        # has to wait behind beta
    elapsed = time.perf_counter() - began

    assert first.status_code == second.status_code == 303
    assert elapsed < 2.0 and counters.sessions == 0       # the press only queued; no browser
    where = second.headers["location"]
    assert where.startswith("/projects/alpha/test/run-")
    queued = _status(dev, where)
    assert WORDS["queued"] in queued and "#1" in queued
    assert "http-equiv='refresh'" in queued                # keeps itself fresh while waiting

    gates["beta"][1].set()                                 # beta finishes, alpha gets the slot
    wait_for(gates["alpha"][0].is_set, "alpha to start")
    assert WORDS["running"] in _status(dev, where)
    gates["alpha"][1].set()
    wait_for(lambda: WORDS["done"] in _status(dev, where), "alpha to be done")
    done = _status(dev, where)
    assert f"/projects/alpha/runs/{where.rsplit('/', 1)[1]}" in done
    assert "http-equiv='refresh'" not in done              # finished: no more reloading

    # readable without the worker: the server object is rebuilt, the page still renders
    rebuilt = make()
    rebuilt.recover()
    monkeypatch.setattr(run_queue, "_QUEUE", rebuilt)
    assert WORDS["done"] in _status(dev, where)


def test_the_page_shows_a_refusal_a_crash_and_a_restart_with_their_reasons(world) -> None:
    dev, _users, _gates, _counters, _make, monkeypatch = world
    jobs: list[Callable[[], None]] = []
    outcome: list[Exception] = []

    def runner(entry: QueueEntry) -> None:
        raise outcome.pop(0)

    queue = RunQueue(limit=lambda: 3, runner=runner, spawn=jobs.append,
                     path=lambda: Path(run_queue._queue_file().parent / "q2.json"))
    monkeypatch.setattr(run_queue, "_QUEUE", queue)
    expected = {}
    for slug, error, status in (
            ("alpha", RunRefused("DEMO_USER has no value yet. Enter it on the Credentials page"),
             "refused"),
            ("beta", RuntimeError("boom with a secret-ish detail"), "failed")):
        outcome.append(error)
        location = dev.post(f"/projects/{slug}/test", headers=HTML).headers["location"]
        jobs.pop()()
        expected[location] = status
    for location, status in expected.items():
        page = _status(dev, location)
        assert WORDS[status] in page
    assert "Enter it on the Credentials page" in _status(dev, next(iter(expected)))
    assert "RuntimeError" in _status(dev, list(expected)[1])
    assert "secret-ish" not in _status(dev, list(expected)[1])      # only the class is stored

    # a request still `running` when the server dies is shown as interrupted after restart
    pending = RunQueue(limit=lambda: 3, runner=runner, spawn=jobs.append,
                       path=lambda: Path(run_queue._queue_file().parent / "q3.json"))
    monkeypatch.setattr(run_queue, "_QUEUE", pending)
    location = dev.post("/projects/alpha/test", headers=HTML).headers["location"]
    revived = RunQueue(limit=lambda: 3, runner=runner, spawn=lambda job: None,
                       path=lambda: Path(run_queue._queue_file().parent / "q3.json"))
    revived.recover()
    monkeypatch.setattr(run_queue, "_QUEUE", revived)
    page = _status(dev, location)
    assert WORDS["interrupted"] in page and "press Test again" in page


def test_the_button_is_shown_only_to_someone_who_may_press_it(world) -> None:
    dev, users, *_rest = world
    set_relation("alpha", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    seen = users["tester"].get("/projects/alpha")
    assert seen.status_code == 200                       # the tester may look ...
    assert "action='/projects/alpha/test'" not in seen.text     # ... but is not offered the button
    for who in (dev, users["admin"]):
        assert "action='/projects/alpha/test'" in who.get("/projects/alpha").text


def test_a_request_the_queue_no_longer_holds_leads_to_its_saved_report(world) -> None:
    dev, _users, _gates, _counters, _make, _mp = world
    ProjectStore("alpha").save_run(Run(id="run-kept", project="alpha"))
    resp = dev.get("/projects/alpha/test/run-kept", headers=HTML)
    assert resp.status_code == 303 and resp.headers["location"] == "/projects/alpha/runs/run-kept"
    assert dev.get("/projects/alpha/test/run-never", headers=HTML).status_code == 404

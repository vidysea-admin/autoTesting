"""T-203 run queue (D-072 G6, hosting.md HO16-HO20): single-flight per project, a server-wide limit,
queued state, persistence, slot release.

Deterministic by construction: the queue's `spawn` seam is a manual spawner that only records
jobs, and each test starts a job by calling it -- no sleeps. Every case names the real scenario
that reaches it (a second member pressing Test, an admin setting the limit, a run that crashes,
the server being redeployed mid-run).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.schema.run_queue import QueueEntry, QueueStatus
from autotester.ui.run_queue import QueueFull, RunQueue, RunRefused


class _Manual:
    """Spawner that holds workers until the test runs them."""

    def __init__(self) -> None:
        self.pending: list[Callable[[], None]] = []

    def __call__(self, job: Callable[[], None]) -> None:
        self.pending.append(job)

    def run_next(self) -> None:
        self.pending.pop(0)()


def _queue(limit: int = 2, **kw) -> tuple[RunQueue, _Manual, list[str]]:
    manual, log = _Manual(), []

    def runner(entry: QueueEntry) -> None:
        log.append(entry.project)
        if entry.project.startswith("boom"):
            raise RuntimeError("browser died with token abc123")
        if entry.project.startswith("deny"):
            raise RunRefused("credentials are missing")

    return RunQueue(limit=lambda: limit, spawn=manual, runner=runner, **kw), manual, log


def _states(queue: RunQueue) -> dict[str, QueueStatus]:
    return {e.project: e.status for e in queue.snapshot()}


def test_first_press_on_an_idle_server_starts_at_once() -> None:
    queue, manual, log = _queue()
    entry = queue.submit("alpha")
    assert entry.status is QueueStatus.RUNNING and entry.id.startswith("run-")
    assert len(manual.pending) == 1 and log == []   # handed to a worker, not run in the call
    manual.run_next()
    assert log == ["alpha"] and _states(queue) == {"alpha": QueueStatus.DONE}


def test_second_member_pressing_test_on_a_busy_project_is_queued_not_started() -> None:
    queue, manual, _ = _queue()
    queue.submit("alpha")
    second = queue.submit("alpha")
    assert second.status is QueueStatus.QUEUED and second.position == 1
    assert len(manual.pending) == 1                 # only the first got a worker
    manual.run_next()                               # it finishes -> the second is dispatched
    assert sorted(e.status for e in queue.snapshot()) == [QueueStatus.DONE, QueueStatus.RUNNING]


def test_different_projects_run_together_up_to_the_server_limit() -> None:
    queue, manual, _ = _queue(limit=2)
    states = [queue.submit(p).status for p in ("alpha", "beta", "gamma")]
    assert states == [QueueStatus.RUNNING, QueueStatus.RUNNING, QueueStatus.QUEUED]
    manual.run_next()                               # alpha ends -> gamma takes the freed slot
    assert _states(queue)["gamma"] is QueueStatus.RUNNING


def test_a_queued_run_of_a_busy_project_does_not_block_other_projects() -> None:
    queue, _, _ = _queue(limit=2)
    queue.submit("alpha")
    queue.submit("alpha")                           # waits behind alpha's own run
    assert queue.submit("beta").status is QueueStatus.RUNNING   # skips the blocked entry


def test_never_more_than_the_limit_and_never_two_of_one_project_running() -> None:
    queue, manual, _ = _queue(limit=2)

    def check() -> None:
        running = [e.project for e in queue.snapshot() if e.status is QueueStatus.RUNNING]
        assert len(running) <= 2 and len(running) == len(set(running))

    for project in ("a", "a", "b", "b", "c", "a"):
        queue.submit(project)
        check()
    while manual.pending:
        manual.run_next()
        check()


def test_limit_of_one_serialises_everything() -> None:
    queue, _, _ = _queue(limit=1)
    assert queue.submit("alpha").status is QueueStatus.RUNNING
    assert queue.submit("beta").status is QueueStatus.QUEUED


def test_admin_raising_the_limit_applies_to_the_next_dispatch_without_a_restart() -> None:
    limit = {"n": 1}
    manual = _Manual()
    queue = RunQueue(limit=lambda: limit["n"], spawn=manual, runner=lambda e: None)
    queue.submit("alpha")
    queue.submit("beta")
    assert _states(queue)["beta"] is QueueStatus.QUEUED
    limit["n"] = 2
    queue.submit("gamma")                           # the next event re-reads the setting
    assert _states(queue) == {"alpha": QueueStatus.RUNNING, "beta": QueueStatus.RUNNING,
                              "gamma": QueueStatus.QUEUED}


def test_queue_positions_are_first_come_first_served() -> None:
    queue, _, _ = _queue(limit=1)
    for project in ("alpha", "beta", "gamma"):
        queue.submit(project)
    queued = [(e.project, e.position) for e in queue.snapshot()
              if e.status is QueueStatus.QUEUED]
    assert queued == [("beta", 1), ("gamma", 2)]


def test_a_project_mashing_the_button_hits_the_waiting_cap_with_a_reason() -> None:
    queue, _, _ = _queue(limit=1, max_waiting=2)
    queue.submit("alpha")                           # running
    queue.submit("alpha")
    queue.submit("alpha")                           # 2 waiting = the cap
    with pytest.raises(QueueFull, match="already waiting"):
        queue.submit("alpha")
    assert queue.submit("beta").status is QueueStatus.QUEUED   # another project is unaffected


def test_a_crashing_run_frees_its_slot_and_reports_only_the_exception_class() -> None:
    queue, manual, _ = _queue(limit=1)
    queue.submit("boom-a")
    queue.submit("beta")
    manual.run_next()                               # the runner raises with a secret in its text
    by_project = {e.project: e for e in queue.snapshot()}
    assert by_project["boom-a"].status is QueueStatus.FAILED
    assert by_project["boom-a"].reason == "RuntimeError"        # not "...token abc123"
    assert by_project["beta"].status is QueueStatus.RUNNING     # released in finally


def test_a_gate_that_says_no_at_start_is_refused_with_its_reason_and_frees_the_slot() -> None:
    """The member's credentials were deleted while the run waited in the queue."""
    queue, manual, _ = _queue(limit=1)
    queue.submit("deny-a")
    queue.submit("beta")
    manual.run_next()
    by_project = {e.project: e for e in queue.snapshot()}
    assert by_project["deny-a"].status is QueueStatus.REFUSED
    assert by_project["deny-a"].reason == "credentials are missing"
    assert by_project["beta"].status is QueueStatus.RUNNING


def test_snapshot_can_be_limited_to_one_project() -> None:
    queue, _, _ = _queue()
    queue.submit("alpha")
    queue.submit("beta")
    assert {e.project for e in queue.snapshot("beta")} == {"beta"}


def test_requested_by_and_trigger_are_recorded_on_every_entry() -> None:
    queue, _, _ = _queue()
    entry = queue.submit("alpha", requested_by="dev@vidysea.example", trigger="schedule")
    assert (entry.requested_by, entry.trigger) == ("dev@vidysea.example", "schedule")


def test_finished_entries_are_trimmed_so_the_page_does_not_grow_forever() -> None:
    queue, manual, _ = _queue(limit=1)
    for i in range(40):
        queue.submit(f"p{i}")
        manual.run_next()
    assert len(queue.snapshot()) <= 20


# -- persistence (HO16/HO18): the server is redeployed while people have runs in flight ------

def test_queue_survives_a_restart_and_a_run_caught_mid_flight_is_interrupted(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".work" / "run_queue.json"
    before, manual, _ = _queue(limit=1, path=lambda: path)
    before.submit("alpha")                           # running when the process dies
    before.submit("beta")                            # waiting
    assert manual.pending                            # (the worker never finishes: process killed)

    after, manual2, log2 = _queue(limit=1, path=lambda: path)   # a fresh process, same data dir
    after.recover()
    states = _states(after)
    assert states["alpha"] is QueueStatus.INTERRUPTED           # never re-executed
    assert "restarted" in {e.project: e for e in after.snapshot()}["alpha"].reason
    assert states["beta"] is QueueStatus.RUNNING                # waiting work resumed
    assert len(manual2.pending) == 1 and log2 == []             # alpha was NOT re-run
    manual2.run_next()
    assert log2 == ["beta"]


def test_a_corrupt_queue_file_does_not_stop_the_site(tmp_path: Path) -> None:
    path = tmp_path / "run_queue.json"
    path.write_text("{not json", encoding="utf-8")
    queue, _, _ = _queue(path=lambda: path)
    queue.recover()
    assert queue.snapshot() == []
    assert queue.submit("alpha").status is QueueStatus.RUNNING


# -- shared RAM budget (HO20) --------------------------------------------------------------

def test_two_runs_planning_together_see_each_others_grants() -> None:
    queue, _, _ = _queue()
    with queue.planning("run-a") as reserved:
        assert reserved == 0.0
        queue.grant("run-a", 1536.0)
    with queue.planning("run-b") as reserved:
        assert reserved == 1536.0                    # b plans net of a's contexts
        queue.grant("run-b", 640.0)
    with queue.planning("run-a") as reserved:        # a re-planning excludes its own grant
        assert reserved == 640.0


def test_planning_is_serialised_so_simultaneous_starts_cannot_both_claim_the_same_ram() -> None:
    queue, _, _ = _queue()
    inside, release, second_in = threading.Event(), threading.Event(), threading.Event()

    def first() -> None:
        with queue.planning("run-a"):
            inside.set()
            assert release.wait(timeout=10)

    def second() -> None:
        with queue.planning("run-b"):
            second_in.set()

    t1 = threading.Thread(target=first)
    t1.start()
    assert inside.wait(timeout=10)
    t2 = threading.Thread(target=second)
    t2.start()
    assert not second_in.wait(timeout=0.2)           # blocked while run-a is planning
    release.set()
    assert second_in.wait(timeout=10)
    t1.join(timeout=10)
    t2.join(timeout=10)


def test_a_finished_run_gives_its_ram_grant_back() -> None:
    queue, manual, _ = _queue()
    entry = queue.submit("alpha")
    with queue.planning(entry.id):
        queue.grant(entry.id, 1024.0)
    manual.run_next()
    with queue.planning("run-other") as reserved:
        assert reserved == 0.0


def test_default_thread_worker_does_not_block_the_caller_and_frees_the_slot() -> None:
    """The production spawner: submit() returns while the job is still blocked on an event."""
    release, started, second_ran, threads = (threading.Event(), threading.Event(),
                                             threading.Event(), [])

    def spawn(job: Callable[[], None]) -> None:
        threads.append(threading.Thread(target=job))
        threads[-1].start()

    def runner(entry: QueueEntry) -> None:
        if not started.is_set():
            started.set()
            assert release.wait(timeout=10)
        else:
            second_ran.set()

    queue = RunQueue(limit=lambda: 1, spawn=spawn, runner=runner)
    first = queue.submit("alpha")
    assert started.wait(timeout=10) and first.status is QueueStatus.RUNNING
    assert queue.submit("alpha").status is QueueStatus.QUEUED       # returned mid-run
    release.set()
    assert second_ran.wait(timeout=10)       # the first worker's finish dispatched the queued one
    for thread in threads:
        thread.join(timeout=10)
    assert [e.status for e in queue.snapshot()] == [QueueStatus.DONE, QueueStatus.DONE]

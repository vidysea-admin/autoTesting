"""T-203 run queue under failure and contention (hosting.md HO17, HO18; AT-865, AT-867).

Scenarios: the data disk is full or read-only when a member presses Test; a run's worker is
cut off by a process exit or a cancelled task; two members press Test for different projects in
the same instant on a server limited to one run.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.schema.run_queue import QueueEntry, QueueStatus
from autotester.ui.run_queue import RunQueue


def _statuses(queue: RunQueue) -> dict[str, QueueStatus]:
    return {e.project: e.status for e in queue.snapshot()}


def test_a_full_disk_when_a_member_presses_test_does_not_strand_the_slot(tmp_path: Path) -> None:
    """HO18: the queue file cannot be written. The entry the press just marked running must
    still get its worker, so finishing it frees the slot (it used to stay `running` forever)."""
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x", encoding="utf-8")              # a file where the folder should be
    jobs: list[Callable[[], None]] = []
    queue = RunQueue(limit=lambda: 1, spawn=jobs.append, runner=lambda e: None,
                     path=lambda: blocker / "run_queue.json")

    queue.submit("alpha")
    queue.submit("beta")

    assert len(jobs) == 1, "alpha was marked running, so it must have been launched"
    jobs.pop(0)()                                            # alpha finishes
    assert _statuses(queue) == {"alpha": QueueStatus.DONE, "beta": QueueStatus.RUNNING}
    assert len(jobs) == 1, "the slot alpha freed went to beta, with a worker"


def _aborting(exc: BaseException) -> Callable[[QueueEntry], None]:
    def runner(entry: QueueEntry) -> None:
        raise exc
    return runner


@pytest.mark.parametrize("abort", [SystemExit(1), asyncio.CancelledError()],
                         ids=["process-exit", "cancelled-task"])
def test_a_run_cut_off_by_exit_or_cancellation_is_not_recorded_as_done(
    abort: BaseException,
) -> None:
    """HO18: the worker of a run is killed mid-way. The slot is freed, the next waiter starts,
    and the finished row says it was interrupted, never `done`."""
    jobs: list[Callable[[], None]] = []
    queue = RunQueue(limit=lambda: 1, spawn=jobs.append, runner=_aborting(abort))
    queue.submit("alpha")
    queue.submit("beta")

    with pytest.raises(type(abort)):                         # the abort still propagates
        jobs.pop(0)()

    by_project = {e.project: e for e in queue.snapshot()}
    assert by_project["alpha"].status is QueueStatus.INTERRUPTED
    assert by_project["alpha"].reason == type(abort).__name__
    assert by_project["beta"].status is QueueStatus.RUNNING


def test_two_members_pressing_test_in_the_same_instant_cannot_both_claim_the_last_slot() -> None:
    """HO17: the claim lock. Widened-window harness: `limit()` is read inside the claim and
    takes 50 ms here, so two unlocked claimers would both see an empty server and both run
    (measured 10 of 10 with the lock removed; the unwidened race hides under the GIL)."""
    def slow_limit() -> int:
        time.sleep(0.05)
        return 1

    queue = RunQueue(limit=slow_limit, spawn=lambda job: None, runner=lambda e: None)
    gate = threading.Barrier(2)

    def press(project: str) -> None:
        gate.wait()
        queue.submit(project)

    threads = [threading.Thread(target=press, args=(p,)) for p in ("alpha", "beta")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    running = [e for e in queue.snapshot() if e.status is QueueStatus.RUNNING]
    assert len(running) == 1, f"limit 1 but {len(running)} runs were started"

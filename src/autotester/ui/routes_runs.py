"""Trigger a real run. Contract: qa/contracts/ui-run.md RU1-RU4. Run-history
and report views live in `ui/routes_report.py`. Every gate, the execution and the saved `Run`
live in `stages/run_launcher.py` (T-205/TF1, the one launcher the Test button and the
scheduler share); serial-vs-parallel case execution lives in `ui/run_execution.py`. This file
only turns a press into a queue entry and a `LaunchRefused` into an HTTP error.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from autotester.core.ids import ulid
from autotester.providers import for_role
from autotester.providers.base import Provider
from autotester.schema.case import CasePriority
from autotester.schema.enums import Trigger
from autotester.schema.project import Project
from autotester.schema.run_queue import QueueEntry
from autotester.stages import run_launcher
from autotester.stages.parallel_run import _free_ram_mb, plan_parallel_run
from autotester.stages.run_launcher import LaunchRefused, RunSeams
from autotester.stages.run_launcher import is_entry_case as _is_entry_case
from autotester.ui.run_queue import (
    QueueFull,
    RunQueue,
    RunRefused,
    get_queue,
    set_queue,
    set_runner,
)

router = APIRouter()

__all__ = ["_is_entry_case", "get_queue", "router", "tick_queue", "tick_runner"]


def _seams(*, shared_ram: bool = True) -> RunSeams:
    """The collaborators of a run, looked up at call time from this module (tests and the
    server both swap `for_role`, `plan_parallel_run` and `_free_ram_mb` here).
    `shared_ram` plans against the queue's RAM ledger (HO20); a gate-only check needs none, and
    must not touch the queue file."""
    def judge(project: Project) -> Provider:
        return for_role(project, "judge")     # LL2: the one provider factory, looked up here

    return RunSeams(judge_factory=judge, planner=plan_parallel_run,
                    free_ram_mb=_free_ram_mb, ledger=get_queue() if shared_ram else None)


def _with_seams(launcher_fn: Callable[..., Any]) -> Callable[..., Any]:
    """Bind a launcher function to this module's current seams (the names tests reach here)."""
    return lambda *args, **kwargs: launcher_fn(*args, seams=_seams(), **kwargs)


_execute_with_trace = _with_seams(run_launcher.run_cases_traced)
_plan_under_shared_budget = _with_seams(run_launcher.plan_under_shared_budget)


@router.post("/projects/{slug}/run")
def trigger_run(slug: str, priority: Annotated[list[CasePriority] | None, Query()] = None
                ) -> RedirectResponse:
    """Queue a real run and return at once (RU1-RU4; T-203/D-072 G6). The launcher's gates are
    checked now, so 400/403 come back immediately; the run itself starts when the server-wide
    limit and the project's single-flight slot allow, and the report page shows it as queued,
    then running."""
    try:
        run_launcher.prepare_run(slug, _seams(shared_ram=False), priority)
    except LaunchRefused as exc:
        raise HTTPException(exc.status, exc.reason) from exc
    try:
        get_queue().submit(slug, run_id=f"run-{ulid()}", priorities=priority)  # id: post-gates
    except QueueFull as exc:
        raise HTTPException(429, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/report", status_code=303)


_TRIGGER = {"button": Trigger.MANUAL, "schedule": Trigger.SCHEDULE, "api": Trigger.CI}


def _run_queued(entry: QueueEntry) -> None:
    """The queue's executor: the launcher re-checks every gate (HO19), then runs the project.
    The entry's origin (trigger, owner, schedule slot) is stamped on the saved `Run` (TS6)."""
    try:
        run_launcher.launch_run(entry.project, run_id=entry.id, trigger=_TRIGGER[entry.trigger],
                                requested_by=entry.requested_by, slot_key=entry.slot_key,
                                via=entry.via, requested_at=entry.enqueued_at,
                                seams=_seams(), priorities=entry.priorities)
    except LaunchRefused as exc:
        raise RunRefused(exc.reason) from exc


set_runner(_run_queued)


def tick_runner(entry: QueueEntry) -> None:
    """`_run_queued` for the tick process: a refusal at start has no UI to show it, so it is
    also written to stderr (the entry still ends `refused`)."""
    try:
        _run_queued(entry)
    except RunRefused as exc:
        print(f"{entry.slot_key or entry.id}: run refused at start: {exc}", file=sys.stderr)
        raise


def tick_queue() -> RunQueue:
    """The queue a scheduler tick process runs its entries on (T-200): in memory only, so it
    never `recover()`s the server's persisted queue; workers are non-daemon threads, so the
    process stays alive until the runs it started finish. Installed as the process queue, so
    the executor's RAM ledger is this one. Executes through the same `_run_queued`."""
    queue = RunQueue(runner=tick_runner,
                     spawn=lambda job: threading.Thread(target=job, name="autotester-run").start())
    set_queue(queue)
    return queue

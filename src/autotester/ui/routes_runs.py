"""Trigger a real run. Contract: qa/contracts/ui-run.md RU1-RU4. Run-history
and report views live in `ui/routes_report.py`. Every gate, the execution and the saved `Run`
live in `stages/run_launcher.py` (T-205/TF1, the one launcher the Test button and the
scheduler share); serial-vs-parallel case execution lives in `ui/run_execution.py`. This file
only turns a press into a queue entry and a `LaunchRefused` into an HTTP error.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from autotester.core.ids import ulid
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.run_queue import QueueEntry
from autotester.stages import run_launcher
from autotester.stages.parallel_run import _free_ram_mb, plan_parallel_run
from autotester.stages.run_launcher import LaunchRefused, RunSeams
from autotester.stages.run_launcher import is_entry_case as _is_entry_case
from autotester.ui.run_queue import QueueFull, RunRefused, get_queue, set_runner

router = APIRouter()

__all__ = ["_is_entry_case", "get_queue", "router"]


def _seams(*, shared_ram: bool = True) -> RunSeams:
    """The collaborators of a run, looked up at call time from this module (tests and the
    server both swap `LangChainFallbackProvider`, `plan_parallel_run` and `_free_ram_mb` here).
    `shared_ram` plans against the queue's RAM ledger (HO20); a gate-only check needs none, and
    must not touch the queue file."""
    return RunSeams(judge_factory=LangChainFallbackProvider, planner=plan_parallel_run,
                    free_ram_mb=_free_ram_mb, ledger=get_queue() if shared_ram else None)


def _with_seams(launcher_fn: Callable[..., Any]) -> Callable[..., Any]:
    """Bind a launcher function to this module's current seams (the names tests reach here)."""
    return lambda *args, **kwargs: launcher_fn(*args, seams=_seams(), **kwargs)


_execute_with_trace = _with_seams(run_launcher.run_cases_traced)
_plan_under_shared_budget = _with_seams(run_launcher.plan_under_shared_budget)


@router.post("/projects/{slug}/run")
def trigger_run(slug: str) -> RedirectResponse:
    """Queue a real run and return at once (RU1-RU4; T-203/D-072 G6). The launcher's gates are
    checked now, so 400/403 come back immediately; the run itself starts when the server-wide
    limit and the project's single-flight slot allow, and the report page shows it as queued,
    then running."""
    try:
        run_launcher.prepare_run(slug, _seams(shared_ram=False))
    except LaunchRefused as exc:
        raise HTTPException(exc.status, exc.reason) from exc
    try:
        get_queue().submit(slug, run_id=f"run-{ulid()}")   # minted only after the gates passed
    except QueueFull as exc:
        raise HTTPException(429, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/report", status_code=303)


def _run_queued(entry: QueueEntry) -> None:
    """The queue's executor: the launcher re-checks every gate (HO19), then runs the project."""
    try:
        run_launcher.launch_run(entry.project, run_id=entry.id, requested_by=entry.requested_by,
                                seams=_seams())
    except LaunchRefused as exc:
        raise RunRefused(exc.reason) from exc


set_runner(_run_queued)

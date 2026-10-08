"""Adapt UI presses and queue workers to the one FastAPI-free regression launcher."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from autotester.auth import accounts, db
from autotester.auth.access import authorize, resource_for
from autotester.auth.config import auth_disabled
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey, Principal, all_permissions
from autotester.schema.enums import Trigger
from autotester.schema.run_queue import QueueEntry
from autotester.schema.team_enums import RunVia
from autotester.stages import run_launcher
from autotester.stages.parallel_run import (
    DEFAULT_PER_CONTEXT_MB,
    VIDEO_OVERHEAD_MB,
    _free_ram_mb,
)
from autotester.stages.run_launcher import RunLaunchRefused, launch_run, prepare_run
from autotester.ui.run_queue import QueueFull, RunRefused, get_queue, set_runner

router = APIRouter()
TRIGGERS = {RunVia.BUTTON: Trigger.MANUAL, RunVia.SCHEDULE: Trigger.SCHEDULE,
            RunVia.API: Trigger.CI}


@router.post("/projects/{slug}/run")
def trigger_run(slug: str) -> RedirectResponse:
    """Preflight now, then queue and return 303; the worker repeats the live gates."""
    try:
        prepare_run(slug)
    except RunLaunchRefused as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    who = current_principal()
    try:
        get_queue().submit(slug, requested_by=who.email if who else None)
    except QueueFull as exc:
        raise HTTPException(429, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/report", status_code=303)


def _worker_principal(requested_by: str | None) -> Principal | None:
    """Current account and grants, never a permission snapshot from enqueue time."""
    if requested_by == "local" and auth_disabled():
        return Principal(user_id=0, email="local", permissions=frozenset(all_permissions()))
    if not requested_by or not db.store_exists():
        return None
    user = accounts.find_user(requested_by)
    if user is None or user.disabled:
        return None
    with db.reading() as conn:
        permissions = frozenset(row["permission"] for row in conn.execute(
            "SELECT DISTINCT p.permission FROM memberships m JOIN group_permissions p "
            "ON p.group_id = m.group_id WHERE m.user_id = ?", (user.id,)))
    return Principal(user_id=user.id, email=user.email, permissions=permissions)


def _plan_under_shared_budget(project, run_id):
    """The queue adapter lends the launcher one plan from the shared server RAM budget."""
    queue = get_queue()
    with queue.planning(run_id) as reserved:
        extra = {"free_ram_mb": max(0.0, _free_ram_mb() - reserved)} if reserved else {}
        plan = run_launcher.plan_parallel_run(project, video_enabled=True, **extra)
        queue.grant(run_id, plan.n * (DEFAULT_PER_CONTEXT_MB + VIDEO_OVERHEAD_MB))
    return plan


def _run_queued(entry: QueueEntry) -> None:
    """Refuse revoked/disabled requesters before preparation or any browser side effect."""
    who = _worker_principal(entry.requested_by)
    if who is None or not authorize(who, PermissionKey.PROJECT_RUN, resource_for(entry.project)):
        raise RunRefused("project.run permission is no longer available for this requester")

    try:
        launch_run(entry.project, run_id=entry.id, trigger=TRIGGERS[entry.trigger],
                   requested_by=entry.requested_by, slot_key=entry.slot_key, via=entry.via,
                   capacity=lambda project: _plan_under_shared_budget(project, entry.id))
    except RunLaunchRefused as exc:
        raise RunRefused(exc.detail) from exc


set_runner(_run_queued)

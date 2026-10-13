"""The team Test button (T-201b, qa/contracts/team-test-button.md TT1-TT6): a teammate with
`project.run` presses Test and gets a queued request, then the report.

One job: turn a permitted press into ONE queue entry attributed to the signed-in person, and
show that entry's status. It never runs anything: the worker the queue starts calls
`stages/run_launcher.launch_run` (the one launcher, TF1), and the launcher's gates (cases, judge,
credentials, the credential-derived approval, D-068) are evaluated here first by `prepare_run`,
so a refusal comes back at once with its reason and leaves nothing behind (no run id, no
directory, no queue entry, no browser). Who pressed comes from the session, never the request.
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.core.ids import ulid
from autotester.schema.auth import PermissionKey, Principal
from autotester.schema.run_queue import ACTIVE, QueueEntry
from autotester.schema.team_enums import CredentialState, RunVia
from autotester.stages import run_launcher
from autotester.stages.run_launcher import LaunchRefused
from autotester.stages.schedule_gate import credential_state
from autotester.store.project_store import ProjectStore
from autotester.ui import team_run_view
from autotester.ui.helpers import _load_project_or_404, _require_safe_id
from autotester.ui.routes_runs import _seams
from autotester.ui.run_queue import QueueFull, get_queue

router = APIRouter()
_PRESS = threading.Lock()
"""Held from "is a request already active?" to "enqueue", so two presses cannot both miss it."""


def _presser(slug: str) -> Principal:
    """The signed-in person who may press Test on `slug`, else the refusal (before any work).
    The login gate already did this; checking again here means the route is safe on its own."""
    who = current_principal()
    if who is None or not who.authenticated:
        raise HTTPException(401, "sign in to press Test")
    resource = resource_for(slug)
    if not authorize(who, PermissionKey.PROJECT_VIEW, resource):
        raise HTTPException(404, f"no project '{slug}'")    # same as a project that is missing
    if not authorize(who, PermissionKey.PROJECT_RUN, resource):
        raise HTTPException(403, "you need the project.run permission on this project "
                                 "to press Test")
    return who


def _reason(slug: str, exc: LaunchRefused) -> str:
    """What the person is told: for an approval refusal (403) the credential state first (the
    same classification the schedule's gate uses), then the launcher's own sentence."""
    if exc.status != 403:
        return exc.reason
    store = ProjectStore(slug)
    project = store.load_project()
    state = credential_state(project, store) if project else CredentialState.PROVISIONED
    return exc.reason if state is CredentialState.PROVISIONED else (
        f"{state.value}: {team_run_view.STATE_SAYS[state]}. "
        f"{exc.reason}")


@router.post("/projects/{slug}/test")
def press_test(slug: str) -> RedirectResponse:
    """Queue a run for the signed-in person and return at once (TT2). A request already queued
    or running for this project is returned instead of a second one (TT5)."""
    who = _presser(slug)
    try:
        run_launcher.prepare_run(slug, _seams(shared_ram=False))   # gates now, nothing started
    except LaunchRefused as exc:
        raise HTTPException(exc.status, _reason(slug, exc)) from exc
    queue = get_queue()
    with _PRESS:
        active = [e for e in queue.snapshot(slug) if e.status in ACTIVE]
        try:
            entry = active[0] if active else queue.submit(
                slug, run_id=f"run-{ulid()}", requested_by=who.email,
                requested_by_id=str(who.user_id),
                trigger="button", via=RunVia.TEAM_BUTTON)
        except QueueFull as exc:
            raise HTTPException(429, str(exc)) from exc
    return RedirectResponse(f"/projects/{slug}/test/{entry.id}", status_code=303)


def _entry(slug: str, run_id: str) -> QueueEntry | None:
    return next((e for e in get_queue().snapshot(slug) if e.id == run_id), None)


@router.get("/projects/{slug}/test/{run_id}", response_class=HTMLResponse)
def test_status(slug: str, run_id: str) -> Response:
    """The request's status, read from the persisted queue entry (no worker handle). An entry
    the queue has since dropped sends the reader to the run report if one was saved."""
    store, _project = _load_project_or_404(slug)
    _require_safe_id(run_id, "run_id")
    entry = _entry(slug, run_id)
    if entry is not None:
        return HTMLResponse(team_run_view.status_page(slug, entry))
    if store.load_run(run_id) is not None:
        return RedirectResponse(f"/projects/{slug}/runs/{run_id}", status_code=303)
    raise HTTPException(404, f"no test request '{run_id}' for project '{slug}'")

"""Markup for the team Test button (T-201b): the button, the request status page, the "started
by" line on a report. Presentation only: it reads a `QueueEntry` or a `Run` it is handed and
starts, queues and decides nothing (the routes in `ui/routes_team_run.py` do).
"""

from __future__ import annotations

from html import escape

from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey
from autotester.schema.run import Run
from autotester.schema.run_queue import ACTIVE, QueueEntry, QueueStatus
from autotester.schema.team_enums import CredentialState, RunVia
from autotester.ui import theme

_TONE = {QueueStatus.QUEUED: "warning", QueueStatus.RUNNING: "positive",
         QueueStatus.DONE: "positive", QueueStatus.FAILED: "warning",
         QueueStatus.REFUSED: "warning", QueueStatus.INTERRUPTED: "warning"}
_MEANING = {
    QueueStatus.QUEUED: "Waiting for a free run slot.",
    QueueStatus.RUNNING: "The run is in progress.",
    QueueStatus.DONE: "The run finished.",
    QueueStatus.FAILED: "The run stopped on an error before it could finish.",
    QueueStatus.REFUSED: "A gate said no when the run was about to start; nothing ran.",
    QueueStatus.INTERRUPTED: "The server stopped while this run was in progress; "
                             "it was not re-run. Press Test again.",
}

STATE_SAYS = {
    CredentialState.NO_SECRETREF:
        "this project declares no credential pair, so there is no standing approval to run "
        "under; declare one on the project's Credentials page",
    CredentialState.SECRETREF_WITHOUT_VALUE:
        "a credential is declared but has no value; enter it on the project's Credentials page",
    CredentialState.TARGET_OUTSIDE_DOMAINS:
        "the credentials are not scoped to this project's target host or allowed domains",
}
"""What a refused press tells the person, by credential state (static text, never a value)."""


def button_html(slug: str) -> str:
    """The Test button, shown only to a viewer who may press it. Hiding it is courtesy: the
    route checks `project.run` on its own (TT2)."""
    who = current_principal()
    if who is not None and not authorize(who, PermissionKey.PROJECT_RUN, resource_for(slug)):
        return ""
    return (f"<form method='post' action='/projects/{escape(slug)}/test' style='display:inline'>"
            "<button class='btn btn-primary' type='submit' title='Run every case now and get "
            "the report'>🧪 Test</button></form>")


def started_by(run: Run | None) -> str:
    """The report header's "who started this" line; empty for a run with no recorded person."""
    if run is None or not run.requested_by:
        return ""
    how = " with the Test button" if run.via is RunVia.TEAM_BUTTON else ""
    when = f" at {run.requested_at:%Y-%m-%d %H:%M} UTC" if run.requested_at else ""
    uid = f" (user #{run.requested_by_id})" if run.requested_by_id is not None else ""
    return (f"<p class='subtitle'>Started by <strong>{escape(run.requested_by)}</strong>"
            f"{uid}{how}{when}</p>")


def status_page(slug: str, entry: QueueEntry) -> str:
    """One request: its status, its place in the line while queued, and where the report is.
    Reloads itself every 5 s while the request is still queued or running."""
    safe_slug, run_id = escape(slug), escape(entry.id)
    refresh = "<meta http-equiv='refresh' content='5'>" if entry.status in ACTIVE else ""
    place = (f"<p>Position in the line: <strong>#{entry.position}</strong></p>"
             if entry.status is QueueStatus.QUEUED else "")
    why = (f"<p class='meta'>Reason: {escape(entry.reason)}</p>" if entry.reason else "")
    report = (f"<p><a class='btn btn-primary' href='/projects/{safe_slug}/runs/{run_id}'>"
              "Open the report</a></p>" if entry.status is QueueStatus.DONE else "")
    uid = f" (user #{entry.requested_by_id})" if entry.requested_by_id is not None else ""
    who = (f" by <strong>{escape(entry.requested_by)}</strong>{uid}" if entry.requested_by else "")
    body = (
        theme.breadcrumb(("Projects", "/"), (safe_slug, f"/projects/{safe_slug}"),
                         ("Test", None))
        + f"<h1>Test run <code>{run_id}</code></h1>"
        + f"<p class='subtitle'>Requested{who} at {entry.enqueued_at:%Y-%m-%d %H:%M} UTC</p>"
        + theme.card(
            f"<p>{theme.pill(escape(entry.status.value), _TONE[entry.status])} "
            f"{escape(_MEANING[entry.status])}</p>{place}{why}{report}"
            f"<p><a href='/projects/{safe_slug}/report'>All runs of this project</a></p>",
            title="Status")
    )
    return theme.page(f"Test {run_id}", refresh + body, active_slug=slug)

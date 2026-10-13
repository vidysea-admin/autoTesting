"""The internal bug tracker page and its Tracker-layout export (T-199, TB7 in part, TB15).

Its one job is to show `BugStore` bugs (list with a status/severity filter, detail with the event
history) and offer them as CSV / xlsx. Nothing here writes to a sheet or to the store. The routes
declare their permission in `ROUTE_POLICY` (report.view over the project, project.edit for the
assignee edit) and the same rows sit in the central `auth.policy.ROUTE_POLICY`, which T-204's login
gate walks: no session -> login, no view scope -> the not-found of a missing project (AU13), view
without the key -> 403. The assignee handler re-checks `authorize` itself (no second rule set).
Evidence links point at the existing run page, behind the same gate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.core.paths import ProjectPaths
from autotester.schema.auth import PermissionKey
from autotester.schema.enums import Severity
from autotester.schema.tracked_bug import BugEvent, BugStatus, EventKind, TrackedBug
from autotester.stages.report_export import _load_redactor
from autotester.stages.sheet_sync import load_status
from autotester.stages.tracker_export import evidence_path, to_csv, to_xlsx
from autotester.store.bug_store import BugStore
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404

router = APIRouter()

ROUTE_POLICY: dict[str, tuple[str, str]] = {
    "GET /projects/{slug}/tracker": ("report.view", "project"),
    "GET /projects/{slug}/tracker/export.csv": ("report.view", "project"),
    "GET /projects/{slug}/tracker/export.xlsx": ("report.view", "project"),
    "GET /projects/{slug}/tracker/{bug_key}": ("report.view", "project"),
    "POST /projects/{slug}/tracker/{bug_key}/assignee": ("project.edit", "project"),
}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_TONE = {BugStatus.OPEN: "danger", BugStatus.REOPENED: "danger", BugStatus.FIXED: "positive",
         BugStatus.STALE: "neutral"}


def _store(slug: str) -> BugStore:
    return BugStore(ProjectPaths(slug).dir)


def _may_edit(slug: str) -> bool:
    who = current_principal()
    return who is not None and authorize(who, PermissionKey.PROJECT_EDIT, resource_for(slug))


def _evidence_cell(bug: TrackedBug) -> str:
    link = evidence_path(bug)
    return f"<a href='{escape(link)}'>{escape(bug.evidence_run_id or '')}</a>" if link else ""


def _row(bug: TrackedBug, scrub) -> str:
    slug = escape(bug.project)
    cells = [
        f"<a href='/projects/{slug}/tracker/{escape(bug.bug_key)}'>{escape(scrub(bug.title))}</a>",
        theme.pill(escape(bug.status.value), tone=_TONE[bug.status]),
        escape(bug.severity.value), escape(scrub(bug.screen or "")),
        escape(scrub(bug.assignee or "")),
        f"{bug.first_seen:%Y-%m-%d %H:%M}", f"{bug.last_seen:%Y-%m-%d %H:%M}", str(bug.count),
        _evidence_cell(bug),
    ]
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _sync_note(slug: str, scrub) -> str:
    """TB12: the last sheet-sync outcome; the bug list below is authoritative either way."""
    status = load_status(slug)
    if status is None:
        return ""
    if status.sync_status == "ok":
        return f"<p>Sheet sync: ok at {status.at:%Y-%m-%d %H:%M} UTC</p>"
    retry = f"{status.retry_at:%Y-%m-%d %H:%M} UTC" if status.retry_at else "unscheduled"
    return (f"<p>Sheet sync: {theme.pill('error', tone='danger')} "
            f"{escape(scrub(status.last_error or ''))} - next retry {retry}. "
            "The bugs below are unaffected.</p>")


def _filter_form(slug: str, status: str, severity: str) -> str:
    def options(values: list[str], chosen: str) -> str:
        pairs = ["<option value=''>any</option>"]
        pairs += [f"<option value='{v}'{' selected' if v == chosen else ''}>{v}</option>"
                  for v in values]
        return "".join(pairs)
    return (f"<form method='get' action='/projects/{escape(slug)}/tracker'>"
            "<label for='f-status'>Status</label> <select id='f-status' name='status'>"
            f"{options([s.value for s in BugStatus], status)}"
            f"</select> <label for='f-severity'>Severity</label> "
            "<select id='f-severity' name='severity'>"
            f"{options([s.value for s in Severity], severity)}</select> "
            "<button class='btn' type='submit'>Filter</button></form>")


@router.get("/projects/{slug}/tracker", response_class=HTMLResponse)
def tracker_page(slug: str, status: str = "", severity: str = "") -> str:
    store, project = _load_project_or_404(slug)
    if status and status not in {s.value for s in BugStatus}:
        raise HTTPException(400, f"unknown status '{status}'")
    if severity and severity not in {s.value for s in Severity}:
        raise HTTPException(400, f"unknown severity '{severity}'")
    scrub = _load_redactor(store).scrub
    every = sorted(_store(slug).bugs().values(), key=lambda b: (b.first_seen, b.bug_key))
    shown = [b for b in every if (not status or b.status.value == status)
             and (not severity or b.severity.value == severity)]
    head = "".join(f"<th>{h}</th>" for h in (
        "Bug", "Status", "Severity", "Screen", "Assignee", "First seen", "Last seen", "Count",
        "Evidence"))
    rows = "".join(_row(b, scrub) for b in shown) or "<tr><td colspan='9'>No bugs match.</td></tr>"
    base = f"/projects/{escape(slug)}/tracker"
    name = escape(project.name)
    body = (
        theme.breadcrumb(("Projects", "/"), (name, f"/projects/{escape(slug)}"), ("Tracker", None))
        + "<h1>Bug tracker</h1>"
        + f"<p class='subtitle'>{len(shown)} of {len(every)} bug(s) · "
          f"<a class='btn' href='{base}/export.csv'>Download CSV</a> "
          f"<a class='btn' href='{base}/export.xlsx'>Download Excel</a></p>"
        + _sync_note(slug, scrub) + _filter_form(slug, status, severity)
        + theme.card(f"<div style='overflow:auto'><table><thead><tr>{head}</tr></thead>"
                     f"<tbody>{rows}</tbody></table></div>", title=f"{name} bugs")
    )
    return theme.page(f"{name} · Tracker", body, active_slug=slug)


@router.get("/projects/{slug}/tracker/export.csv")
def export_csv(slug: str) -> Response:
    store, _project = _load_project_or_404(slug)
    data = to_csv(_store(slug).bugs().values(), _load_redactor(store).scrub)
    return Response(data, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{slug}-tracker.csv"'})


@router.get("/projects/{slug}/tracker/export.xlsx")
def export_xlsx(slug: str) -> Response:
    store, _project = _load_project_or_404(slug)
    data = to_xlsx(_store(slug).bugs().values(), _load_redactor(store).scrub)
    return Response(data, media_type=XLSX, headers={
        "Content-Disposition": f'attachment; filename="{slug}-tracker.xlsx"'})


def _assignee_form(slug: str, bug: TrackedBug) -> str:
    """The edit form, only for someone holding project.edit here; members are suggestions."""
    if not _may_edit(slug):
        return ""
    res = resource_for(slug)
    members = sorted({*(res.assignees), *res.shared_with, *([res.owner_email] if res.owner_email
                                                            else [])})
    options = "".join(f"<option value='{escape(m)}'>" for m in members)
    return (f"<form method='post' action='/projects/{escape(slug)}/tracker/"
            f"{escape(bug.bug_key)}/assignee'><label for='assignee'>Assignee</label> "
            f"<input id='assignee' name='assignee' list='members' maxlength='120' "
            f"value='{escape(bug.assignee or '')}'><datalist id='members'>{options}</datalist> "
            "<button class='btn' type='submit'>Save</button></form>")


@router.post("/projects/{slug}/tracker/{bug_key}/assignee")
def set_assignee(slug: str, bug_key: str, assignee: str = Form("")) -> Response:
    _load_project_or_404(slug)
    who = current_principal()
    if who is None or not authorize(who, PermissionKey.PROJECT_EDIT, resource_for(slug)):
        raise HTTPException(403, "you do not have permission for this action")
    bug_store = _store(slug)
    if bug_store.get(bug_key) is None:
        raise HTTPException(404, "no such bug")
    try:
        event = BugEvent(bug_key=bug_key, kind=EventKind.ASSIGN, ref=f"assign-{uuid4().hex}",
                         at=datetime.now(UTC), actor=f"user:{who.email}",
                         assignee=assignee.strip() or None)
    except ValueError as exc:
        raise HTTPException(400, "assignee must be at most 120 characters, no control "
                                 "characters") from exc
    bug_store.apply(event)
    return RedirectResponse(f"/projects/{slug}/tracker/{bug_key}", status_code=303)


@router.get("/projects/{slug}/tracker/{bug_key}", response_class=HTMLResponse)
def bug_detail(slug: str, bug_key: str) -> str:
    store, project = _load_project_or_404(slug)
    bug_store = _store(slug)
    bug = bug_store.get(bug_key)
    if bug is None:
        raise HTTPException(404, "no such bug")
    scrub = _load_redactor(store).scrub
    events = "".join(
        f"<tr><td>{e.at:%Y-%m-%d %H:%M:%S}</td><td>{escape(e.kind.value)}</td>"
        f"<td>{escape(e.actor)}</td><td>{escape(e.run_id or '')}</td>"
        f"<td>{escape(scrub(e.assignee or ''))}</td></tr>" for e in bug_store.history(bug_key))
    facts = (f"<p><strong>{escape(scrub(bug.title))}</strong></p>"
             f"<p>Status {theme.pill(escape(bug.status.value), tone=_TONE[bug.status])} · "
             f"severity {escape(bug.severity.value)} · screen {escape(scrub(bug.screen or '-'))} · "
             f"assignee {escape(scrub(bug.assignee or '-'))} · seen {bug.count}x · "
             f"evidence {_evidence_cell(bug) or '-'}</p>")
    table = (_assignee_form(slug, bug)
             + "<table><thead><tr><th>When</th><th>Event</th><th>Actor</th><th>Run</th>"
             + f"<th>Assignee</th></tr></thead><tbody>{events}</tbody></table>")
    body = (theme.breadcrumb(("Projects", "/"), (escape(project.name), f"/projects/{escape(slug)}"),
                             ("Tracker", f"/projects/{escape(slug)}/tracker"), ("Bug", None))
            + "<h1>Bug</h1>" + theme.card(facts) + theme.card(table, title="History"))
    return theme.page("Bug", body, active_slug=slug)

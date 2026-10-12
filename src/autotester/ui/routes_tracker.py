"""The tracker page: a project's tracked bugs, the sheet mapping preview and the sync status.

Its one job is TB7 (read-only) with the TB8/TB12/TB13 views. The page shows the in-product bugs
(authoritative), the proposed or confirmed column mapping with unmapped fields and their
candidates, the last sync outcome with a scrubbed last error, and the conflicts where a human
edited a cell. It states that nothing has been written to the sheet. It has no form and no write:
confirming a mapping or a first write needs `project.edit`, which is T-204's engine, so those are
stage functions with an injected check and not routes here (contract gap, see the manifest).
Every value is passed through the project's `Redactor.scrub` and then HTML-escaped.
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.tracked_bug import BugStatus, TrackedBug
from autotester.schema.tracker_binding import MappingStatus, TrackerBinding
from autotester.store.bug_store import BugStore
from autotester.store.tracker_store import load_binding
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404

router = APIRouter()

ROUTE_POLICY: dict[str, tuple[str, str]] = {
    "GET /projects/{slug}/tracker": ("report.view", "project"),
}
"""This unit's rows for the central policy table (TF4). The resolver name is T-204's to define."""

NOTHING_WRITTEN = ("Nothing has been written to the sheet. "
                   "Writing stays off until a person confirms.")
_TONE = {MappingStatus.CONFIRMED: "positive", MappingStatus.PROPOSED: "warning",
         MappingStatus.STALE: "danger"}


def _cell(text: str, scrub) -> str:
    return f"<td>{escape(scrub(text))}</td>"


def _bug_rows(bugs: list[TrackedBug], scrub) -> str:
    rows = "".join(
        "<tr>" + _cell(b.title, scrub) + _cell(b.severity.value, scrub)
        + _cell(b.screen or "", scrub)
        + _cell(b.status.value, scrub) + _cell(b.assignee or "", scrub) + f"<td>{b.count}</td></tr>"
        for b in sorted(bugs, key=lambda b: (b.status is BugStatus.STALE, b.first_seen, b.bug_key)))
    return rows or "<tr><td colspan='6'>No bugs tracked yet.</td></tr>"


def _mapping_block(binding: TrackerBinding | None, scrub) -> str:
    if binding is None:
        return "<p>No sheet is bound to this project. The tracker works in-product without one.</p>"
    m = binding.mapping
    who = f" by {escape(scrub(m.confirmed_by))}" if m.confirmed_by else ""
    mapped = "".join(f"<tr><td>{escape(f)}</td><td>{escape(scrub(h))}</td></tr>"
                     for f, h in m.columns.items())
    open_ = "".join(
        f"<tr><td>{escape(f)}</td><td>unmapped"
        + (f": {escape(scrub(', '.join(c)))}" if c else " (no candidate)") + "</td></tr>"
        for f, c in m.unmapped.items())
    return (f"<p>Sheet {escape(scrub(binding.sheet_id))} / tab {escape(scrub(binding.tab))} "
            f"{theme.pill(escape(m.status.value) + who, tone=_TONE[m.status])}</p>"
            f"<table><tr><th>Field</th><th>Sheet column</th></tr>{mapped}{open_}</table>")


def _sync_block(binding: TrackerBinding | None, scrub) -> str:
    if binding is None:
        return ""
    s = binding.sync
    out = f"<p>Sync status: <strong id='sync-status'>{escape(s.sync_status)}</strong>"
    if s.last_error:
        retry = f", retry at {s.retry_at:%Y-%m-%d %H:%M UTC}" if s.retry_at else ""
        out += f"<br>Last error: <span id='sync-error'>{escape(scrub(s.last_error))}</span>{retry}"
    out += "</p>"
    if s.conflicts:
        items = "".join(
            f"<li>{escape(scrub(c.bug_key))}: column {escape(scrub(c.column))} was edited in the "
            f"sheet (now {escape(scrub(c.sheet_has))}); not overwritten</li>" for c in s.conflicts)
        out += f"<h2>Sync conflicts</h2><ul id='conflicts'>{items}</ul>"
    return out


@router.get("/projects/{slug}/tracker", response_class=HTMLResponse)
def tracker_page(slug: str) -> str:
    _, project = _load_project_or_404(slug)
    paths = ProjectPaths(slug)
    scrub = SecretStore.load(project, paths.env_file, strict=False).redactor().scrub
    bugs = list(BugStore(paths.bugs_dir).bugs().values())
    binding = load_binding(slug)
    body = (
        theme.breadcrumb(("Projects", "/"), (escape(project.name), f"/projects/{escape(slug)}"),
                         ("Tracker", None))
        + "<h1>Bug tracker</h1>"
        + f"<p class='subtitle'>{len(bugs)} bug(s) tracked in AutoTester. {NOTHING_WRITTEN}</p>"
        + "<table><tr><th>Bug</th><th>Severity</th><th>Screen</th><th>Status</th>"
          "<th>Assignee</th><th>Seen</th></tr>" + _bug_rows(bugs, scrub) + "</table>"
        + "<h2>Sheet mapping</h2>" + _mapping_block(binding, scrub)
        + _sync_block(binding, scrub)
    )
    return theme.page("Bug tracker", body, active_slug=slug)

"""Markup for "My reports" (TT7). Presentation only: it renders the `InboxEntry` rows the
stage built and decides nothing about who may see what."""

from __future__ import annotations

from html import escape

from autotester.schema.delivery import InboxEntry, ReportLabel
from autotester.schema.run_queue import QueueStatus
from autotester.ui import theme

_LABEL_TONE = {ReportLabel.GREEN: "positive"}


def _status(row: InboxEntry) -> str:
    if row.status is QueueStatus.QUEUED:
        return f"queued, position #{row.position}"
    return row.status.value


def _row(row: InboxEntry) -> str:
    label = (theme.pill(escape(row.label.value), _LABEL_TONE.get(row.label, "warning"))
             if row.label else "in progress")
    who = "scheduled" if row.scheduled else escape(row.started_by or "unknown")
    return (f"<tr><td>{escape(row.project)}</td><td><code>{escape(row.run_id)}</code></td>"
            f"<td>{row.at:%Y-%m-%d %H:%M} UTC</td><td>{who}</td>"
            f"<td>{escape(_status(row))}</td><td>{label}</td>"
            f"<td><a class='btn' href='{escape(row.link)}' "
            f"aria-label='Open the report for run {escape(row.run_id)}'>Open report</a></td></tr>")


def inbox_page(rows: list[InboxEntry]) -> str:
    refresh = "<meta http-equiv='refresh' content='10'>" if any(
        r.label is None for r in rows) else ""
    if not rows:
        body = theme.empty_state("📬", "No reports yet. Press Test on a project to get one.")
    else:
        head = "".join(f"<th scope='col'>{h}</th>" for h in (
            "Project", "Run", "Time", "Started by", "Status", "Report label", "Report"))
        body = theme.card(f"<table aria-label='My reports'><thead><tr>{head}</tr></thead>"
                          f"<tbody>{''.join(_row(r) for r in rows)}</tbody></table>")
    crumbs = theme.breadcrumb(("Projects", "/"), ("My reports", None))
    return theme.page("My reports", refresh + crumbs + "<h1>My reports</h1>" + body)

"""The queue status card shown on a project's runs page (T-203): what is queued, running, done.

Presentation only: reads `ui/run_queue.py`'s snapshot, calls no store and starts nothing."""

from __future__ import annotations

from html import escape

from autotester.schema.run_queue import ACTIVE, QueueEntry, QueueStatus
from autotester.store.server_settings import effective_max_concurrent_runs
from autotester.ui import theme
from autotester.ui.run_queue import RunQueue, get_queue

_TONE = {QueueStatus.QUEUED: "warning", QueueStatus.RUNNING: "positive",
         QueueStatus.DONE: "neutral", QueueStatus.FAILED: "warning",
         QueueStatus.REFUSED: "warning", QueueStatus.INTERRUPTED: "warning"}


def _label(entry: QueueEntry) -> str:
    if entry.status is QueueStatus.QUEUED:
        return f"queued (#{entry.position})"
    return entry.status.value


def _row(entry: QueueEntry) -> str:
    when = (entry.finished_at or entry.started_at or entry.enqueued_at)
    run = (f" <a href='/projects/{escape(entry.project)}/runs/{escape(entry.id)}'>"
           f"<code>{escape(entry.id)}</code></a>" if entry.status is QueueStatus.DONE else "")
    why = f" <span class='meta'>{escape(entry.reason)}</span>" if entry.reason else ""
    who = escape(entry.requested_by) if entry.requested_by else "unknown"
    return (f"<tr><td>{theme.pill(escape(_label(entry)), _TONE[entry.status])}</td>"
            f"<td>{when.strftime('%H:%M:%S UTC')}{run}{why}</td>"
            f"<td>{who} <span class='meta'>({escape(entry.trigger)})</span></td></tr>")


def queue_panel(slug: str, queue: RunQueue | None = None) -> str:
    """HTML card for `slug`'s runs (empty string when nothing was ever queued). Reloads itself
    every 5 s while a run is queued or running, so "queued" turns into "running" unaided."""
    everything = (queue or get_queue()).snapshot()
    mine = [e for e in everything if e.project == slug]
    if not mine:
        return ""
    running = sum(e.status is QueueStatus.RUNNING for e in everything)
    waiting = sum(e.status is QueueStatus.QUEUED for e in everything)
    summary = (f"<p class='meta'>Server: {running} of {effective_max_concurrent_runs()} run "
               f"slots busy, {waiting} waiting. One run per project at a time.</p>")
    refresh = ("<meta http-equiv='refresh' content='5'>"
               if any(e.status in ACTIVE for e in mine) else "")
    head = "<tr><th>Status</th><th>Time</th><th>Requested by</th></tr>"
    table = "<table>" + head + "".join(map(_row, mine)) + "</table>"
    return refresh + theme.card(summary + table, title="Run queue")

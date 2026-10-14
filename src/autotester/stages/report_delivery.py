"""The report label (computed once) and the website inbox listing (TT7, R58, R22).

One job: decide what each viewer's "My reports" shows. `report_label` is the ONE place a run's
label is worked out; the inbox, the status page and any later message only read its result.
The listing is filtered through `authorize(report.view, project)` per row, so a report the
viewer may not read is absent (never a 403 row), and an all-blocked run never reads green.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from autotester.auth import accounts
from autotester.auth.access import authorize, resource_for
from autotester.delivery.inbox import DeliveryLog, delivery_key
from autotester.schema.auth import PermissionKey, Principal
from autotester.schema.delivery import (
    DeliveryChannel,
    DeliveryRecord,
    DeliveryStatus,
    InboxEntry,
    ReportLabel,
)
from autotester.schema.enums import Result
from autotester.schema.run_queue import ACTIVE, QueueEntry, QueueStatus
from autotester.schema.schedule import SlotOutcome, SlotRecord
from autotester.store.project_store import ProjectStore

log = logging.getLogger(__name__)


def report_label(status: QueueStatus, results: list[Result], planned: int) -> ReportLabel | None:
    """The label for a request. None while it is still queued or running.

    `green` only when every planned case has a verdict and all of them passed. A refused
    request is `blocked`; a failed or interrupted one is `failed`; otherwise the worst verdict
    present decides (failed, then blocked, then inconclusive), and missing verdicts read
    `low coverage`.
    """
    if status in ACTIVE:
        return None
    if status is QueueStatus.REFUSED:
        return ReportLabel.BLOCKED
    if status in (QueueStatus.FAILED, QueueStatus.INTERRUPTED):
        return ReportLabel.FAILED
    for result, label in ((Result.FAIL, ReportLabel.FAILED), (Result.BLOCKED, ReportLabel.BLOCKED),
                          (Result.INCONCLUSIVE, ReportLabel.INCONCLUSIVE)):
        if result in results:
            return label
    return ReportLabel.GREEN if results and len(results) >= planned else ReportLabel.LOW_COVERAGE


def _label(entry: QueueEntry, store: ProjectStore) -> ReportLabel | None:
    if entry.status is not QueueStatus.DONE:
        return report_label(entry.status, [], 0)
    results = [v.result for v in store.load_verdicts(entry.id)]
    run = store.load_run(entry.id)
    return report_label(entry.status, results, len(run.case_ids) if run else len(results))


def _link(entry: QueueEntry) -> str:
    base = f"/projects/{entry.project}"
    done = entry.status is QueueStatus.DONE
    return f"{base}/runs/{entry.id}" if done else f"{base}/test/{entry.id}"


# FAILED (enqueue raised, or the worker died) is a row too; the row carries no detail or URL,
# only a link to the schedule card, so a cause that held a secret never reaches the inbox.
_BLOCKED_SLOTS = (SlotOutcome.BLOCKED_NO_CREDENTIALS, SlotOutcome.REFUSED, SlotOutcome.FAILED,
                  SlotOutcome.INTERRUPTED)


def _slot_row(rec: SlotRecord) -> InboxEntry:
    """A blocked scheduled slot as an inbox row (TS5): no run exists, so the id is a stable
    digest of the slot key and the link goes to the schedule card, which names the reason."""
    digest = hashlib.sha256(rec.slot_key.encode()).hexdigest()[:12]
    return InboxEntry(project=rec.project, run_id=f"slot-{digest}", status=QueueStatus.REFUSED,
                      at=rec.recorded_at, scheduled=True, label=ReportLabel.BLOCKED,
                      link=f"/projects/{rec.project}/schedule")


def inbox_for(who: Principal, entries: Iterable[QueueEntry],
              store_for: Callable[[str], ProjectStore] = ProjectStore,
              slots: Iterable[SlotRecord] = ()) -> list[InboxEntry]:
    """Requests, plus blocked scheduled slots (`slots`), whose project the viewer holds
    `report.view` on, newest first."""
    allowed: dict[str, bool] = {}
    rows: list[InboxEntry] = []
    for entry in entries:
        if entry.project not in allowed:
            allowed[entry.project] = authorize(who, PermissionKey.REPORT_VIEW,
                                               resource_for(entry.project))
        if not allowed[entry.project]:
            continue
        scheduled = entry.trigger == "schedule"
        rows.append(InboxEntry(
            project=entry.project, run_id=entry.id, status=entry.status,
            at=entry.finished_at or entry.enqueued_at, scheduled=scheduled,
            started_by=None if scheduled else entry.requested_by,
            label=_label(entry, store_for(entry.project)), position=entry.position,
            link=_link(entry)))
    for rec in slots:
        if rec.outcome not in _BLOCKED_SLOTS:
            continue
        if rec.project not in allowed:
            allowed[rec.project] = authorize(who, PermissionKey.REPORT_VIEW,
                                             resource_for(rec.project))
        if allowed[rec.project]:
            rows.append(_slot_row(rec))
    return sorted(rows, key=lambda r: r.at, reverse=True)


def _recipient(entry: QueueEntry) -> str | None:
    """The user the report is for: the presser's id, or the schedule owner's (found by email)."""
    if entry.requested_by_id is not None:
        return str(entry.requested_by_id)
    owner = accounts.find_user(entry.requested_by) if entry.requested_by else None
    return str(owner.id) if owner else None


def record_inbox_delivery(entry: QueueEntry, delivery: DeliveryLog) -> bool:
    """Write the `inbox` DeliveryRecord when a request finishes (D-093 item 2). True if written.

    One per run and recipient: the write-once store makes a re-delivery a no-op. Nothing is
    written while the request is queued or running, or when it has no known recipient. The inbox
    list itself is still derived on read (`inbox_for`); this is the delivery's audit row.
    """
    user = _recipient(entry)
    if entry.status in ACTIVE or user is None:
        return False
    key = delivery_key(entry.id, DeliveryChannel.INBOX, user)
    if delivery.records_for_key(key):
        return False
    record = DeliveryRecord(run_id=entry.id, channel=DeliveryChannel.INBOX, recipient_user_id=user,
                            status=DeliveryStatus.SENT, attempts=1,
                            created_at=entry.finished_at or datetime.now(UTC))
    try:
        delivery.append(key, record)
    except FileExistsError:
        return False
    return True

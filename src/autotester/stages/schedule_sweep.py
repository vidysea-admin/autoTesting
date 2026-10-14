"""TS7: a scheduled run killed after its enqueue must not stay `enqueued` forever.

One job: amend the slot record of a run that is known (restart recovery) or provably (the
sweep) dead. `record_interrupted` is called by the server queue's `recover()` for each entry it
turns `interrupted`. `sweep_dead_enqueued` runs in the tick: a record still `enqueued` or
`catch_up` past `STALE_AFTER`, whose entry is not live in the queue and whose run never wrote a
`finished_at`, was cut off by a kill that no handler saw (the tick queue is memory-only), so it
is amended `interrupted`. Amendments are appended lines (`schedule_store.amend_record`).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from autotester.schema.run_queue import QueueEntry
from autotester.schema.schedule import SlotOutcome
from autotester.stages.schedule_store import amend_record, project_records_path, read_records
from autotester.store.project_store import ProjectStore

STALE_AFTER = timedelta(hours=3)
_OPEN = (SlotOutcome.ENQUEUED, SlotOutcome.CATCH_UP)


def record_interrupted(entry: QueueEntry, records_dir: Path) -> bool:
    """A scheduled entry the queue recovered as interrupted: say so on its slot record."""
    if entry.trigger != "schedule" or not entry.slot_key:
        return False
    return amend_record(project_records_path(records_dir, entry.project), entry.slot_key,
                        SlotOutcome.INTERRUPTED, "run interrupted: the process ended mid-run")


def sweep_dead_enqueued(slug: str, records_dir: Path, now: datetime,
                        live_ids: Callable[[], set[str]], store: ProjectStore,
                        stale_after: timedelta = STALE_AFTER) -> int:
    """Amend every stale open record of `slug` whose run is dead. Returns how many."""
    path = project_records_path(records_dir, slug)
    stale = [r for r in read_records(path)
             if r.outcome in _OPEN and r.entry_id and now - r.recorded_at > stale_after]
    if not stale:
        return 0
    live, amended = live_ids(), 0
    for rec in stale:
        run = store.load_run(rec.entry_id or "")
        if rec.entry_id in live or (run is not None and run.finished_at is not None):
            continue
        detail = f"no live run after {int(stale_after.total_seconds() // 3600)}h: interrupted"
        amended += amend_record(path, rec.slot_key, SlotOutcome.INTERRUPTED, detail)
    return amended

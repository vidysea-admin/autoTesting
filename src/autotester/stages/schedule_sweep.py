"""TS7: a scheduled run killed after its enqueue must not stay `enqueued` forever.

One job: amend the slot record of a run that is known (restart recovery) or provably (the
sweep) dead. `record_interrupted` is called by the server queue's `recover()` for each entry it
turns `interrupted`. `sweep_dead_enqueued` runs in the tick: a record still `enqueued` or
`catch_up` past `STALE_AFTER`, whose entry is not live in the queue and whose run never wrote a
`finished_at`, was cut off by a kill that no handler saw (the tick queue is memory-only), so it
is amended `interrupted`. The age is per slot (`stale_after_for`): `max(3h, min(bound + 30min,
24h))` where `bound` is the `wall_clock_s` the run recorded in `Run.bounds`; no recorded bound
keeps 3h, and the 24h cap stops an absurd approval (600000000 s) disabling the sweep forever.
Amendments are appended lines (`schedule_store.amend_record`).
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
STALE_MARGIN = timedelta(minutes=30)
STALE_CAP = timedelta(hours=24)
_OPEN = (SlotOutcome.ENQUEUED, SlotOutcome.CATCH_UP)


def record_interrupted(entry: QueueEntry, records_dir: Path) -> bool:
    """A scheduled entry the queue recovered as interrupted: say so on its slot record."""
    if entry.trigger != "schedule" or not entry.slot_key:
        return False
    return amend_record(project_records_path(records_dir, entry.project), entry.slot_key,
                        SlotOutcome.INTERRUPTED, "run interrupted: the process ended mid-run")


def stale_after_for(bound_s: float | None, floor: timedelta = STALE_AFTER) -> timedelta:
    """How old a slot must be before it may be swept: its own run bound plus a margin, never
    below `floor` (3h) and never above 24h. Unknown or non-positive bound: `floor`."""
    if bound_s is None or not bound_s > 0:
        return floor
    return max(floor, min(timedelta(seconds=min(bound_s, STALE_CAP.total_seconds()))
                          + STALE_MARGIN, STALE_CAP))


def sweep_dead_enqueued(slug: str, records_dir: Path, now: datetime,
                        live_ids: Callable[[], set[str]], store: ProjectStore,
                        stale_after: timedelta = STALE_AFTER) -> int:
    """Amend every stale open record of `slug` whose run is dead. Returns how many."""
    path = project_records_path(records_dir, slug)
    open_recs = [r for r in read_records(path)
                 if r.outcome in _OPEN and r.entry_id and now - r.recorded_at > stale_after]
    if not open_recs:
        return 0
    live, amended = live_ids(), 0
    for rec in open_recs:
        run = store.load_run(rec.entry_id or "")
        if rec.entry_id in live or (run is not None and run.finished_at is not None):
            continue
        bound = run.bounds.wall_clock_s if run is not None and run.bounds else None
        limit = stale_after_for(bound, stale_after)
        if now - rec.recorded_at <= limit:
            continue  # a legitimate long run, still inside its own approved wall clock
        detail = f"no live run after {int(limit.total_seconds() // 3600)}h: interrupted"
        amended += amend_record(path, rec.slot_key, SlotOutcome.INTERRUPTED, detail)
    return amended

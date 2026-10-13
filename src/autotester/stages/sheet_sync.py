"""SHEET SYNC: try to sync a project's bugs to its sheet, and turn any failure into a status (TB12).

Its one job is the outage rule: a sheet error never reaches the run. `try_sync` runs the guarded
write of `stages/sheet_write.py` and, on any exception, records `sync_status=error` with the
scrubbed last error and a retry time; the in-product tracker (`BugStore`) is not touched either
way. The last status and what was last written (so a retry converges, TB11) are one file each under
`projects/<slug>/`. The client is a seam; the live path stays refused by `write_confirmed_plan`.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

from autotester.core.paths import ProjectPaths
from autotester.schema.sheet_plan import PlanConfirmation, SheetColumns, SyncMemory
from autotester.schema.tracked_bug import TrackedBug
from autotester.schema.tracker_binding import SyncStatus
from autotester.stages.sheet_plan import Scrub
from autotester.stages.sheet_write import SheetClient, write_confirmed_plan
from autotester.store.filestore import read_json, write_json

STATUS_FILE, MEMORY_FILE = "sheet_sync.json", "sheet_sync_memory.json"
RETRY_AFTER = timedelta(minutes=15)


def load_status(slug: str, root: Path | None = None) -> SyncStatus | None:
    return read_json(ProjectPaths(slug, root).dir / STATUS_FILE, SyncStatus)


def try_sync(slug: str, client: SheetClient, bugs: Iterable[TrackedBug], cols: SheetColumns,
             confirmation: PlanConfirmation | None, scrub: Scrub, now: datetime,
             root: Path | None = None) -> SyncStatus:
    """Write the confirmed plan; never raise. The outcome is saved and returned."""
    base = ProjectPaths(slug, root).dir
    memory = read_json(base / MEMORY_FILE, SyncMemory) or SyncMemory()
    try:
        write_confirmed_plan(client, bugs, cols, memory, scrub, confirmation)
        status = SyncStatus(sync_status="ok", at=now)
    except Exception as exc:  # TB12: any sheet error is a status, not a failure of the run
        status = SyncStatus(sync_status="error", at=now, retry_at=now + RETRY_AFTER,
                            last_error=scrub(f"{type(exc).__name__}: {exc}")[:500])
    write_json(base / MEMORY_FILE, memory)  # rows written before a crash are remembered
    write_json(base / STATUS_FILE, status)
    return status

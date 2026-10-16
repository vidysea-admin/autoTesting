"""The server-wide run queue (T-203, D-072 G6, hosting.md HO15-HO20): pressing Test returns at once.

One job: decide WHEN a run may start. At most `effective_max_concurrent_runs()` runs execute at
once across the server (default 2, admin-set, re-read on every dispatch) and a project never has
two at a time (they would fight over its Chromium profile and shared test account); the rest wait
first come first served and show as `queued`. HOW a run executes stays in `ui/run_execution.py`
and `stages/parallel_run.py`: that is the per-run case width, a different concept from this
across-runs limit; the only bridge is `planning()`, which makes concurrent runs share one RAM
budget. The queue is a file under the data root, so it survives a restart: a run that was
`running` when the process died becomes `interrupted` (never re-executed), waiting runs resume.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from autotester.core.ids import ulid
from autotester.core.paths import data_root, team_path
from autotester.delivery.inbox import DeliveryLog
from autotester.schema.run_queue import ACTIVE, QueueEntry, QueueStatus, RunQueueFile
from autotester.schema.team_enums import RunVia
from autotester.stages.report_delivery import record_inbox_delivery
from autotester.stages.schedule_store import QueueUnreadable
from autotester.stages.schedule_sweep import record_interrupted
from autotester.store.filestore import read_json, write_json
from autotester.store.server_settings import effective_max_concurrent_runs

__all__ = ["QueueFull", "RunQueue", "RunRefused", "get_queue", "persisted_entries", "set_queue",
           "set_runner"]

MAX_WAITING_PER_PROJECT = 3
"""A project may have this many presses waiting behind its running one; the next is refused
with 429 (a person mashing the button, or a schedule that outpaces its runs) -- never dropped
silently."""
KEEP_FINISHED = 20
log = logging.getLogger(__name__)
Runner = Callable[[QueueEntry], None]
Spawn = Callable[[Callable[[], None]], None]


class QueueFull(Exception):
    """This project already has `MAX_WAITING_PER_PROJECT` presses waiting."""


class RunRefused(Exception):
    """Raised by a runner when a gate says no at start time; `str(exc)` is the human reason."""


def _thread_spawn(job: Callable[[], None]) -> None:
    threading.Thread(target=job, name="autotester-run", daemon=True).start()


_runner: Runner | None = None


def set_runner(runner: Runner) -> None:
    """Register what executes one queue entry (`ui/routes_runs.py` does it at import)."""
    global _runner
    _runner = runner


def _registered_runner(entry: QueueEntry) -> None:
    if _runner is None:
        raise RuntimeError("no run executor registered")
    _runner(entry)


def _queue_file() -> Path:
    return data_root() / ".work" / "run_queue.json"


class RunQueue:
    """Thread-safe scheduler. `limit`, `spawn` and `runner` are seams: tests need no threads."""

    def __init__(self, limit: Callable[[], int] = effective_max_concurrent_runs,
                 spawn: Spawn = _thread_spawn, runner: Runner = _registered_runner,
                 path: Callable[[], Path] | None = None,
                 delivery: Callable[[], Path] | None = None,
                 max_waiting: int = MAX_WAITING_PER_PROJECT) -> None:
        self._limit, self._spawn, self._runner = limit, spawn, runner
        self._path, self._max_waiting = path, max_waiting
        self._delivery = delivery
        self._lock = threading.Lock()
        self._plan_lock = threading.Lock()
        self._entries: list[QueueEntry] = []
        self._grants: dict[str, float] = {}

    # -- public ----------------------------------------------------------------------------
    def submit(self, project: str, *, requested_by: str | None = None,
               trigger: str = "button", run_id: str | None = None,
               priorities: list[str] | None = None, slot_key: str | None = None,
               via: RunVia | None = None, requested_by_id: int | None = None) -> QueueEntry:
        """Enqueue a press and start whatever the limits allow. Raises `QueueFull`.
        `run_id`: the caller mints it only after every gate passed (a refused press mints none).
        `slot_key` (HO23): a schedule slot has at most one entry; asking again returns it."""
        starts: list[QueueEntry] = []
        with self._lock:
            held = next((e.id for e in self._entries if slot_key and e.slot_key == slot_key), None)
            if held is None:
                waiting = sum(e.project == project and e.status is QueueStatus.QUEUED
                              for e in self._entries)
                if waiting >= self._max_waiting:
                    raise QueueFull(f"{waiting} runs of '{project}' are already waiting; "
                                    "wait for one to start")
                entry = QueueEntry(id=run_id or f"run-{ulid()}", project=project,
                                   requested_by=requested_by, requested_by_id=requested_by_id,
                                   trigger=trigger,
                                   slot_key=slot_key, priorities=priorities, via=via)
                self._entries.append(entry)
                held, starts = entry.id, self._take_startable()
                self._persist()
        self._launch(starts)
        return self._view(held)

    def recover(self) -> None:
        """After a (re)start: a `running` row becomes `interrupted`; waiting rows resume."""
        with self._lock:
            self._entries = self._load()
            for entry in self._entries:
                if entry.status is QueueStatus.RUNNING:
                    entry.status = QueueStatus.INTERRUPTED
                    entry.finished_at = datetime.now(UTC)
                    entry.reason = ("the server restarted while this run was in progress; "
                                    "it was not re-run -- press Test again")
            starts = self._take_startable()
            self._persist()
        for entry in self._entries:
            self._deliver(entry)
            self._mark_slot_interrupted(entry)
        self._launch(starts)

    def _mark_slot_interrupted(self, entry: QueueEntry) -> None:
        """TS7: a scheduled run recovered as interrupted says so on its slot record."""
        if entry.status is not QueueStatus.INTERRUPTED:
            return
        try:
            from autotester.stages.schedule_wiring import schedule_paths
            record_interrupted(entry, schedule_paths().records)
        except Exception:
            log.exception("slot record for %s could not be marked interrupted", entry.id)

    def nudge(self) -> None:
        """Start whatever the limits allow now (the admin raised the cap; nothing else changed)."""
        with self._lock:
            starts = self._take_startable()
            self._persist()
        self._launch(starts)

    def snapshot(self, project: str | None = None) -> list[QueueEntry]:
        """Running, then queued in order (with `position`), then recent finished, newest first."""
        with self._lock:
            queued = [e for e in self._entries if e.status is QueueStatus.QUEUED]
            out = [e.model_copy(update={"position": queued.index(e) + 1 if e in queued else 0})
                   for e in self._entries if project in (None, e.project)]
        rank = {QueueStatus.RUNNING: 0, QueueStatus.QUEUED: 1}
        out.sort(key=lambda e: (rank.get(e.status, 2), e.position,
                                -(e.finished_at or e.enqueued_at).timestamp()))
        return out

    @contextlib.contextmanager
    def planning(self, run_id: str) -> Iterator[float]:
        """Serialise `plan_parallel_run` across runs and yield the MB other running runs already
        hold, so two runs starting at once plan against one budget (HO20), not two."""
        with self._plan_lock:
            with self._lock:
                reserved = sum(mb for rid, mb in self._grants.items() if rid != run_id)
            yield reserved

    def grant(self, run_id: str, megabytes: float) -> None:
        """Record what the plan just decided this run will hold (call inside `planning`)."""
        with self._lock:
            self._grants[run_id] = megabytes

    # -- internals -------------------------------------------------------------------------
    def _view(self, entry_id: str) -> QueueEntry:
        return next(e for e in self.snapshot() if e.id == entry_id)

    def _take_startable(self) -> list[QueueEntry]:
        """Mark and return every queued entry that may start now (caller holds the lock)."""
        starts: list[QueueEntry] = []
        while True:
            running = [e for e in self._entries if e.status is QueueStatus.RUNNING]
            if len(running) >= self._limit():
                return starts
            busy = {e.project for e in running}
            nxt = next((e for e in self._entries
                        if e.status is QueueStatus.QUEUED and e.project not in busy), None)
            if nxt is None:
                return starts
            nxt.status, nxt.started_at = QueueStatus.RUNNING, datetime.now(UTC)
            starts.append(nxt)

    def _launch(self, starts: list[QueueEntry]) -> None:
        for entry in starts:  # outside the lock: an inline spawner re-enters `_finish`
            self._spawn(lambda e=entry: self._work(e))

    def _work(self, entry: QueueEntry) -> None:
        status, reason = QueueStatus.DONE, None
        try:
            self._runner(entry)
        except RunRefused as exc:
            status, reason = QueueStatus.REFUSED, str(exc)
        except Exception as exc:
            status, reason = QueueStatus.FAILED, type(exc).__name__
            log.exception("run %s for project %s failed", entry.id, entry.project)
        except BaseException as exc:  # SystemExit, CancelledError: cut off, so never `done`
            status, reason = QueueStatus.INTERRUPTED, type(exc).__name__
            raise
        finally:
            self._finish(entry, status, reason)

    def _finish(self, entry: QueueEntry, status: QueueStatus, reason: str | None) -> None:
        with self._lock:
            entry.status, entry.reason = status, reason
            entry.finished_at = datetime.now(UTC)
            self._grants.pop(entry.id, None)
            finished = [e for e in self._entries if e.status not in ACTIVE]
            for old in finished[:-KEEP_FINISHED]:
                self._entries.remove(old)
            starts = self._take_startable()
            self._persist()
        self._deliver(entry)
        self._launch(starts)

    def _deliver(self, entry: QueueEntry) -> None:
        """Write the entry's `inbox` DeliveryRecord (idempotent). Never raises: a full disk must
        not stop scheduling."""
        if self._delivery is None or entry.status in ACTIVE:
            return
        try:
            record_inbox_delivery(entry, DeliveryLog(self._delivery()))
        except Exception:
            log.exception("inbox delivery record for %s could not be written", entry.id)

    def _load(self) -> list[QueueEntry]:
        if self._path is None:
            return list(self._entries)
        try:
            stored = read_json(self._path(), RunQueueFile)
        except ValueError as exc:
            log.warning("run queue file unreadable, starting empty: %s", exc)
            return []
        return list(stored.entries) if stored else []

    def _persist(self) -> None:
        """Write the queue file for the next restart. A failed write (full or read-only disk)
        is logged, never raised: the caller has already marked entries `running` and must go
        on to launch them, or they would hold a slot with no worker until a restart (AT-865)."""
        try:
            self._save()
        except Exception:
            log.exception("run queue file could not be written; scheduling continues in memory")

    def _save(self) -> None:
        if self._path is not None:
            write_json(self._path(), RunQueueFile(entries=self._entries))


_QUEUE: RunQueue | None = None
_QUEUE_LOCK = threading.Lock()


def get_queue() -> RunQueue:
    """The process-wide queue, recovered from disk on first use (one uvicorn worker per server)."""
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is None:
            queue = RunQueue(path=_queue_file, delivery=lambda: team_path("delivery"))
            queue.recover()
            _QUEUE = queue
        return _QUEUE


def set_queue(queue: RunQueue) -> None:
    """Install the process-wide queue. The scheduler's tick process uses this to run its own
    in-memory queue, so it never `recover()`s (and so never interrupts) the server's one."""
    global _QUEUE
    with _QUEUE_LOCK:
        _QUEUE = queue


def persisted_entries() -> list[QueueEntry]:
    """The server's queue file, read only: another process's view, for the scheduler's overlap
    check. Never `recover()`s, never writes. An absent file is an empty queue; an unreadable or
    corrupt one raises `QueueUnreadable` (busy is unknown, so the slot is skipped, not run)."""
    try:
        stored = read_json(_queue_file(), RunQueueFile)
    except (ValueError, OSError) as exc:
        raise QueueUnreadable(f"the run queue file cannot be read ({type(exc).__name__})") from exc
    return list(stored.entries) if stored else []

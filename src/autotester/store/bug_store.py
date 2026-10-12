"""BUG STORE: the set of bug events, one file each, under a caller-given directory (T-199a/b, TB6).

Its one job is persistence. The only thing stored is the event; a bug is `fold(events)`, so history
is never rewritten. An event is one file `bug_events/<event_id>@<time>.json`, written whole by
`store/filestore.py::write_json` (the repo's atomic writer; no second lock helper, no
`fcntl`/`flock`, R65). Nothing is ever appended to a shared file: on Windows concurrent appends from
two processes lose and tear lines (measured in review, 2026-10-11), so a shared log is not safe
without a lock the repo does not have. Distinct files cannot tear each other.

Why that converges: the event id is `(bug_key, ref, kind)`, so the same event written twice is the
same file with the same bytes. If two processes race the same fact with two different times, both
files are kept (the time is in the name, so neither replaces the other) and `fold` counts the fact
once, at its earliest applied time: the result is a function of the set of files, whichever
process wrote first (P8). `fold` orders by event
time, not by write order, so late-arriving events give the same bugs.

A file that is not a valid event (torn, zero-length after a crash, or named for another event) does
not stop the store (P4): the valid events are kept, the file is reported by name in `snapshot().bad`
and never deleted, and applying the same event again repairs its own file. A persistent permission
denial is not corruption and still raises. One call reads each file once (P3): `snapshot()` is the
read, and `apply_all(..., snapshot=snap)` reuses it.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from autotester.schema.base import utc_now
from autotester.schema.bug_run import BadEventFile, BugSnapshot
from autotester.schema.tracked_bug import DEFAULT_CLOSE_PASSES, BugEvent, TrackedBug
from autotester.stages.bug_loop import (
    Applied,
    Effect,
    Refusal,
    judge,
    keeps,
    order_key,
    storable,
    trace,
)
from autotester.store.filestore import read_json, write_json

EVENTS_DIR = "bug_events"


def file_name(event: BugEvent) -> str:
    """The event's file. The time is part of the name so two writers of one fact at two times
    leave two files, never one overwriting the other (P8)."""
    return f"{event.event_id}@{event.at.astimezone(UTC):%Y%m%dT%H%M%S%f}Z.json"


def _read(path: Path) -> BugEvent | None:
    """`read_json`, retried briefly: on Windows a reader can hit a sharing violation while a racing
    writer of the same event replaces the file. Anything else, and a persistent denial, raises."""
    for attempt in range(20):
        try:
            return read_json(path, BugEvent)
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.01)
    return None


class BugStore:
    def __init__(self, root: Path, *, close_passes: int = DEFAULT_CLOSE_PASSES,
                 clock: Callable[[], datetime] = utc_now) -> None:
        if close_passes < 1:
            raise ValueError("close_passes must be at least 1")
        self.dir = Path(root) / EVENTS_DIR
        self.close_passes = close_passes
        self.clock = clock

    def snapshot(self) -> BugSnapshot:
        """Read every event file once: the valid events, their fold, and the files that were not
        valid (named, never deleted, never fatal: P4)."""
        found: list[BugEvent] = []
        bad: list[BadEventFile] = []
        for path in sorted(self.dir.glob("bev_*.json")):
            try:
                event = _read(path)
            except ValueError as exc:
                bad.append(BadEventFile(name=path.name, why=_why(exc, path)))
                continue
            if event is None:  # removed between the listing and the read
                continue
            if path.name != file_name(event):
                bad.append(BadEventFile(name=path.name, why="file name is not this event's name"))
                continue
            found.append(event)
        found.sort(key=order_key)
        return BugSnapshot(events=found, bad=bad,
                           bugs=trace(found, close_passes=self.close_passes)[0])

    def events(self) -> list[BugEvent]:
        """Every valid stored event, oldest first (event time, ties by rank then id)."""
        return self.snapshot().events

    def bugs(self) -> dict[str, TrackedBug]:
        return self.snapshot().bugs

    def get(self, bug_key: str) -> TrackedBug | None:
        return self.bugs().get(bug_key)

    def history(self, bug_key: str) -> list[BugEvent]:
        return [e for e in self.events() if e.bug_key == bug_key]

    def apply(self, event: BugEvent) -> Applied:
        """Store the event if it is new and report what it did. Applying it again writes nothing."""
        return self.apply_all([event])[0]

    def apply_all(self, events: list[BugEvent], *, snapshot: BugSnapshot | None = None,
                  ) -> list[Applied]:
        """Store each new event, then judge them in time order together with what was already
        there. After a crash, call again with the same list: written events are duplicates (TB6).
        The log is read once; pass a `snapshot` the caller already holds to not read it at all."""
        snap = snapshot if snapshot is not None else self.snapshot()
        known = {e.event_id for e in snap.events}
        now = self.clock()
        fresh: dict[str, BugEvent] = {}
        refused: dict[int, Refusal] = {}
        for index, event in enumerate(events):
            why = storable(event, now)
            if why is not None:
                refused[index] = why
            elif keeps(event) and event.event_id not in known and event.event_id not in fresh:
                self._write(event)
                fresh[event.event_id] = event
        bugs, judged = trace([*snap.events, *fresh.values()], close_passes=self.close_passes)
        out: list[Applied] = []
        for index, e in enumerate(events):
            again = (e.event_id in known) or any(
                p.event_id == e.event_id and i not in refused for i, p in enumerate(events[:index]))
            out.append(self._report(e, again, refused.get(index), judged, bugs.get(e.bug_key)))
        return out

    def _write(self, event: BugEvent) -> None:
        target = self.dir / file_name(event)
        if target.exists() and self._is_valid(target, event):
            return
        try:
            write_json(target, event)
        except OSError:
            if not (target.exists() and self._is_valid(target, event)):
                raise  # a racing writer of the same event won; anything else is real

    @staticmethod
    def _is_valid(path: Path, event: BugEvent) -> bool:
        try:
            return _read(path) == event
        except ValueError:
            return False

    def _report(self, event: BugEvent, was_known: bool, refusal: Refusal | None,
                judged: dict[str, Applied], bug: TrackedBug | None) -> Applied:
        if refusal is not None:
            return Applied(Effect.REFUSED, refusal, bug)
        if was_known:
            return Applied(Effect.DUPLICATE, None, bug)
        if not keeps(event):
            return judge(bug, event, close_passes=self.close_passes)
        return judged[event.event_id]


def _why(exc: ValueError, path: Path) -> str:
    first = (str(exc).splitlines() or ["unreadable"])[0].replace(str(path), path.name)
    return first[:300]

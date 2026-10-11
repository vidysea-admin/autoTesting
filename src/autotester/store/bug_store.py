"""BUG STORE: the set of bug events, one file each, under a caller-given directory (T-199a, TB6).

Its one job is persistence. The only thing stored is the event; a bug is `fold(events)`, so history
is never rewritten. An event is one file `bug_events/<event_id>.json`, written whole by
`store/filestore.py::write_json` (the repo's atomic writer; no second lock helper, no
`fcntl`/`flock`, R65). Nothing is ever appended to a shared file: on Windows concurrent appends from
two processes lose and tear lines (measured in review, 2026-10-11), so a shared log is not safe
without a lock the repo does not have. Distinct files cannot tear each other.

Why that converges: the event id is `(bug_key, ref)`, so the same event written twice is the same
file with the same bytes; and `fold` orders by event time, not by write order, so racing writers
and late-arriving events give the same bugs. A file that fails to parse raises with its path.
"""

from __future__ import annotations

import time
from pathlib import Path

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
    def __init__(self, root: Path, *, close_passes: int = DEFAULT_CLOSE_PASSES) -> None:
        if close_passes < 1:
            raise ValueError("close_passes must be at least 1")
        self.dir = Path(root) / EVENTS_DIR
        self.close_passes = close_passes

    def _path(self, event_id: str) -> Path:
        return self.dir / f"{event_id}.json"

    def events(self) -> list[BugEvent]:
        """Every stored event, oldest first (event time, ties by id)."""
        found = [_read(p) for p in sorted(self.dir.glob("bev_*.json"))]
        return sorted((e for e in found if e is not None), key=order_key)

    def bugs(self) -> dict[str, TrackedBug]:
        return trace(self.events(), close_passes=self.close_passes)[0]

    def get(self, bug_key: str) -> TrackedBug | None:
        return self.bugs().get(bug_key)

    def history(self, bug_key: str) -> list[BugEvent]:
        return [e for e in self.events() if e.bug_key == bug_key]

    def apply(self, event: BugEvent) -> Applied:
        """Store the event if it is new and report what it did. Applying it again writes nothing."""
        return self.apply_all([event])[0]

    def apply_all(self, events: list[BugEvent]) -> list[Applied]:
        """Store each new event, then judge them in time order together with what was already
        there. After a crash, call again with the same list: written events are duplicates (TB6)."""
        known = {p.stem for p in self.dir.glob("bev_*.json")}
        fresh: set[str] = set()
        refused: dict[int, Refusal] = {}
        for index, event in enumerate(events):
            why = storable(event)
            if why is not None:
                refused[index] = why
            elif keeps(event) and event.event_id not in known | fresh:
                self._write(event)
                fresh.add(event.event_id)
        bugs, judged = trace(self.events(), close_passes=self.close_passes)
        out: list[Applied] = []
        for index, e in enumerate(events):
            again = (e.event_id in known and e.event_id not in fresh) or any(
                p.event_id == e.event_id and i not in refused for i, p in enumerate(events[:index]))
            out.append(self._report(e, again, refused.get(index), judged, bugs.get(e.bug_key)))
        return out

    def _write(self, event: BugEvent) -> None:
        target = self._path(event.event_id)
        if target.exists():
            return
        try:
            write_json(target, event)
        except OSError:
            if not target.exists():  # a racing writer of the same event won; anything else is real
                raise

    def _report(self, event: BugEvent, was_known: bool, refusal: Refusal | None,
                judged: dict[str, Applied], bug: TrackedBug | None) -> Applied:
        if refusal is not None:
            return Applied(Effect.REFUSED, refusal, bug)
        if was_known:
            return Applied(Effect.DUPLICATE, None, bug)
        if not keeps(event):
            return judge(bug, event, close_passes=self.close_passes)
        return judged[event.event_id]

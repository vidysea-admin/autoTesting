"""BUG STORE: the append-only log of bug events under a directory the caller names (T-199a, TB6).

Its one job is persistence. The log is the only thing stored: a bug is `fold(events)`, never a row
that can be edited, so history is never rewritten and an unchanged event writes nothing. Reads and
appends go through `store/filestore.py` (`read_jsonl`, `append_jsonl`), the repo's one place for
jsonl; no second lock helper and no `fcntl`/`flock` (R65).

Why no lock is needed: an append is one whole line, and `fold` is the single interpreter. Two
writers racing on the same event both append it and `fold` keeps the first; two racing on different
events are applied in file order. The result `apply` returns is what it saw when it looked; the
state is always `bugs()`. A torn tail line (power cut mid-append) is not hidden: reading raises
with `path:line`, and the file is human-editable (C6).
"""

from __future__ import annotations

from pathlib import Path

from autotester.schema.tracked_bug import DEFAULT_CLOSE_PASSES, BugEvent, TrackedBug
from autotester.stages.bug_loop import Applied, Effect, fold, judge
from autotester.store.filestore import append_jsonl, read_jsonl

EVENTS_FILE = "bug_events.jsonl"


class BugStore:
    def __init__(self, root: Path, *, close_passes: int = DEFAULT_CLOSE_PASSES) -> None:
        if close_passes < 1:
            raise ValueError("close_passes must be at least 1")
        self.path = Path(root) / EVENTS_FILE
        self.close_passes = close_passes

    def events(self) -> list[BugEvent]:
        """Every event, in file order."""
        return read_jsonl(self.path, BugEvent)

    def bugs(self) -> dict[str, TrackedBug]:
        return fold(self.events(), close_passes=self.close_passes)

    def get(self, bug_key: str) -> TrackedBug | None:
        return self.bugs().get(bug_key)

    def history(self, bug_key: str) -> list[BugEvent]:
        """The events behind one bug, oldest first. Includes events a race later made redundant."""
        return [e for e in self.events() if e.bug_key == bug_key]

    def apply(self, event: BugEvent) -> Applied:
        """Judge one event against the log and append it only if it moved a bug. Applying the same
        event again (same `bug_key` and `ref`) changes nothing."""
        return self.apply_all([event])[0]

    def apply_all(self, events: list[BugEvent]) -> list[Applied]:
        """Apply in order, one append per applied event. After a crash, call again with the same
        list: the events already written are duplicates and the rest are applied (TB6)."""
        existing = self.events()
        bugs = fold(existing, close_passes=self.close_passes)
        seen = {e.event_id for e in existing}
        results: list[Applied] = []
        for event in events:
            result = judge(bugs.get(event.bug_key), event, close_passes=self.close_passes,
                           seen=seen)
            if result.effect is Effect.APPLIED and result.bug is not None:
                append_jsonl(self.path, event)
                bugs[event.bug_key] = result.bug
                seen.add(event.event_id)
            results.append(result)
        return results

"""SHEET PLAN: from the open bugs and one read of the sheet, the exact cells a sync would write.

Its one job is the pure plan and its human rendering (T-199b dry run; TB9-TB11, TB13 in part).
No client, no file, no network: the caller reads the sheet and passes the read in, so nothing here
can write to anything.

One row per live bug, located by the bug-key column. A bug that already has a row keeps it even
after it is fixed or stale (its status cell is updated), but a closed bug that was never in the
sheet is not added. Only columns the mapping names are ever written; every other column is left
exactly as a human has it. A cell is overwritten only if it still holds what we last wrote (or is
empty and we never wrote it); any other value is a human edit, and it becomes a reported conflict,
never a write (TB10). Every value passes `scrub` before it is planned or shown (TB13).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from autotester.schema.sheet_plan import (
    CellChange,
    CellConflict,
    PlanRow,
    SheetColumns,
    SheetPlan,
    SheetState,
    SyncMemory,
)
from autotester.schema.tracked_bug import BugStatus, TrackedBug

LIVE = (BugStatus.OPEN, BugStatus.REOPENED)
Scrub = Callable[[str], str]


class PlanRefused(ValueError):
    """The sheet cannot be planned against: a mapped column is not in its header (the mapping is
    stale, TB8) or the header repeats a name."""


def bug_values(bug: TrackedBug) -> dict[str, str]:
    """A bug as the strings a sheet cell holds, keyed by owned field."""
    return {
        "bug_key": bug.bug_key, "title": bug.title, "severity": bug.severity.value,
        "screen": bug.screen or "", "status": bug.status.value, "assignee": bug.assignee or "",
        "first_seen": bug.first_seen.strftime("%Y-%m-%d %H:%M UTC"),
        "last_seen": bug.last_seen.strftime("%Y-%m-%d %H:%M UTC"), "count": str(bug.count),
    }


def _cell(row: list[str], index: int) -> str:
    return row[index] if index < len(row) else ""


def _index(sheet: SheetState, cols: SheetColumns) -> dict[str, int]:
    missing = [h for h in cols.columns.values() if h not in sheet.header]
    if missing:
        raise PlanRefused(f"mapped column(s) not in the sheet header: {missing}; re-map first")
    named = [h for h in sheet.header if h]
    if len(set(named)) != len(named):
        raise PlanRefused("the sheet header repeats a column name; the mapping is ambiguous")
    return {field: sheet.header.index(h) for field, h in cols.columns.items()}


def _located(sheet: SheetState, key_at: int) -> dict[str, list[int]]:
    """bug key -> sheet row numbers (the header is row 1)."""
    found: dict[str, list[int]] = {}
    for offset, row in enumerate(sheet.rows):
        if key := _cell(row, key_at).strip():
            found.setdefault(key, []).append(offset + 2)
    return found


def _row_for(bug: TrackedBug, rows: list[int], sheet: SheetState, index: dict[str, int],
             cols: SheetColumns, memory: SyncMemory, scrub: Scrub) -> PlanRow | None:
    want = {cols.columns[f]: scrub(v) for f, v in bug_values(bug).items() if f in cols.columns}
    if not rows:
        return PlanRow(action="append", bug_key=bug.bug_key,
                       changes=[CellChange(column=h, before="", after=v) for h, v in want.items()])
    if len(rows) > 1:
        return PlanRow(action="conflict", bug_key=bug.bug_key, row_number=rows[0],
                       note=f"the key is on {len(rows)} rows {rows}; none is written")
    row, mine = sheet.rows[rows[0] - 2], memory.written.get(bug.bug_key, {})
    changes: list[CellChange] = []
    conflicts: list[CellConflict] = []
    for field, header in cols.columns.items():
        have, new, last = _cell(row, index[field]), want[header], mine.get(header)
        if have == new:
            continue
        if have == last or (last is None and have == ""):
            changes.append(CellChange(column=header, before=have, after=new))
        else:
            conflicts.append(CellConflict(column=header, sheet_has=have, we_last_wrote=last,
                                          we_would_write=new))
    if not changes and not conflicts:
        return None
    return PlanRow(action="update" if changes else "conflict", bug_key=bug.bug_key,
                   row_number=rows[0], changes=changes, conflicts=conflicts)


def plan_sync(bugs: Iterable[TrackedBug], sheet: SheetState, cols: SheetColumns,
              memory: SyncMemory, scrub: Scrub) -> SheetPlan:
    """The rows a sync would write now. Deterministic: bugs in (first seen, key) order."""
    index = _index(sheet, cols)
    located = _located(sheet, index["bug_key"])
    rows: list[PlanRow] = []
    unchanged = 0
    for bug in sorted(bugs, key=lambda b: (b.first_seen, b.bug_key)):
        have = located.get(bug.bug_key, [])
        if bug.status not in LIVE and not have:
            continue
        row = _row_for(bug, have, sheet, index, cols, memory, scrub)
        if row is None:
            unchanged += 1
        else:
            rows.append(row)
    return SheetPlan(sheet_id=cols.sheet_id, tab=cols.tab, rows=rows, unchanged=unchanged)


def render_plan(plan: SheetPlan, *, written: bool = False) -> str:
    """The plan as exact cells for a human. Values are shown with `repr` so a space or an empty
    cell is visible. The first line says whether anything was written."""
    state = "WRITTEN" if written else "DRY RUN - nothing has been written"
    lines = [state, f"sheet {plan.sheet_id} / tab {plan.tab!r} / plan {plan.plan_hash}",
             f"{len(plan.writes)} row(s) to write, "
             f"{len(plan.rows) - len(plan.writes)} blocked, {plan.unchanged} already match"]
    for row in plan.rows:
        where = "new row at the end" if row.row_number is None else f"row {row.row_number}"
        lines.append(f"{row.action.upper():8} {row.bug_key}  ({where})")
        lines += [f"    {c.column}: {c.before!r} -> {c.after!r}" for c in row.changes]
        lines += [f"    CONFLICT {c.column}: the sheet has {c.sheet_has!r}"
                  f" (we last wrote {c.we_last_wrote!r}); would write {c.we_would_write!r};"
                  " NOT WRITTEN" for c in row.conflicts]
        if row.note:
            lines.append(f"    {row.note}")
    return "\n".join(lines)

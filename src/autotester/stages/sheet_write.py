"""SHEET WRITE: the sheet client interface, the dry run, and the guarded write of a confirmed plan.

Its one job is the only path from a `SheetPlan` to a sheet (T-199b; TB9, TB10, TB11 in part). The
client is an interface (`SheetClient`) and the only implementation in this repo is a test fake: no
Google call, no `gws` call and no network exists here. The interface has no delete and no clear.

A write needs, in this order, and fails closed at each step with zero write calls:
  1. a client that is not live. A live client is refused outright: the owner has not approved any
     write to a real tracker (`qa/gates/t199-first-live-write.md` is OPEN), and no confirmed
     first-write record exists in this slice to lift that;
  2. a `PlanConfirmation`;
  3. a plan re-computed now from the bugs and a fresh read of the sheet, whose hash is the
     confirmed one. A plan that changed since it was shown (a bug moved, a human edited a cell, one
     cell differs) needs a new confirmation.
Retry after a crash re-plans: rows already written no longer appear, so every row lands once (TB11),
and the smaller plan is confirmed again.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from autotester.schema.sheet_plan import (
    PlanConfirmation,
    SheetColumns,
    SheetPlan,
    SheetState,
    SyncMemory,
)
from autotester.schema.tracked_bug import TrackedBug
from autotester.stages.sheet_plan import Scrub, plan_sync, render_plan


class SheetClient(Protocol):
    """What a sheet must offer. Read, append a row, update named cells of one row. Nothing else:
    there is no delete, no clear and no way to touch a column that is not named."""

    live: bool

    def read(self, sheet_id: str, tab: str) -> SheetState: ...

    def append_row(self, sheet_id: str, tab: str, cells: dict[str, str]) -> None: ...

    def update_cells(self, sheet_id: str, tab: str, row_number: int,
                     cells: dict[str, str]) -> None: ...


class WriteRefused(RuntimeError):
    """A write was not made. Nothing has been written when this is raised."""


class LiveWriteRefused(WriteRefused):
    """The client is a real sheet. No first live write has been approved."""


class NotConfirmed(WriteRefused):
    """There is no confirmation of the plan."""


class PlanChanged(WriteRefused):
    """The plan now is not the plan that was confirmed."""


def dry_run(client: SheetClient, bugs: Iterable[TrackedBug], cols: SheetColumns,
            memory: SyncMemory, scrub: Scrub) -> tuple[SheetPlan, str]:
    """The plan and its rendering. Calls `client.read` and nothing else, on any client."""
    plan = plan_sync(bugs, client.read(cols.sheet_id, cols.tab), cols, memory, scrub)
    return plan, render_plan(plan)


def write_confirmed_plan(client: SheetClient, bugs: Iterable[TrackedBug], cols: SheetColumns,
                         memory: SyncMemory, scrub: Scrub,
                         confirmation: PlanConfirmation | None) -> SheetPlan:
    """Write the plan a person confirmed, and only that plan. `memory` is updated after each row,
    so a crash leaves it describing exactly what was written. Returns the plan that was written."""
    if client.live:
        raise LiveWriteRefused("a live sheet is refused: no first live write has been approved "
                               "(qa/gates/t199-first-live-write.md)")
    if confirmation is None:
        raise NotConfirmed("no confirmation: show the plan and have a person confirm its hash")
    plan = plan_sync(bugs, client.read(cols.sheet_id, cols.tab), cols, memory, scrub)
    if plan.plan_hash != confirmation.plan_hash:
        raise PlanChanged(f"confirmed {confirmation.plan_hash}, but the plan is now "
                          f"{plan.plan_hash}; show it again")
    for row in plan.writes:
        if row.row_number is None:
            client.append_row(cols.sheet_id, cols.tab, row.cells)
        else:
            client.update_cells(cols.sheet_id, cols.tab, row.row_number, row.cells)
        memory.written.setdefault(row.bug_key, {}).update(row.cells)
    return plan

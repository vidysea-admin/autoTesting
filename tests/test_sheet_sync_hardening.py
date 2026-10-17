"""Sheet sync hardening: AT-981 secret in a sheet cell, AT-982 partial write, AT-983 write
barrier, AT-984 guard apostrophe stripped on read-back. A fake client only: no network."""

from __future__ import annotations

from datetime import timedelta

import pytest
from bug_loop_fixture import T0, bug
from sheet_fake import FakeSheet, StripGuardSheet

from autotester.core.redact import Redactor
from autotester.schema.sheet_plan import (
    PlanConfirmation,
    SheetColumns,
    SheetPlan,
    SheetState,
    SyncMemory,
)
from autotester.schema.tracked_bug import BugStatus, TrackedBug
from autotester.stages.sheet_plan import plan_sync, render_plan
from autotester.stages.sheet_write import (
    LiveWriteRefused,
    WriteRefused,
    dry_run,
    write_confirmed_plan,
)

S = BugStatus
HEADER = ["Notes", "Key", "Title", "Severity", "Status"]
COLS = SheetColumns(sheet_id="sheet_demo", tab="Bugs", columns={
    "bug_key": "Key", "title": "Title", "severity": "Severity", "status": "Status"})
SECRET = "hunter2-sekret"


def scrub(text: str) -> str:
    return Redactor({"DEMO_PASSWORD": SECRET}).scrub(text)


def _bug(status: S = S.OPEN, **kw) -> TrackedBug:
    return bug(status).model_copy(update={"bug_key": "bug_000000000001", "title": "Bug one",
                                          "first_seen": T0 + timedelta(minutes=1), **kw})


def _confirm(plan: SheetPlan) -> PlanConfirmation:
    return PlanConfirmation(plan_hash=plan.plan_hash, confirmed_by="umesh",
                            confirmed_at=T0 + timedelta(days=1))


def _write(sheet, bugs, memory):
    plan = dry_run(sheet, bugs, COLS, memory, scrub)[0]
    return write_confirmed_plan(sheet, bugs, COLS, memory, scrub, _confirm(plan))


# -- AT-981 (C1): sheet-side text is scrubbed before it is shown, hashed or stored --------------

def test_at981_a_secret_typed_into_a_sheet_cell_is_in_no_plan_text_or_hash_input() -> None:
    typed = f"login with {SECRET}"
    sheet = FakeSheet(HEADER, [["", _bug().bug_key, typed, "", ""]])
    stale = SyncMemory(written={_bug().bug_key: {"Status": f"old {SECRET}"}})
    sheet.human_edit(2, "Status", f"old {SECRET}")      # a cell we own whose old value has it
    plan, text = dry_run(sheet, [_bug()], COLS, stale, scrub)
    [row] = plan.rows
    assert row.conflicts and row.changes                 # both sheet-side fields are exercised
    blobs = [plan.model_dump_json(), text, repr(row)]
    assert not any(SECRET in blob for blob in blobs)
    [status] = [c for c in row.changes if c.column == "Status"]
    assert "[REDACTED]" in row.conflicts[0].sheet_has and "[REDACTED]" in status.before
    assert "[REDACTED]" in render_plan(plan)


# -- AT-982 (C2): a retry after a partial write adopts the equal cell into memory ---------------

class ApplyThenTimeout(FakeSheet):
    """The write lands on the sheet, then the call raises: the caller cannot tell it landed."""

    def update_cells(self, sheet_id, tab, row_number, cells):
        super().update_cells(sheet_id, tab, row_number, cells)
        raise TimeoutError("no answer, but the write landed")


def test_at982_a_retry_after_a_write_that_landed_does_not_make_a_later_change_a_conflict() -> None:
    memory = SyncMemory()
    sheet = ApplyThenTimeout(HEADER)
    _write(sheet, [_bug()], memory)                       # the append is not overridden: lands
    with pytest.raises(TimeoutError):
        _write(sheet, [_bug(S.FIXED)], memory)            # status "fixed" lands, memory unaware
    assert sheet.rows[0][HEADER.index("Status")] == "fixed"
    assert memory.written[_bug().bug_key]["Status"] == "open"
    retry = _write(sheet, [_bug(S.FIXED)], memory)        # nothing to write, one cell to adopt
    assert retry.writes == [] and retry.adopts == {_bug().bug_key: {"Status": "fixed"}}
    assert memory.written[_bug().bug_key]["Status"] == "fixed"
    later = plan_sync([_bug(S.STALE)], sheet.read("s", "t"), COLS, memory, scrub)
    [row] = later.rows
    assert row.action == "update" and row.conflicts == []
    assert [(c.column, c.after) for c in row.changes] == [("Status", "stale")]


def test_at982_a_dry_run_reports_the_adoption_and_changes_nothing() -> None:
    sheet = FakeSheet(HEADER, [["", _bug().bug_key, "Bug one", "S2", "open"]])
    memory = SyncMemory()
    plan, text = dry_run(sheet, [_bug()], COLS, memory, scrub)
    assert plan.rows == [] and plan.unchanged == 1 and plan.adopts
    assert "remembered" in text and memory.written == {} and sheet.write_calls == []


# -- AT-983 (C3): a write needs a structural check, and `live` is re-checked after the read -----

class UnregisteredClient:
    """A conforming client of the SheetClient shape that is not the fake and says live=False."""

    live = False

    def __init__(self) -> None:
        self.calls: list[str] = []

    def read(self, sheet_id: str, tab: str) -> SheetState:
        self.calls.append("read")
        return SheetState(header=HEADER)

    def append_row(self, sheet_id: str, tab: str, cells: dict[str, str]) -> None:
        self.calls.append("append_row")

    def update_cells(self, sheet_id: str, tab: str, row_number: int, cells: dict) -> None:
        self.calls.append("update_cells")


class GoesLiveDuringRead(FakeSheet):
    def read(self, sheet_id: str, tab: str) -> SheetState:
        state = super().read(sheet_id, tab)
        self.live = True
        return state


def test_at983_a_client_that_only_claims_live_false_is_not_written_to() -> None:
    client = UnregisteredClient()
    plan = plan_sync([_bug()], SheetState(header=HEADER), COLS, SyncMemory(), scrub)
    with pytest.raises(WriteRefused, match="not a registered writer"):
        write_confirmed_plan(client, [_bug()], COLS, SyncMemory(), scrub,   # type: ignore[arg-type]
                             _confirm(plan))
    assert "append_row" not in client.calls and "update_cells" not in client.calls


def test_at983_a_client_that_turns_live_during_the_read_is_not_written_to() -> None:
    sheet = GoesLiveDuringRead(HEADER)
    plan = plan_sync([_bug()], SheetState(header=HEADER), COLS, SyncMemory(), scrub)
    with pytest.raises(LiveWriteRefused):
        write_confirmed_plan(sheet, [_bug()], COLS, SyncMemory(), scrub, _confirm(plan))
    assert sheet.write_calls == [] and sheet.rows == []


# -- AT-984 (C4): a guarded value read back without its apostrophe is not a conflict ------------

def test_at984_a_sheet_that_strips_the_formula_guard_reports_no_conflict_and_converges() -> None:
    sheet, memory = StripGuardSheet(HEADER), SyncMemory()
    _write(sheet, [_bug(title="-5")], memory)
    assert sheet.rows[0][HEADER.index("Title")] == "'-5"           # written guarded
    assert sheet.read("s", "t").rows[0][HEADER.index("Title")] == "-5"   # read back plain
    again = plan_sync([_bug(title="-5")], sheet.read("s", "t"), COLS, memory, scrub)
    assert again.rows == [] and again.unchanged == 1 and again.adopts == {}
    renamed = plan_sync([_bug(title="-6")], sheet.read("s", "t"), COLS, memory, scrub)
    [row] = renamed.rows
    assert row.action == "update" and row.conflicts == []
    assert [(c.before, c.after) for c in row.changes] == [("-5", "'-6")]

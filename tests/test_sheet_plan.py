"""T-199b: the tracker-sheet DRY RUN on a fake client (TB9, TB10, TB11, TB13 in part).

No Google, no gws, no network. The fake records every call, so "nothing was written" is asserted
from its log and its contents, not from what the code says it did.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from bug_loop_fixture import T0, bug
from pydantic import ValidationError
from sheet_fake import FakeSheet

import autotester.schema.sheet_plan as schema_mod
import autotester.stages.sheet_plan as plan_mod
import autotester.stages.sheet_write as write_mod
from autotester.core.redact import Redactor
from autotester.schema.enums import Severity
from autotester.schema.sheet_plan import (
    PlanConfirmation,
    SheetColumns,
    SheetPlan,
    SheetState,
    SyncMemory,
)
from autotester.schema.tracked_bug import BugStatus, TrackedBug
from autotester.stages.sheet_plan import PlanRefused, plan_sync, render_plan
from autotester.stages.sheet_write import (
    LiveWriteRefused,
    NotConfirmed,
    PlanChanged,
    SheetClient,
    dry_run,
    write_confirmed_plan,
)

S = BugStatus
HEADER = ["Notes (human)", "Key", "Title", "Severity", "Status", "Assignee", "Owner's tag"]
COLS = SheetColumns(sheet_id="sheet_demo", tab="Bugs", columns={
    "bug_key": "Key", "title": "Title", "severity": "Severity", "status": "Status",
    "assignee": "Assignee"})
NOW = T0 + timedelta(days=1)
SECRET = "hunter2-sekret"


def scrub(text: str) -> str:
    return Redactor({"DEMO_PASSWORD": SECRET}).scrub(text)


def _bug(n: int, status: S = S.OPEN, **kw) -> TrackedBug:
    base = bug(status).model_copy(update={"bug_key": f"bug_{n:012d}", "title": f"Bug number {n}",
                                          "first_seen": T0 + timedelta(minutes=n), **kw})
    return base


def _confirm(plan: SheetPlan, who: str = "umesh") -> PlanConfirmation:
    return PlanConfirmation(plan_hash=plan.plan_hash, confirmed_by=who, confirmed_at=NOW)


def _write(sheet, bugs, memory=None, confirmation="auto", cols=COLS):
    memory = memory if memory is not None else SyncMemory()
    if confirmation == "auto":
        confirmation = _confirm(dry_run(sheet, bugs, cols, memory, scrub)[0])
    return write_confirmed_plan(sheet, bugs, cols, memory, scrub, confirmation), memory


# -- the plan and the dry run -------------------------------------------------------------------

def test_the_dry_run_shows_the_exact_cells_and_leaves_the_sheet_untouched() -> None:
    sheet = FakeSheet(HEADER, [["keep me", "", "", "", "", "", "tag"]])
    before = sheet.snapshot()
    plan, text = dry_run(sheet, [_bug(1), _bug(2, severity=Severity.S1)], COLS, SyncMemory(), scrub)
    assert [r.action for r in plan.rows] == ["append", "append"]
    assert text.splitlines()[0] == "DRY RUN - nothing has been written"
    assert plan.plan_hash in text and "'Bug number 1'" in text and "Severity: '' -> 'S1'" in text
    assert sheet.snapshot() == before and [c[0] for c in sheet.calls] == ["read"]


def test_one_row_per_live_bug_a_closed_bug_not_in_the_sheet_is_not_added() -> None:
    bugs = [_bug(1), _bug(2, S.REOPENED), _bug(3, S.FIXED), _bug(4, S.STALE)]
    plan = plan_sync(bugs, SheetState(header=HEADER), COLS, SyncMemory(), scrub)
    assert [r.bug_key for r in plan.rows] == [_bug(1).bug_key, _bug(2).bug_key]


def test_a_closed_bug_that_already_has_a_row_gets_its_status_updated() -> None:
    sheet = FakeSheet(HEADER)
    memory = SyncMemory()
    _write(sheet, [_bug(1)], memory)
    plan, _ = _write(sheet, [_bug(1, S.FIXED)], memory)
    assert [(r.action, r.cells) for r in plan.rows] == [("update", {"Status": "fixed"})]
    assert sheet.rows[0][HEADER.index("Status")] == "fixed"


def test_the_plan_is_the_same_whatever_order_the_bugs_arrive_in() -> None:
    state = SheetState(header=HEADER)
    a = plan_sync([_bug(1), _bug(2), _bug(3)], state, COLS, SyncMemory(), scrub)
    b = plan_sync([_bug(3), _bug(1), _bug(2)], state, COLS, SyncMemory(), scrub)
    assert a == b and a.plan_hash == b.plan_hash


def test_a_plan_whose_hash_does_not_match_its_content_is_refused() -> None:
    plan = plan_sync([_bug(1)], SheetState(header=HEADER), COLS, SyncMemory(), scrub)
    forged = plan.model_dump(mode="json")
    forged["rows"][0]["changes"][0]["after"] = "something else"
    with pytest.raises(ValidationError, match="plan_hash"):
        SheetPlan.model_validate(forged)


def test_a_mapped_column_that_left_the_header_makes_the_mapping_stale() -> None:
    renamed = ["Notes (human)", "Key", "Name", "Severity", "Status", "Assignee"]
    with pytest.raises(PlanRefused, match="Title"):
        plan_sync([_bug(1)], SheetState(header=renamed), COLS, SyncMemory(), scrub)


def test_a_key_on_two_rows_is_blocked_not_guessed() -> None:
    key = _bug(1).bug_key
    state = SheetState(header=HEADER, rows=[["", key], ["", key]])
    plan = plan_sync([_bug(1)], state, COLS, SyncMemory(), scrub)
    assert [r.action for r in plan.rows] == ["conflict"] and plan.writes == []


# -- TB9: nothing is written before a person confirmed this plan --------------------------------

def test_tb9_no_write_without_a_confirmation_and_none_after_the_plan_changed() -> None:
    sheet = FakeSheet(HEADER)
    bugs = [_bug(1), _bug(2)]
    with pytest.raises(NotConfirmed):
        write_confirmed_plan(sheet, bugs, COLS, SyncMemory(), scrub, None)
    assert sheet.calls == []                           # not even a read
    confirmation = _confirm(dry_run(sheet, bugs, COLS, SyncMemory(), scrub)[0])
    changed = [_bug(1), _bug(2, title="Bug number 2, reworded")]       # one cell differs
    with pytest.raises(PlanChanged):
        write_confirmed_plan(sheet, changed, COLS, SyncMemory(), scrub, confirmation)
    assert sheet.write_calls == [] and sheet.rows == []


def test_tb9_a_plan_that_changed_because_a_human_edited_the_sheet_needs_a_new_confirmation(
) -> None:
    sheet = FakeSheet(HEADER)
    memory = SyncMemory()
    _write(sheet, [_bug(1)], memory)
    stale = _confirm(dry_run(sheet, [_bug(1, S.FIXED)], COLS, memory, scrub)[0])
    sheet.human_edit(2, "Status", "wontfix")
    with pytest.raises(PlanChanged):
        write_confirmed_plan(sheet, [_bug(1, S.FIXED)], COLS, memory, scrub, stale)
    assert sheet.rows[0][HEADER.index("Status")] == "wontfix"


def test_tb9_the_confirmed_plan_is_written_and_a_person_is_named() -> None:
    sheet = FakeSheet(HEADER)
    plan, _ = _write(sheet, [_bug(1), _bug(2)])
    assert len(sheet.write_calls) == 2 and len(sheet.rows) == 2
    assert render_plan(plan, written=True).startswith("WRITTEN")


@pytest.mark.parametrize("who", ["system:bug-loop", "system", "", "a\nb"])
def test_tb9_the_machine_cannot_confirm_a_plan(who: str) -> None:
    with pytest.raises(ValidationError):
        PlanConfirmation(plan_hash="plan_x", confirmed_by=who, confirmed_at=NOW)
    with pytest.raises(ValidationError):
        PlanConfirmation(plan_hash="plan_x", confirmed_by="umesh",
                         confirmed_at=datetime(2026, 1, 1))


def test_tb9_a_live_client_is_refused_even_with_a_correct_confirmation() -> None:
    sheet = FakeSheet(HEADER, live=True)
    plan, _ = dry_run(sheet, [_bug(1)], COLS, SyncMemory(), scrub)
    with pytest.raises(LiveWriteRefused, match="t199-first-live-write"):
        write_confirmed_plan(sheet, [_bug(1)], COLS, SyncMemory(), scrub, _confirm(plan))
    assert sheet.write_calls == []
    assert dry_run(sheet, [_bug(1)], COLS, SyncMemory(), scrub)[0].rows   # a dry run still works


# -- TB10: own rows only, human edits survive ---------------------------------------------------

def test_tb10_the_client_interface_has_no_delete_or_clear() -> None:
    names = {n for n in {*vars(SheetClient), *SheetClient.__annotations__}
             if not n.startswith("_")}
    assert names == {"live", "read", "append_row", "update_cells"}
    assert not any(w in n for n in names for w in ("delete", "clear", "remove", "drop"))


def test_tb10_unmapped_columns_keep_their_values_and_are_never_in_a_write() -> None:
    sheet = FakeSheet(HEADER, [["human note", "", "", "", "", "", "tag-1"]])
    sheet.rows[0][HEADER.index("Key")] = _bug(1).bug_key
    _write(sheet, [_bug(1)])
    row = sheet.rows[0]
    assert row[0] == "human note" and row[HEADER.index("Owner's tag")] == "tag-1"
    written = {c for call in sheet.write_calls for c in call[-1]}
    assert written <= set(COLS.columns.values())


def test_tb10_a_cell_a_human_edited_is_not_overwritten_and_the_conflict_is_reported() -> None:
    sheet, memory = FakeSheet(HEADER), SyncMemory()
    _write(sheet, [_bug(1)], memory)
    sheet.human_edit(2, "Title", "Priya renamed this")
    plan, _ = _write(sheet, [_bug(1, S.FIXED, title="Bug number 1 v2")], memory)
    row = sheet.rows[0]
    assert row[HEADER.index("Title")] == "Priya renamed this"        # the edit survives
    assert row[HEADER.index("Status")] == "fixed"                    # our other cell still moved
    [conflict] = plan.rows[0].conflicts
    assert (conflict.column, conflict.sheet_has, conflict.we_would_write) == (
        "Title", "Priya renamed this", "Bug number 1 v2")
    assert "CONFLICT Title" in render_plan(plan) and "NOT WRITTEN" in render_plan(plan)


def test_tb10_a_row_that_already_has_other_values_and_no_memory_of_us_is_not_overwritten() -> None:
    sheet = FakeSheet(HEADER, [["", _bug(1).bug_key, "Typed by a person", "", "", "", ""]])
    plan, _ = _write(sheet, [_bug(1)])
    assert sheet.rows[0][HEADER.index("Title")] == "Typed by a person"
    assert [c.column for c in plan.rows[0].conflicts] == ["Title"]
    assert sheet.rows[0][HEADER.index("Severity")] == "S2"           # an empty cell was filled


# -- TB11: idempotent, convergent ---------------------------------------------------------------

def test_tb11_syncing_twice_makes_no_duplicate_rows_and_the_second_plan_is_empty() -> None:
    sheet, memory = FakeSheet(HEADER), SyncMemory()
    bugs = [_bug(1), _bug(2)]
    _write(sheet, bugs, memory)
    snap = sheet.snapshot()
    second, _ = _write(sheet, bugs, memory)
    assert second.rows == [] and second.unchanged == 2 and sheet.snapshot() == snap


def test_tb11_a_crash_after_row_k_converges_on_retry_with_every_row_once() -> None:
    bugs = [_bug(n) for n in range(1, 6)]
    clean = FakeSheet(HEADER)
    _write(clean, bugs)
    sheet, memory = FakeSheet(HEADER, fail_after_writes=2), SyncMemory()
    with pytest.raises(ConnectionError):
        _write(sheet, bugs, memory)
    assert len(sheet.rows) == 2
    sheet.fail_after_writes = None
    stale = _confirm(plan_sync(bugs, SheetState(header=HEADER), COLS, SyncMemory(), scrub))
    with pytest.raises(PlanChanged):         # the old confirmation does not cover the retry
        write_confirmed_plan(sheet, bugs, COLS, memory, scrub, stale)
    _write(sheet, bugs, memory)
    assert sheet.rows == clean.rows and len({r[1] for r in sheet.rows}) == 5


# -- TB13: what is written is clean -------------------------------------------------------------

def test_tb13_a_planted_secret_is_in_neither_the_plan_nor_its_rendering_nor_the_sheet() -> None:
    sheet = FakeSheet(HEADER)
    leaky = _bug(1, title=f"Login fails with password {SECRET}")
    plan, _ = _write(sheet, [leaky])
    blobs = [plan.model_dump_json(), render_plan(plan), repr(sheet.rows), repr(sheet.calls)]
    assert not any(SECRET in blob for blob in blobs)
    assert "[REDACTED]" in sheet.rows[0][HEADER.index("Title")]


def test_a_value_that_would_run_as_a_formula_is_written_as_plain_text() -> None:
    sheet = FakeSheet(HEADER)
    plan, _ = _write(sheet, [_bug(1, title='=HYPERLINK("http://evil","x")'), _bug(2, title="-1+1")])
    assert sheet.rows[0][HEADER.index("Title")] == "'=HYPERLINK(\"http://evil\",\"x\")"
    assert sheet.rows[1][HEADER.index("Title")] == "'-1+1"
    assert plan.rows[0].changes[1].after.startswith("'=")


# -- design rules -------------------------------------------------------------------------------

def test_the_sheet_modules_import_no_network_google_or_process_library() -> None:
    banned = {"socket", "httpx", "requests", "urllib", "subprocess", "googleapiclient", "google",
              "http", "aiohttp", "smtplib", "gspread"}
    for mod in (schema_mod, plan_mod, write_mod):
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        roots = {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module}
        roots |= {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                  for a in n.names}
        assert not roots & banned, (mod.__name__, roots & banned)


def test_the_columns_mapping_must_name_the_key_and_only_owned_fields() -> None:
    for bad in ({"title": "Title"}, {"bug_key": "Key", "reporter": "Who"},
                {"bug_key": "Key", "title": "Key"}):
        with pytest.raises(ValidationError):
            SheetColumns(sheet_id="s", tab="t", columns=bad)


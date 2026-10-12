"""T-199c: first-write confirmation, sheet outage, clean values on a fake sheet (TB9, TB12, TB13).

No live client exists. Every sheet here is `FakeSheet`, which records each call.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from bug_loop_fixture import KEY, T0, bug
from sheet_fake import FakeSheet
from tracker_fakes import ALLOWED, LAYOUT_A, binding

from autotester.core.redact import Redactor
from autotester.schema.tracked_bug import BugStatus
from autotester.schema.tracker_binding import TrackerBinding
from autotester.stages.sheet_write import LiveWriteRefused, NotConfirmed, PlanChanged
from autotester.stages.tracker_mapping import (
    NotAllowed,
    confirm_mapping,
    propose_mapping,
    rebind,
)
from autotester.stages.tracker_sync import (
    check_link,
    confirm_first_write,
    preview_sync,
    sync_confirmed,
)

NOW = T0 + timedelta(days=1)
SECRET = "hunter2-sekret"
scrub = Redactor({"K": SECRET}).scrub


def _confirmed() -> TrackerBinding:
    start = binding().model_copy(update={"mapping": propose_mapping(LAYOUT_A)})
    return confirm_mapping(start, "umesh.s", ALLOWED, NOW)


def _writes(sheet: FakeSheet) -> int:
    return len(sheet.write_calls)


def test_tb9_preview_reads_and_plans_but_never_writes() -> None:
    sheet = FakeSheet(LAYOUT_A)
    after, plan, shown = preview_sync(_confirmed(), sheet, [bug(BugStatus.OPEN)], scrub, NOW)
    assert plan is not None and len(plan.writes) == 1 and "nothing has been written" in shown
    assert _writes(sheet) == 0 and after.sync.sync_status == "ok" and after.sync.written is False


def test_tb9_zero_writes_before_confirmation_and_after_a_one_cell_change() -> None:
    sheet, bugs = FakeSheet(LAYOUT_A), [bug(BugStatus.OPEN)]
    b = _confirmed()
    with pytest.raises(NotConfirmed):
        sync_confirmed(b, sheet, bugs, scrub, NOW)
    assert _writes(sheet) == 0
    _, plan, _ = preview_sync(b, sheet, bugs, scrub, NOW)
    b = confirm_first_write(b, plan, "umesh.s", ALLOWED, NOW)
    assert b.first_write.plan_hash == plan.plan_hash and b.first_write.confirmed_by == "umesh.s"
    changed = [bug(BugStatus.OPEN).model_copy(update={"title": "A different title"})]
    with pytest.raises(PlanChanged):
        sync_confirmed(b, sheet, changed, scrub, NOW)
    assert _writes(sheet) == 0
    done = sync_confirmed(b, sheet, bugs, scrub, NOW)
    assert _writes(sheet) == 1 and done.sync.written is True


def test_tb9_confirming_the_first_write_needs_project_edit() -> None:
    sheet, b = FakeSheet(LAYOUT_A), _confirmed()
    _, plan, _ = preview_sync(b, sheet, [bug(BugStatus.OPEN)], scrub, NOW)
    with pytest.raises(NotAllowed):
        confirm_first_write(b, plan, "mallory", ALLOWED, NOW)
    assert b.first_write is None


def test_tb9_a_live_client_is_still_refused_through_this_layer() -> None:
    sheet, b = FakeSheet(LAYOUT_A, live=True), _confirmed()
    plan = preview_sync(b, sheet, [bug(BugStatus.OPEN)], scrub, NOW)[1]
    b = confirm_first_write(b, plan, "umesh.s", ALLOWED, NOW)
    with pytest.raises(LiveWriteRefused):
        sync_confirmed(b, sheet, [bug(BugStatus.OPEN)], scrub, NOW)
    assert _writes(sheet) == 0


def test_tb13_swapping_the_sheet_id_refuses_the_write() -> None:
    sheet, bugs, b = FakeSheet(LAYOUT_A), [bug(BugStatus.OPEN)], _confirmed()
    b = confirm_first_write(b, preview_sync(b, sheet, bugs, scrub, NOW)[1], "umesh.s", ALLOWED, NOW)
    swapped = rebind(b, sheet_id="someone_elses_sheet")
    with pytest.raises(Exception) as err:
        sync_confirmed(swapped, sheet, bugs, scrub, NOW)
    assert "not confirmed" in str(err.value) or isinstance(err.value, NotConfirmed)
    assert _writes(sheet) == 0


def test_tb12_a_sheet_outage_sets_error_status_and_leaves_the_bugs_alone() -> None:
    class Down(FakeSheet):
        def read_header(self, sheet_id, tab):
            raise ConnectionError(f"HTTP 503 for {SECRET}")

    bugs = [bug(BugStatus.OPEN)]
    after, plan, shown = preview_sync(_confirmed(), Down(LAYOUT_A), bugs, scrub, NOW)
    assert plan is None and after.sync.sync_status == "error"
    assert after.sync.retry_at == NOW + timedelta(minutes=15)
    assert SECRET not in (after.sync.last_error or "") and SECRET not in after.model_dump_json()
    assert bugs[0].status is BugStatus.OPEN and "Nothing has been written" in shown


def test_tb12_confirmed_write_during_an_outage_is_an_error_status_then_converges() -> None:
    bugs = [bug(BugStatus.OPEN)]
    b = _confirmed()
    probe = FakeSheet(LAYOUT_A)
    b = confirm_first_write(b, preview_sync(b, probe, bugs, scrub, NOW)[1], "umesh.s", ALLOWED, NOW)
    flaky = FakeSheet(LAYOUT_A, fail_after_writes=0)
    failed = sync_confirmed(b, flaky, bugs, scrub, NOW)
    assert failed.sync.sync_status == "error" and failed.sync.last_error
    healthy = FakeSheet(LAYOUT_A)
    done = sync_confirmed(failed, healthy, bugs, scrub, NOW + timedelta(minutes=20))
    assert done.sync.sync_status == "ok" and done.sync.last_error is None
    assert [r[1] for r in healthy.rows] == [KEY]


def test_tb12_a_changed_header_is_stale_and_gives_no_plan() -> None:
    renamed = [h if h != "Status" else "State" for h in LAYOUT_A]
    after, plan, shown = preview_sync(_confirmed(), FakeSheet(renamed), [bug(BugStatus.OPEN)],
                                      scrub, NOW)
    assert plan is None and after.mapping.status.value == "stale" and "stale" in shown


def test_tb13_a_planted_secret_in_a_bug_title_is_in_neither_plan_nor_rendering() -> None:
    leaky = bug(BugStatus.OPEN).model_copy(update={"title": f"Pay failed {SECRET}"})
    after, plan, shown = preview_sync(_confirmed(), FakeSheet(LAYOUT_A), [leaky], scrub, NOW)
    assert SECRET not in plan.model_dump_json() and SECRET not in shown
    assert SECRET not in after.model_dump_json()


def test_tb13_a_screenshot_link_must_be_on_the_product_host_and_unsigned() -> None:
    ok = "https://app.example.test/projects/demo/evidence/shot1.png"
    assert check_link(ok, "app.example.test") == ok
    for bad in ("http://app.example.test/x.png", "https://elsewhere.test/x.png",
                "https://app.example.test/x.png?X-Amz-Signature=abc",
                "https://app.example.test/x.png?token=abc"):
        with pytest.raises(ValueError):
            check_link(bad, "app.example.test")

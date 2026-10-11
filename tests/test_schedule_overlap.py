"""TS4: a slot that finds its project still busy is skipped and says so (R52, HO17)."""

from __future__ import annotations

from pathlib import Path

from schedule_fakes import daily, make_deps, utc

from autotester.schema.schedule import SlotOutcome
from autotester.stages.schedule_store import list_claims, read_records
from autotester.stages.scheduler import tick_project

SINCE = utc(2026, 10, 7, 12)


def test_slot_finding_a_running_entry_is_skipped_with_the_blocking_id(tmp_path: Path) -> None:
    """The previous slot's run, or a Test-button run, is still going when 09:00 arrives."""
    deps, q = make_deps(tmp_path, "p")
    q.add_running("p", "busy1")
    out = tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 10), deps, since=SINCE)
    assert [r.outcome for r in out] == [SlotOutcome.SKIPPED_OVERLAP]
    assert out[0].blocking_entry_id == "busy1"
    assert len(q) == 1  # no second entry: HO17's single flight is untouched


def test_a_skipped_slot_is_not_retried_as_a_catch_up_later(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    q.add_running("p", "busy1")
    tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 10), deps, since=SINCE)
    q.finish("busy1")
    assert tick_project("p", daily(), utc(2026, 10, 8, 9, 20), deps, since=SINCE) == []
    assert len(q) == 1
    assert [r.outcome.value for r in read_records(deps.records_path)] == ["skipped_overlap"]


def test_the_next_slot_is_judged_fresh_after_a_skip(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    q.add_running("p", "busy1")
    tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 10), deps, since=SINCE)
    q.finish("busy1")
    out = tick_project("p", daily(), utc(2026, 10, 9, 9, 0, 10), deps, since=SINCE)
    assert [r.outcome for r in out] == [SlotOutcome.ENQUEUED]
    assert len(q) == 2


def test_a_finished_entry_does_not_block(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    q.add_running("p", "done1")
    q.finish("done1")
    out = tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 10), deps, since=SINCE)
    assert [r.outcome for r in out] == [SlotOutcome.ENQUEUED]


def test_another_projects_busy_entry_does_not_block_this_project(tmp_path: Path) -> None:
    """Two projects share the queue; only the same project is single-flight (HO17)."""
    deps, q = make_deps(tmp_path, "p")
    q.add_running("other-project", "busy2")
    out = tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 10), deps, since=SINCE)
    assert [r.outcome for r in out] == [SlotOutcome.ENQUEUED]


def test_a_paused_schedule_records_and_claims_nothing(tmp_path: Path) -> None:
    """Paused is not a skipped slot: no `skipped_overlap` line, no marker."""
    deps, q = make_deps(tmp_path, "p")
    q.add_running("p", "busy1")
    paused = daily().model_copy(update={"paused": True})
    assert tick_project("p", paused, utc(2026, 10, 8, 9, 0, 10), deps, since=SINCE) == []
    assert read_records(deps.records_path) == []
    assert list(list_claims(deps.claim_dir)) == []
    assert len(q) == 1

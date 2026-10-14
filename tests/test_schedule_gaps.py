"""T-200 TS4/TS7 gap closure: the history names the blocker, the card names the stale time, a
failed slot reaches the inbox, a dead worker updates its slot record, an unreadable queue file
skips the slot, and the dry run predicts the real gate's refusals (production, owner rights)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from schedule_fakes import daily, make_deps, utc

from autotester.schema.project import Project
from autotester.schema.run_queue import QueueEntry
from autotester.schema.schedule import CredentialState, SlotOutcome, SlotRecord
from autotester.stages import schedule_wiring
from autotester.stages.report_delivery import _BLOCKED_SLOTS, _slot_row
from autotester.stages.schedule_store import (
    QueueUnreadable,
    amend_record,
    append_record,
    read_records,
    write_heartbeat,
)
from autotester.stages.schedule_wiring import NullQueue, record_worker_end, schedule_paths, tick_all
from autotester.stages.scheduler import tick_project
from autotester.store.project_store import ProjectStore
from autotester.ui import schedule_view

NOW = utc(2026, 10, 8, 9, 0, 10)
SINCE = utc(2026, 10, 7, 12)
KEY = "demo:fixed:2026-10-08T09:00Z"


def _rec(outcome: SlotOutcome, **kw: str) -> SlotRecord:
    return SlotRecord(slot_key=KEY, project="demo", mode=daily().mode,
                      instant=utc(2026, 10, 8, 9), recorded_at=NOW, outcome=outcome, **kw)


def _save(root: Path, **kw: object) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="d", base_url="https://demo.test",
                               allowed_domains=["demo.test"], schedule=daily(), **kw))
    os.utime(store.paths.config, (SINCE.timestamp(), SINCE.timestamp()))
    return store


# --- 1. TS4: the history shows the blocker and the reason ---------------------------------
def test_history_shows_the_blocking_entry_and_that_the_slot_was_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = schedule_paths(tmp_path)
    monkeypatch.setattr(schedule_view, "schedule_paths", lambda: paths)
    deps, q = make_deps(tmp_path / "t", "demo")
    q.add_running("demo", "run-busy7")
    deps = type(deps)(**{**deps.__dict__, "records_path": paths.records / "demo.jsonl"})
    tick_project("demo", daily(), NOW, deps, since=SINCE)
    html = schedule_view._history("demo")
    assert "skipped_overlap" in html and "run-busy7" in html and "skipped, not retried" in html


# --- 2. TS7(a): "scheduler stale since <time>" -------------------------------------------
def _card(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, last_tick: datetime) -> str:
    paths = schedule_paths(tmp_path)
    monkeypatch.setattr(schedule_view, "schedule_paths", lambda: paths)
    monkeypatch.setattr(schedule_view, "credential_state", lambda *_: CredentialState.PROVISIONED)
    write_heartbeat(paths.heartbeat, last_tick)
    return schedule_view._status("demo", daily(), None, None, utc(2026, 10, 8, 9))  # type: ignore[arg-type]


def test_stale_card_reads_scheduler_stale_since_the_last_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "scheduler stale since 2026-10-01 08:30 UTC" in _card(
        tmp_path, monkeypatch, utc(2026, 10, 1, 8, 30))


def test_fresh_heartbeat_is_not_called_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = _card(tmp_path, monkeypatch, utc(2026, 10, 8, 8, 59))
    assert "stale" not in html and "healthy" in html


# --- 3. TS7(b): a FAILED slot is an inbox row with no cause in it -------------------------
def test_failed_slot_is_an_inbox_row_without_the_cause() -> None:
    assert SlotOutcome.FAILED in _BLOCKED_SLOTS
    row = _slot_row(_rec(SlotOutcome.FAILED, detail="RuntimeError: token=SECRET-123 https://x"))
    dumped = row.model_dump_json()
    assert "SECRET-123" not in dumped and "https://x" not in dumped
    assert row.link == "/projects/demo/schedule" and row.scheduled


# --- 4. TS7(c): a dead worker rewrites its slot record ------------------------------------
def _enqueued(tmp_path: Path) -> tuple[Path, QueueEntry]:
    path = schedule_paths(tmp_path).records / "demo.jsonl"
    append_record(path, _rec(SlotOutcome.ENQUEUED, entry_id="run-q1"))
    return path, QueueEntry(id="run-q1", project="demo", trigger="schedule", slot_key=KEY)


def test_worker_failure_updates_the_durable_slot_record_with_the_class_only(
    tmp_path: Path,
) -> None:
    path, entry = _enqueued(tmp_path)
    assert record_worker_end(entry, RuntimeError("password=hunter2"), tmp_path)
    [rec] = read_records(path)
    assert rec.outcome is SlotOutcome.FAILED and rec.entry_id == "run-q1"
    assert rec.detail == "worker ended: RuntimeError" and "hunter2" not in rec.model_dump_json()


def test_a_killed_worker_is_recorded_too_and_a_button_run_is_left_alone(tmp_path: Path) -> None:
    path, entry = _enqueued(tmp_path)
    button = entry.model_copy(update={"trigger": "button"})
    assert not record_worker_end(button, RuntimeError("x"), tmp_path)
    assert read_records(path)[0].outcome is SlotOutcome.ENQUEUED
    assert record_worker_end(entry, SystemExit(1), tmp_path)
    assert read_records(path)[0].detail == "worker ended: SystemExit"


def test_tick_runner_records_a_worker_crash_then_reraises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import autotester.ui.routes_runs as routes_runs
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    path, entry = _enqueued(tmp_path)

    def boom(_entry: QueueEntry) -> None:
        raise ValueError("secret")

    monkeypatch.setattr(routes_runs, "_run_queued", boom)
    with pytest.raises(ValueError):
        routes_runs.tick_runner(entry)
    assert read_records(path)[0].outcome is SlotOutcome.FAILED


def test_amend_record_of_an_unknown_slot_changes_nothing(tmp_path: Path) -> None:
    path, _ = _enqueued(tmp_path)
    assert not amend_record(path, "other", SlotOutcome.FAILED, "x")
    assert read_records(path)[0].outcome is SlotOutcome.ENQUEUED


# --- 5. fail closed: an unreadable queue file is "busy unknown", not idle -----------------
def test_unreadable_queue_file_skips_the_slot_with_a_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autotester.ui import run_queue
    bad = tmp_path / "queue.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(run_queue, "_queue_file", lambda: bad)
    with pytest.raises(QueueUnreadable):
        run_queue.persisted_entries()
    _save(tmp_path)

    class Spy(NullQueue):
        def submit(self, project: str, **kw: object) -> QueueEntry:
            raise AssertionError("an unreadable queue must not enqueue")

    report = tick_all(NOW, root=tmp_path, queue=Spy(), persisted=run_queue.persisted_entries,
                      gate_for=lambda _p: (lambda _s: None))
    [rec] = report.records
    assert rec.outcome is SlotOutcome.SKIPPED_OVERLAP and "busy unknown" in (rec.detail or "")


def test_an_absent_queue_file_is_still_an_idle_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autotester.ui import run_queue
    monkeypatch.setattr(run_queue, "_queue_file", lambda: tmp_path / "none.json")
    assert run_queue.persisted_entries() == []


# --- 6. dry run: "would be refused" for production approval and owner rights --------------
def test_dry_run_refuses_a_production_project_without_a_human_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _save(tmp_path, production=True)
    monkeypatch.setattr(schedule_wiring, "refusal_for", lambda *_: None)
    monkeypatch.setattr(schedule_wiring, "auth_disabled", lambda: True)
    report = tick_all(NOW, root=tmp_path, queue=NullQueue(), dry_run=True)
    assert report.would_fire == [] and report.exit_code == 2
    [reason] = report.would_block_reasons.values()
    assert reason.startswith("approval_required")


def test_dry_run_refuses_when_the_owner_lost_run_permission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _save(tmp_path)
    monkeypatch.setattr(schedule_wiring, "refusal_for", lambda *_: None)
    monkeypatch.setattr(schedule_wiring, "auth_disabled", lambda: False)
    monkeypatch.setattr(schedule_wiring, "owner_refusal",
                        lambda slug, owner: "owner_refused: no project.run")
    report = tick_all(NOW, root=tmp_path, queue=NullQueue(), dry_run=True)
    assert report.would_block_reasons == {KEY: "owner_refused: no project.run"}
    monkeypatch.setattr(schedule_wiring, "owner_refusal", lambda slug, owner: None)
    ok = tick_all(NOW, root=tmp_path, queue=NullQueue(), dry_run=True)
    assert ok.would_fire == [KEY] and ok.exit_code == 0


def test_cli_text_says_would_be_refused_with_the_reason() -> None:
    from autotester import cli_schedule
    from autotester.schema.schedule import TickReport
    r = TickReport(tick_at=datetime(2026, 10, 8, tzinfo=UTC), dry_run=True, exit_code=2,
                   would_block=["k"], would_block_reasons={"k": "approval_required: x"})
    assert "k  would be refused: approval_required: x" in cli_schedule._text(r)


# --- fix cycle 2: a killed run is not `enqueued` forever; amendments are append-only ------
def test_amend_appends_a_line_and_the_latest_amendment_wins(tmp_path: Path) -> None:
    path, _ = _enqueued(tmp_path)
    before = path.read_text(encoding="utf-8")
    assert amend_record(path, KEY, SlotOutcome.FAILED, "first")
    assert amend_record(path, KEY, SlotOutcome.INTERRUPTED, "second")
    assert path.read_text(encoding="utf-8").startswith(before)  # nothing rewritten
    [rec] = read_records(path)
    assert rec.outcome is SlotOutcome.INTERRUPTED and rec.detail == "second"
    assert not append_record(path, _rec(SlotOutcome.ENQUEUED))  # still one record per slot


def test_appends_concurrent_with_amends_lose_nothing(tmp_path: Path) -> None:
    import threading
    path, _ = _enqueued(tmp_path)
    stop = threading.Event()

    def amend_loop() -> None:
        while not stop.is_set():
            amend_record(path, KEY, SlotOutcome.FAILED, "x")

    worker = threading.Thread(target=amend_loop)
    worker.start()
    keys = [f"demo:fixed:2026-10-{d:02d}T09:00Z" for d in range(9, 29)]
    for k in keys:
        append_record(path, _rec(SlotOutcome.ENQUEUED).model_copy(update={"slot_key": k}))
    stop.set()
    worker.join()
    assert {r.slot_key for r in read_records(path)} == {KEY, *keys}


def test_recover_marks_a_scheduled_slot_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autotester.schema.run_queue import QueueStatus, RunQueueFile
    from autotester.store.filestore import write_json
    from autotester.ui.run_queue import RunQueue
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    path, entry = _enqueued(tmp_path)
    qfile = tmp_path / "queue.json"
    write_json(qfile, RunQueueFile(entries=[entry.model_copy(
        update={"status": QueueStatus.RUNNING})]))
    RunQueue(path=lambda: qfile, spawn=lambda job: None).recover()
    [rec] = read_records(path)
    assert rec.outcome is SlotOutcome.INTERRUPTED and rec.entry_id == "run-q1"
    assert SlotOutcome.INTERRUPTED in _BLOCKED_SLOTS  # reaches the inbox


def test_tick_sweep_amends_a_stale_enqueued_slot_with_no_live_run(tmp_path: Path) -> None:
    from datetime import timedelta

    from autotester.stages.schedule_sweep import sweep_dead_enqueued
    path, _ = _enqueued(tmp_path)
    store = _save(tmp_path)
    records = schedule_paths(tmp_path).records
    soon = NOW + timedelta(hours=1)
    assert sweep_dead_enqueued("demo", records, soon, set, store) == 0      # not stale yet
    late = NOW + timedelta(hours=4)
    assert sweep_dead_enqueued("demo", records, late, lambda: {"run-q1"}, store) == 0  # live
    assert sweep_dead_enqueued("demo", records, late, set, store) == 1
    assert read_records(path)[0].outcome is SlotOutcome.INTERRUPTED
    assert sweep_dead_enqueued("demo", records, late, set, store) == 0      # idempotent


def test_sweep_leaves_a_finished_run_alone(tmp_path: Path) -> None:
    from datetime import timedelta

    from autotester.schema.run import Run
    from autotester.stages.schedule_sweep import sweep_dead_enqueued
    path, _ = _enqueued(tmp_path)
    store = _save(tmp_path)
    store.save_run(Run(id="run-q1", project="demo", finished_at=NOW))
    assert sweep_dead_enqueued("demo", schedule_paths(tmp_path).records,
                               NOW + timedelta(hours=4), set, store) == 0
    assert read_records(path)[0].outcome is SlotOutcome.ENQUEUED

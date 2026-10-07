"""TS7 (pure parts): enqueue failures are recorded loudly; a stopped scheduler is detected."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from schedule_fakes import daily, make_deps, utc

from autotester.schema.schedule import (
    ScheduleConfig,
    SchedulerHealth,
    SlotOutcome,
    SlotRecord,
)
from autotester.stages.schedule_store import read_heartbeat, read_records, write_heartbeat
from autotester.stages.scheduler import scheduler_health, tick_interval_from_env, tick_project

SINCE = utc(2026, 10, 7, 12)
NOW = utc(2026, 10, 8, 9, 0, 10)


def test_slot_outcomes_are_the_closed_set_of_seven() -> None:
    assert {o.value for o in SlotOutcome} == {
        "enqueued", "catch_up", "missed", "skipped_overlap", "blocked_no_credentials",
        "refused", "failed"}


def test_a_record_with_an_outcome_outside_the_set_fails_the_model() -> None:
    with pytest.raises(ValidationError):
        SlotRecord(slot_key="p:fixed:x", project="p", mode="fixed", instant=NOW,
                   recorded_at=NOW, outcome="retrying")


def test_queue_down_when_the_slot_fires_is_recorded_failed_with_its_cause(
    tmp_path: Path,
) -> None:
    """The run queue raises (disk full, bad state file) at 09:00: the slot must not vanish."""
    deps, _ = make_deps(tmp_path, "p")
    import dataclasses

    def boom(_slot: object) -> str:
        raise RuntimeError("queue is down: disk full")

    out = tick_project("p", daily(), NOW, dataclasses.replace(deps, enqueue=boom), since=SINCE)
    assert [r.outcome for r in out] == [SlotOutcome.FAILED]
    assert "queue is down: disk full" in (out[0].detail or "")
    assert out[0].entry_id is None
    assert [r.outcome for r in read_records(deps.records_path)] == [SlotOutcome.FAILED]


def test_failed_detail_is_scrubbed_so_no_secret_reaches_the_record(tmp_path: Path) -> None:
    """An exception message can echo an env value; the record must not keep it (no-fire list)."""
    import dataclasses

    deps, _ = make_deps(tmp_path, "p", scrub=lambda s: s.replace("hunter2", "[REDACTED]"))

    def boom(_slot: object) -> str:
        raise RuntimeError("login failed for password hunter2")

    tick_project("p", daily(), NOW, dataclasses.replace(deps, enqueue=boom), since=SINCE)
    text = deps.records_path.read_text(encoding="utf-8")
    assert "hunter2" not in text
    assert "[REDACTED]" in text


def test_a_failed_slot_is_not_retried_by_the_next_tick(tmp_path: Path) -> None:
    deps, q = make_deps(tmp_path, "p")
    import dataclasses

    def boom(_slot: object) -> str:
        raise RuntimeError("down")

    tick_project("p", daily(), NOW, dataclasses.replace(deps, enqueue=boom), since=SINCE)
    assert tick_project("p", daily(), NOW + timedelta(minutes=10), deps, since=SINCE) == []
    assert len(q) == 0


def _health(cfg: ScheduleConfig, last, now, interval: int = 60):
    return scheduler_health(cfg, last, now, tick_interval_s=interval)


def test_a_schedule_that_never_ticked_is_never_shown_healthy() -> None:
    h = _health(daily(), None, NOW)
    assert h.state is SchedulerHealth.NEVER_TICKED
    assert h.since is None


@pytest.mark.parametrize(
    ("age", "state"),
    [(timedelta(hours=47, minutes=59), SchedulerHealth.HEALTHY),
     (timedelta(hours=48), SchedulerHealth.HEALTHY),
     (timedelta(hours=48, seconds=1), SchedulerHealth.STALE)],
    ids=["47h59", "48h-exactly", "48h-plus-1s"],
)
def test_a_daily_rule_is_stale_after_two_intervals_of_48_hours(age, state) -> None:
    h = _health(daily(), NOW - age, NOW)
    assert h.state is state
    if state is SchedulerHealth.STALE:
        assert h.since == NOW - age  # "scheduler stale since <time>"


@pytest.mark.parametrize(
    ("age_s", "state"),
    [(119, SchedulerHealth.HEALTHY), (120, SchedulerHealth.HEALTHY),
     (121, SchedulerHealth.STALE)],
)
def test_a_one_off_or_weekly_schedule_is_stale_after_two_tick_timer_intervals(
    age_s: int, state: SchedulerHealth
) -> None:
    cfg = ScheduleConfig.model_validate(
        {"mode": "custom", "owner": "u", "weekly": {"weekdays": [0], "at": "09:00"}})
    assert _health(cfg, NOW - timedelta(seconds=age_s), NOW).state is state


def test_the_tick_interval_comes_from_the_env_and_falls_back_to_60() -> None:
    assert tick_interval_from_env({}) == 60
    assert tick_interval_from_env({"AUTOTESTER_TICK_INTERVAL_S": "30"}) == 30
    for bad in ("0", "-5", "abc", "", "99999999"):
        assert tick_interval_from_env({"AUTOTESTER_TICK_INTERVAL_S": bad}) == 60
    cfg = ScheduleConfig.model_validate(
        {"mode": "custom", "owner": "u", "one_offs": ["2026-12-01T10:00"]})
    assert _health(cfg, NOW - timedelta(seconds=61), NOW, interval=30).state is (
        SchedulerHealth.STALE)


def test_manual_schedule_has_no_scheduler_health_to_report() -> None:
    assert _health(ScheduleConfig(), None, NOW).state is SchedulerHealth.NOT_APPLICABLE


def test_heartbeat_round_trips_replaces_and_leaves_no_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "state" / "last_tick.json"
    assert read_heartbeat(path) is None
    write_heartbeat(path, NOW)
    write_heartbeat(path, NOW + timedelta(minutes=1))
    assert read_heartbeat(path) == NOW + timedelta(minutes=1)
    assert [p.name for p in path.parent.iterdir()] == ["last_tick.json"]


def test_a_corrupt_heartbeat_reads_as_never_ticked_not_as_healthy(tmp_path: Path) -> None:
    """A half-written file after a power cut must not make the card say healthy."""
    path = tmp_path / "last_tick.json"
    path.write_text("{not json", encoding="utf-8")
    assert read_heartbeat(path) is None

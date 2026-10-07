"""TS2 (pure half): `due()` and slot arithmetic are timezone-correct and take the clock as an
argument. Fake clock only; nothing here sleeps or reads the environment.
"""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from autotester.schema.schedule import ScheduleConfig, slot_key
from autotester.stages.schedule_time import slot_instants
from autotester.stages.scheduler import due


def utc(*a: int) -> datetime:
    return datetime(*a, tzinfo=UTC)


def fixed(at: str, tz: str = "UTC") -> ScheduleConfig:
    return ScheduleConfig.model_validate(
        {"mode": "fixed", "fixed_at": at, "timezone": tz, "owner": "u1"})


def span(cfg: ScheduleConfig, a: datetime, b: datetime) -> list[datetime]:
    return slot_instants(cfg, a, b)


def test_utc_daily_rule_yields_one_slot_per_day() -> None:
    got = span(fixed("00:00"), utc(2026, 10, 7, 0, 0), utc(2026, 10, 9, 23, 59))
    assert got == [utc(2026, 10, 7), utc(2026, 10, 8), utc(2026, 10, 9)]


def test_kolkata_has_no_dst_and_offset_is_five_thirty() -> None:
    got = span(fixed("09:00", "Asia/Kolkata"), utc(2026, 1, 1), utc(2026, 8, 1))
    assert len(got) > 200
    assert {g.time() for g in got} == {utc(2026, 1, 1, 3, 30).time()}


def test_new_york_spring_forward_0230_fires_once_at_first_valid_instant() -> None:
    """02:30 does not exist on 2026-03-08 in New York; the day fires once, at the 03:00 EDT jump
    (07:00 UTC) = the first valid instant after the gap."""
    got = span(fixed("02:30", "America/New_York"), utc(2026, 3, 7), utc(2026, 3, 10))
    assert got == [utc(2026, 3, 7, 7, 30), utc(2026, 3, 8, 7, 0), utc(2026, 3, 9, 6, 30)]


def test_new_york_fall_back_0130_fires_once_not_twice() -> None:
    """01:30 happens twice on 2026-11-01; the rule fires on the first occurrence only."""
    got = span(fixed("01:30", "America/New_York"), utc(2026, 10, 31), utc(2026, 11, 3))
    assert got == [utc(2026, 10, 31, 5, 30), utc(2026, 11, 1, 5, 30), utc(2026, 11, 2, 6, 30)]


def test_weekly_rule_is_judged_on_the_local_calendar_day_across_midnight() -> None:
    """Monday 00:30 in Kolkata is Sunday 19:00 UTC: the weekday follows the LOCAL date."""
    cfg = ScheduleConfig.model_validate({
        "mode": "custom", "owner": "u1", "timezone": "Asia/Kolkata",
        "weekly": {"weekdays": [0], "at": "00:30"}})
    got = span(cfg, utc(2026, 10, 11), utc(2026, 10, 19))
    assert got == [utc(2026, 10, 11, 19, 0), utc(2026, 10, 18, 19, 0)]  # Mondays 12 and 19


def test_manual_and_paused_schedules_produce_no_slot_however_long_the_window() -> None:
    assert span(ScheduleConfig(), utc(2026, 1, 1), utc(2026, 12, 31)) == []
    paused = fixed("09:00").model_copy(update={"paused": True})
    d = due(paused, utc(2026, 10, 7, 12), set(), project="p", since=utc(2026, 10, 1))
    assert d.fire is None
    assert d.missed == ()


@pytest.mark.parametrize(
    ("now", "fires"),
    [
        (utc(2026, 10, 8, 8, 59, 59), False),  # a second before the instant
        (utc(2026, 10, 8, 9, 0, 0), True),     # exactly at the instant
        (utc(2026, 10, 8, 9, 0, 1), True),     # a second after
    ],
    ids=["one-second-before", "exactly-at", "one-second-after"],
)
def test_one_off_fires_at_or_after_its_instant_never_before(now: datetime, fires: bool) -> None:
    cfg = ScheduleConfig.model_validate(
        {"mode": "custom", "owner": "u1", "one_offs": ["2026-10-08T09:00"]})
    d = due(cfg, now, set(), project="p", since=now - timedelta(days=1))
    assert (d.fire is not None) is fires
    if fires:
        assert d.fire is not None
        assert d.fire.key == slot_key("p", cfg.mode, utc(2026, 10, 8, 9, 0))


def test_due_ignores_a_slot_that_is_already_claimed() -> None:
    cfg = fixed("09:00")
    key = slot_key("p", cfg.mode, utc(2026, 10, 8, 9, 0))
    d = due(cfg, utc(2026, 10, 8, 9, 0, 5), {key}, project="p", since=utc(2026, 10, 7))
    assert d.fire is None


def test_slot_key_is_deterministic_and_minute_precision() -> None:
    cfg = fixed("09:00")
    a = slot_key("proj", cfg.mode, utc(2026, 10, 8, 9, 0, 0))
    b = slot_key("proj", cfg.mode, utc(2026, 10, 8, 9, 0, 59))
    assert a == b == "proj:fixed:2026-10-08T09:00Z"


def test_due_takes_the_clock_as_an_argument_and_rejects_a_naive_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        due(fixed("09:00"), datetime(2026, 10, 8, 9, 0), set(), project="p",
            since=utc(2026, 10, 7))


@pytest.mark.xfail(
    strict=True,
    reason="OWED: tzdata must be a declared dependency (TS2, Windows has no zone data) but a new "
    "dependency needs a D-entry from Umesh; remove this xfail when pyproject lists tzdata",
)
def test_tzdata_is_a_declared_dependency_for_windows() -> None:
    """Windows ships no IANA database, so zoneinfo needs the `tzdata` wheel (TS2)."""
    toml = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    names = {d.split(">")[0].split("=")[0].split("[")[0].strip().lower()
             for d in toml["project"]["dependencies"]}
    assert "tzdata" in names

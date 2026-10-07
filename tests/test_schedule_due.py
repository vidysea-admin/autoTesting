"""TS2 (pure half): `due()` and slot arithmetic are timezone-correct and take the clock as an
argument. Fake clock only; nothing here sleeps or reads the environment.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_ist_nine_oclock_is_0330_utc_every_day_of_the_year() -> None:
    """IST is a fixed +05:30 with no DST: 09:00 IST is 03:30 UTC in January and in July."""
    got = span(fixed("09:00", "IST"), utc(2026, 1, 1), utc(2026, 8, 1))
    assert len(got) > 200
    assert {g.time() for g in got} == {utc(2026, 1, 1, 3, 30).time()}
    assert utc(2026, 1, 15, 3, 30) in got
    assert utc(2026, 7, 15, 3, 30) in got


def test_both_supported_zones_give_known_instants_for_the_same_wall_time() -> None:
    """A user saves 18:00 once as UTC and once as IST; the instants are 5h30m apart."""
    window = (utc(2026, 10, 8), utc(2026, 10, 8, 23, 59))
    assert span(fixed("18:00", "UTC"), *window) == [utc(2026, 10, 8, 18, 0)]
    assert span(fixed("18:00", "IST"), *window) == [utc(2026, 10, 8, 12, 30)]


def test_ist_early_morning_slot_lands_on_the_previous_utc_date() -> None:
    """IST 00:00 is 18:30 UTC the day before; IST 05:00 is 23:30 UTC the day before."""
    got = span(fixed("00:00", "IST"), utc(2026, 10, 7), utc(2026, 10, 9))
    assert got == [utc(2026, 10, 7, 18, 30), utc(2026, 10, 8, 18, 30)]
    assert span(fixed("05:00", "IST"), utc(2026, 10, 7), utc(2026, 10, 8, 23, 59)) == [
        utc(2026, 10, 7, 23, 30), utc(2026, 10, 8, 23, 30)]


def test_ist_late_evening_slot_stays_on_the_same_utc_date() -> None:
    assert span(fixed("23:59", "IST"), utc(2026, 10, 8), utc(2026, 10, 8, 23, 59)) == [
        utc(2026, 10, 8, 18, 29)]


def test_weekly_rule_is_judged_on_the_local_calendar_day_across_ist_midnight() -> None:
    """Monday 00:30 IST is Sunday 19:00 UTC: the weekday follows the LOCAL (IST) date."""
    cfg = ScheduleConfig.model_validate({
        "mode": "custom", "owner": "u1", "timezone": "IST",
        "weekly": {"weekdays": [0], "at": "00:30"}})
    got = span(cfg, utc(2026, 10, 11), utc(2026, 10, 19))
    assert got == [utc(2026, 10, 11, 19, 0), utc(2026, 10, 18, 19, 0)]  # IST Mondays 12 and 19
    sunday = cfg.model_copy(update={"weekly": cfg.weekly.model_copy(update={"weekdays": [6]})})
    assert span(sunday, utc(2026, 10, 11), utc(2026, 10, 19)) == [utc(2026, 10, 17, 19, 0)]


def test_a_utc_weekly_rule_does_not_shift_with_the_ist_date() -> None:
    """The same Monday 00:30 rule in UTC fires at Monday 00:30 UTC."""
    cfg = ScheduleConfig.model_validate({
        "mode": "custom", "owner": "u1", "timezone": "UTC",
        "weekly": {"weekdays": [0], "at": "00:30"}})
    assert span(cfg, utc(2026, 10, 11), utc(2026, 10, 19, 1)) == [
        utc(2026, 10, 12, 0, 30), utc(2026, 10, 19, 0, 30)]


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

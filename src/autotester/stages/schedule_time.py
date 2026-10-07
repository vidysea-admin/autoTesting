"""Slot arithmetic: which UTC instants does a schedule mean to fire at, inside a window?

Pure: no clock, no file, no environment. A schedule yields at most one instant per local
calendar day per rule (so there is no interval floor to configure) and every instant is on a
whole minute. Zones are the fixed offsets `UTC` and `IST` (`core.localtime`), so one local time
is always exactly one instant. `manual` and `paused` schedules yield nothing.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo

from autotester.core.localtime import resolve_local, zone
from autotester.schema.schedule import ScheduleConfig, ScheduleMode


def _hhmm(text: str) -> time:
    return time(int(text[:2]), int(text[3:5]))


def _local_dates(start: datetime, end: datetime, tz: tzinfo) -> list[date]:
    # pad a day each side: the local date can differ from the UTC date
    first = start.astimezone(tz).date() - timedelta(days=1)
    last = end.astimezone(tz).date() + timedelta(days=1)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def slot_instants(schedule: ScheduleConfig, start: datetime, end: datetime) -> list[datetime]:
    """Sorted, de-duplicated UTC instants with `start <= instant <= end` (both inclusive)."""
    if schedule.mode is ScheduleMode.MANUAL or schedule.paused:
        return []
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    tz = zone(schedule.timezone)
    found: set[datetime] = set()
    if schedule.mode is ScheduleMode.FIXED and schedule.fixed_at is not None:
        at = _hhmm(schedule.fixed_at)
        for day in _local_dates(start, end, tz):
            found.add(resolve_local(datetime.combine(day, at), tz))
    elif schedule.mode is ScheduleMode.CUSTOM:
        found.update(schedule.one_off_instants())
        if schedule.weekly is not None:
            at = _hhmm(schedule.weekly.at)
            for day in _local_dates(start, end, tz):
                if day.weekday() in schedule.weekly.weekdays:
                    found.add(resolve_local(datetime.combine(day, at), tz))
    return sorted(i for i in found if start <= i <= end)

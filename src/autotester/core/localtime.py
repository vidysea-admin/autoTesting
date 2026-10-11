"""Fixed-offset time zones and local-to-UTC conversion for the scheduler.

Its one job: turn "09:30 on this date in zone Z" into one UTC instant. Umesh's decision
(2026-10-07) limits schedules to `UTC` and `IST` (+05:30). Both are fixed offsets with no
daylight saving, so this uses `datetime.timezone` only: no `zoneinfo`, no `tzdata`, no zone
database, and it behaves the same on Windows and Ubuntu. Every local time maps to exactly one
instant, so there is no gap or repeated time to resolve.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo

_ZONES: dict[str, tzinfo] = {
    "UTC": UTC,
    "IST": timezone(timedelta(hours=5, minutes=30), "IST"),
}


class UnknownZone(ValueError):
    """The name is not one of the supported zones."""


def zone(name: str) -> tzinfo:
    """`UTC` or `IST`. Anything else raises `UnknownZone` naming the allowed values."""
    try:
        return _ZONES[name]
    except (KeyError, TypeError):
        raise UnknownZone(f"unknown time zone {name!r}; use {' or '.join(_ZONES)}") from None


def resolve_local(naive: datetime, tz: tzinfo) -> datetime:
    """The aware UTC instant for a naive local wall-clock time in `tz`."""
    if naive.tzinfo is not None:
        raise ValueError("resolve_local needs a naive local datetime")
    return naive.replace(tzinfo=tz).astimezone(UTC)

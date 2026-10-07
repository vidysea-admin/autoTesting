"""Zone lookup and DST-correct conversion of a local wall-clock time to a UTC instant.

Its one job: turn "09:30 on this date in zone Z" into exactly one UTC instant, naming the
two awkward cases (a time that does not exist, a time that happens twice) instead of
leaving them to whatever `datetime.replace(tzinfo=...)` happens to do.

Rules (TS2): a time inside a spring-forward gap resolves to the first valid instant, the
moment the clocks jump; a time that happens twice resolves to its first occurrence.
`UTC` never touches the zone database, so it works on a Windows box with no `tzdata`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo
from enum import StrEnum
from zoneinfo import ZoneInfo

_MINUTE = timedelta(minutes=1)


class UnknownZone(ValueError):
    """The name is not an IANA zone this machine can resolve."""


class LocalKind(StrEnum):
    NORMAL = "normal"
    GAP = "gap"  # the wall-clock time does not exist (spring forward)
    OVERLAP = "overlap"  # the wall-clock time happens twice (fall back)


def zone(name: str) -> tzinfo:
    """Resolve an IANA name. Raises `UnknownZone` for anything else, never a path error."""
    if name == "UTC":
        return UTC
    try:
        return ZoneInfo(name)
    except Exception as exc:  # ZoneInfoNotFoundError, ValueError (bad key), OSError, TypeError
        raise UnknownZone(f"unknown time zone {name!r}") from exc


def resolve_local(naive: datetime, tz: tzinfo) -> tuple[datetime, LocalKind]:
    """UTC instant (aware) for a naive local time, and which kind of time it was."""
    if naive.tzinfo is not None:
        raise ValueError("resolve_local needs a naive local datetime")
    first = naive.replace(tzinfo=tz, fold=0)
    second = naive.replace(tzinfo=tz, fold=1)
    off_first, off_second = first.utcoffset(), second.utcoffset()
    assert off_first is not None
    assert off_second is not None
    utc_first = (naive - off_first).replace(tzinfo=UTC)
    if off_first == off_second:
        return utc_first, LocalKind.NORMAL
    if utc_first.astimezone(tz).replace(tzinfo=None) == naive:
        return utc_first, LocalKind.OVERLAP  # both readings are real: take the first
    utc_second = (naive - off_second).replace(tzinfo=UTC)
    return _transition(tz, utc_second, utc_first, off_second), LocalKind.GAP


def _transition(tz: tzinfo, lo: datetime, hi: datetime, after: timedelta) -> datetime:
    """First whole minute in (lo, hi] whose offset is `after`: the instant the clocks jump."""
    low, high = 0, int((hi - lo) / _MINUTE)  # offset(lo + low min) != after, offset(hi) == after
    while high - low > 1:
        mid = (low + high) // 2
        if (lo + mid * _MINUTE).astimezone(tz).utcoffset() == after:
            high = mid
        else:
            low = mid
    return lo + high * _MINUTE

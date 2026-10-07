"""TS1 (schema half): `ScheduleConfig` is a typed, bounded setting; invalid values are refused.

Every case is a value a real user can type into the schedule card (R51 / HO22): a bad time,
an unknown zone, a one-off already in the past, an empty weekday set.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from autotester.schema.schedule import (
    ScheduleConfig,
    ScheduleInvalid,
    ScheduleMode,
    default_timezone,
)

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)

VALID = {
    "manual default": {},
    "manual explicit": {"mode": "manual"},
    "fixed utc": {"mode": "fixed", "fixed_at": "09:00", "owner": "u1"},
    "fixed midnight": {"mode": "fixed", "fixed_at": "00:00", "owner": "u1"},
    "fixed 23:59 kolkata": {
        "mode": "fixed", "fixed_at": "23:59", "timezone": "Asia/Kolkata", "owner": "u1"},
    "fixed new york": {
        "mode": "fixed", "fixed_at": "02:30", "timezone": "America/New_York", "owner": "u1"},
    "custom one-off": {"mode": "custom", "one_offs": ["2026-10-09T10:00"], "owner": "u1"},
    "custom weekly": {
        "mode": "custom", "weekly": {"weekdays": [0], "at": "08:15"}, "owner": "u1"},
    "custom all weekdays": {
        "mode": "custom", "weekly": {"weekdays": [0, 1, 2, 3, 4, 5, 6], "at": "08:15"},
        "owner": "u1"},
    "custom both": {
        "mode": "custom", "one_offs": ["2026-10-09T10:00"],
        "weekly": {"weekdays": [5, 6], "at": "12:00"}, "owner": "u1"},
    "custom two one-offs": {
        "mode": "custom", "one_offs": ["2026-10-09T10:00", "2026-10-10T10:00"], "owner": "u1"},
    "paused fixed": {"mode": "fixed", "fixed_at": "09:00", "owner": "u1", "paused": True},
}

INVALID = {
    "25:00": ({"mode": "fixed", "fixed_at": "25:00", "owner": "u"}, "fixed_at"),
    "24:00": ({"mode": "fixed", "fixed_at": "24:00", "owner": "u"}, "fixed_at"),
    "9:5": ({"mode": "fixed", "fixed_at": "9:5", "owner": "u"}, "fixed_at"),
    "9:05": ({"mode": "fixed", "fixed_at": "9:05", "owner": "u"}, "fixed_at"),
    "09:60": ({"mode": "fixed", "fixed_at": "09:60", "owner": "u"}, "fixed_at"),
    "fixed without time": ({"mode": "fixed", "owner": "u"}, "fixed_at"),
    "unknown zone": (
        {"mode": "fixed", "fixed_at": "09:00", "owner": "u", "timezone": "Mars/Olympus"},
        "timezone"),
    "empty zone": (
        {"mode": "fixed", "fixed_at": "09:00", "owner": "u", "timezone": ""}, "timezone"),
    "path-like zone": (
        {"mode": "fixed", "fixed_at": "09:00", "owner": "u", "timezone": "../etc/passwd"},
        "timezone"),
    "weekday 7": (
        {"mode": "custom", "weekly": {"weekdays": [7], "at": "09:00"}, "owner": "u"}, "weekdays"),
    "weekday -1": (
        {"mode": "custom", "weekly": {"weekdays": [-1], "at": "09:00"}, "owner": "u"},
        "weekdays"),
    "empty weekday set": (
        {"mode": "custom", "weekly": {"weekdays": [], "at": "09:00"}, "owner": "u"}, "weekdays"),
    "duplicate weekday": (
        {"mode": "custom", "weekly": {"weekdays": [1, 1], "at": "09:00"}, "owner": "u"},
        "weekdays"),
    "custom with nothing": ({"mode": "custom", "owner": "u"}, "custom"),
    "duplicate one-off": (
        {"mode": "custom", "one_offs": ["2026-10-09T10:00", "2026-10-09T10:00"], "owner": "u"},
        "one_offs"),
    "past one-off": (
        {"mode": "custom", "one_offs": ["2026-10-07T11:59"], "owner": "u"}, "one_offs"),
    "one-off in DST gap": (
        {"mode": "custom", "one_offs": ["2027-03-14T02:30"], "owner": "u",
         "timezone": "America/New_York"}, "one_offs"),
    "one-off with offset": (
        {"mode": "custom", "one_offs": ["2026-10-09T10:00:00+05:30"], "owner": "u"}, "one_offs"),
    "one-off with seconds": (
        {"mode": "custom", "one_offs": ["2026-10-09T10:00:30"], "owner": "u"}, "one_offs"),
    "manual carrying a time": ({"mode": "manual", "fixed_at": "09:00"}, "manual"),
    "fixed carrying weekly": (
        {"mode": "fixed", "fixed_at": "09:00", "owner": "u",
         "weekly": {"weekdays": [0], "at": "09:00"}}, "fixed"),
    "custom carrying fixed_at": (
        {"mode": "custom", "fixed_at": "09:00", "one_offs": ["2026-10-09T10:00"], "owner": "u"},
        "custom"),
    "fixed without owner": ({"mode": "fixed", "fixed_at": "09:00"}, "owner"),
    "unknown key": ({"mode": "manual", "interval_minutes": 5}, "interval_minutes"),
    "unknown mode": ({"mode": "hourly"}, "mode"),
    "too many one-offs": (
        {"mode": "custom", "owner": "u",
         "one_offs": [f"2026-11-{d:02d}T10:00" for d in range(1, 29)]
         + [f"2026-12-{d:02d}T10:00" for d in range(1, 29)]}, "one_offs"),
}


@pytest.mark.parametrize("data", VALID.values(), ids=VALID.keys())
def test_valid_schedule_is_accepted_when_a_user_saves_it(data: dict) -> None:
    cfg = ScheduleConfig.parse_for_save(data, now=NOW)
    assert cfg.mode in set(ScheduleMode)
    assert cfg.timezone  # never empty: default is AUTOTESTER_TIMEZONE else UTC


@pytest.mark.parametrize(("data", "field"), INVALID.values(), ids=INVALID.keys())
def test_invalid_schedule_is_refused_with_a_reason_naming_the_field(
    data: dict, field: str
) -> None:
    with pytest.raises(ScheduleInvalid) as err:
        ScheduleConfig.parse_for_save(data, now=NOW)
    assert field in err.value.field or field in err.value.reason


def test_manual_is_the_default_and_a_project_json_without_schedule_loads_as_manual() -> None:
    """A legacy project.json has no schedule at all (TF6 back-compat)."""
    cfg = ScheduleConfig()
    assert cfg.mode is ScheduleMode.MANUAL
    assert cfg.paused is False
    assert not cfg.one_offs
    assert cfg.weekly is None


def test_default_timezone_follows_autotester_timezone_else_utc() -> None:
    """An operator sets AUTOTESTER_TIMEZONE in .env; a typo there must not break every schedule."""
    assert default_timezone({}) == "UTC"
    assert default_timezone({"AUTOTESTER_TIMEZONE": "Asia/Kolkata"}) == "Asia/Kolkata"
    assert default_timezone({"AUTOTESTER_TIMEZONE": "Not/AZone"}) == "UTC"


def test_round_trip_is_lossless_for_a_saved_custom_schedule() -> None:
    cfg = ScheduleConfig.parse_for_save(VALID["custom both"], now=NOW)
    again = ScheduleConfig.model_validate_json(cfg.model_dump_json())
    assert again == cfg

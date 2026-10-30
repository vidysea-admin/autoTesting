"""The per-project schedule (G5, R51): a typed, bounded setting plus the slot-record vocabulary.

Three modes (D-072 item 9): `manual` (button only, the default, produces no slot), `fixed`
(one daily `HH:MM`) and `custom` (a time the user selects: one-off date-times and/or one weekly
rule). Every time is a local wall-clock time in the schedule's `timezone`; the instants the
scheduler fires at are derived by `stages/schedule_time.py`, never stored here.

Time zones (Umesh, 2026-10-07): a schedule supports only `UTC` and `IST` (a fixed +05:30
offset). Neither has daylight saving, so there is no zone database, no `tzdata` dependency and
no DST rule anywhere. Anything else is refused at save, naming the two allowed values.

Vocabulary note: `ScheduleMode`, `SlotOutcome`, `SchedulerHealth`, `ScheduleZone` and
`CredentialState` are Group 10
closed vocabularies. Their home is `schema/team_enums.py` (T-205/TF8); they are imported here so
`from autotester.schema.schedule import SlotOutcome` keeps working.

`ScheduleConfig.parse_for_save` is the one door for user input: it refuses bad values with a
reason that names the field, so a caller can store nothing. Weekdays are Python's: 0 = Monday.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from autotester.core.localtime import resolve_local, zone
from autotester.schema.team_enums import (  # noqa: F401  (re-exported: importers keep their path)
    CredentialState,
    ScheduleMode,
    SchedulerHealth,
    ScheduleZone,
    SlotOutcome,
)

TIMEZONE_ENV = "AUTOTESTER_TIMEZONE"
MAX_ONE_OFFS = 50
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ScheduleInvalid(ValueError):
    """A value was refused at save. `field` names it; the caller stores nothing."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


def default_timezone(environ: Mapping[str, str]) -> ScheduleZone:
    """`AUTOTESTER_TIMEZONE` if it is `UTC` or `IST`, else UTC (a typo must not break saves)."""
    name = environ.get(TIMEZONE_ENV, "").strip()
    return ScheduleZone(name) if name in set(ScheduleZone) else ScheduleZone.UTC


def _env_default_timezone() -> ScheduleZone:
    return default_timezone(os.environ)


def slot_key(project: str, mode: ScheduleMode, instant: datetime) -> str:
    """`<project>:<mode>:<UTC instant to the minute>`: deterministic, never wall-clock-at-tick."""
    return f"{project}:{mode.value}:{instant.astimezone(UTC).strftime('%Y-%m-%dT%H:%MZ')}"


class WeeklyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekdays: list[int] = Field(description="0 = Monday .. 6 = Sunday; non-empty, no duplicates")
    at: str = Field(description="HH:MM local")

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("weekdays: pick at least one weekday")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("weekdays: each weekday must be 0 (Mon) to 6 (Sun)")
        if len(set(v)) != len(v):
            raise ValueError("weekdays: a weekday is listed twice")
        return sorted(v)

    @field_validator("at")
    @classmethod
    def _at(cls, v: str) -> str:
        return _check_hhmm(v, "at")


def _check_hhmm(v: str, field: str) -> str:
    if not _HHMM.match(v):
        raise ValueError(f"{field}: must be HH:MM, 00:00 to 23:59 (got {v!r})")
    return v


class ScheduleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ScheduleMode = ScheduleMode.MANUAL
    fixed_at: str | None = Field(default=None, description="daily HH:MM local (mode fixed)")
    one_offs: list[datetime] = Field(
        default_factory=list, description="naive local date-times; each fires once (mode custom)")
    weekly: WeeklyRule | None = None
    timezone: ScheduleZone = Field(
        default_factory=_env_default_timezone, description="UTC or IST (+05:30, no DST)")
    owner: str | None = Field(default=None, description="user who last saved; requested_by")
    paused: bool = False

    @field_validator("fixed_at")
    @classmethod
    def _fixed_at(cls, v: str | None) -> str | None:
        return None if v is None else _check_hhmm(v, "fixed_at")

    @field_validator("timezone", mode="before")
    @classmethod
    def _timezone(cls, v: object) -> object:
        if v not in [z.value for z in ScheduleZone]:
            allowed = " or ".join(z.value for z in ScheduleZone)
            raise ValueError(f"timezone: must be {allowed} (got {v!r})")
        return v

    @field_validator("one_offs")
    @classmethod
    def _one_offs(cls, v: list[datetime]) -> list[datetime]:
        if len(v) > MAX_ONE_OFFS:
            raise ValueError(f"one_offs: at most {MAX_ONE_OFFS} one-off times")
        for stamp in v:
            if stamp.tzinfo is not None:
                raise ValueError("one_offs: give local date-times without a UTC offset")
            if stamp.second or stamp.microsecond:
                raise ValueError("one_offs: minute precision only (no seconds)")
        if len(set(v)) != len(v):
            raise ValueError("one_offs: the same date-time is listed twice")
        return sorted(v)

    @model_validator(mode="after")
    def _shape(self) -> ScheduleConfig:
        mode, extras = self.mode, []
        if self.fixed_at is not None:
            extras.append("fixed_at")
        if self.one_offs:
            extras.append("one_offs")
        if self.weekly is not None:
            extras.append("weekly")
        if mode is ScheduleMode.MANUAL:
            if extras:
                raise ValueError(f"manual: takes no times (remove {', '.join(extras)})")
            return self
        if not self.owner:
            raise ValueError("owner: a scheduled project needs the user who saved it")
        if mode is ScheduleMode.FIXED:
            if self.fixed_at is None:
                raise ValueError("fixed_at: mode fixed needs a daily HH:MM")
            if self.one_offs or self.weekly is not None:
                raise ValueError("fixed: takes only fixed_at (remove one_offs / weekly)")
            return self
        if self.fixed_at is not None:
            raise ValueError("custom: takes one_offs and/or weekly, not fixed_at")
        if not self.one_offs and self.weekly is None:
            raise ValueError("custom: give at least one one-off time or a weekly rule")
        return self

    def one_off_instants(self) -> list[datetime]:
        """UTC instants of the one-offs, in order."""
        tz = zone(self.timezone)
        return [resolve_local(s, tz) for s in self.one_offs]

    @classmethod
    def parse_for_save(cls, data: Mapping[str, Any], *, now: datetime) -> ScheduleConfig:
        """The one door for user input. Raises `ScheduleInvalid`; stores nothing."""
        try:
            cfg = cls.model_validate(dict(data))
        except ValidationError as exc:
            first = exc.errors()[0]
            msg = str(first["msg"]).removeprefix("Value error, ")
            loc = ".".join(str(p) for p in first["loc"])
            head, _, rest = msg.partition(": ")
            if loc:
                raise ScheduleInvalid(loc, rest or msg) from exc
            raise ScheduleInvalid(head, rest or msg) from exc
        for i, instant in enumerate(cfg.one_off_instants()):
            if instant < now:
                raise ScheduleInvalid(f"one_offs.{i}", "is in the past")
        return cfg


class SlotRecord(BaseModel):
    """One append-only line per slot decision. Holds no secret: ids, instants and a short cause."""

    model_config = ConfigDict(extra="forbid")

    slot_key: str
    project: str
    mode: ScheduleMode
    instant: datetime
    recorded_at: datetime
    outcome: SlotOutcome
    entry_id: str | None = None
    blocking_entry_id: str | None = None
    superseded_by: str | None = None
    detail: str | None = None
    amended: bool = False  # an amendment line: the latest one per slot wins (TS7, append-only)


class SlotClaim(BaseModel):
    """The content of a claim marker: what the winning tick decided, so a crash can be re-driven."""

    model_config = ConfigDict(extra="forbid")

    slot_key: str
    mode: ScheduleMode
    instant: datetime
    claimed_at: datetime
    intended: SlotOutcome = Field(description="enqueued | catch_up | missed, as decided at claim")
    superseded_by: str | None = None


class Heartbeat(BaseModel):
    """The tick heartbeat file: when the scheduler last ran, as ISO text."""

    model_config = ConfigDict(extra="ignore", strict=True)  # as tolerant as the old reader

    last_tick: str


class TickReport(BaseModel):
    """What one `autotester schedule tick` did: the JSON document of `--output json`.

    `exit_code`: 0 nothing due or all handled, 2 a slot blocked / refused / failed or a project
    errored, 3 a config was invalid. `errors` holds `<project>: <ExceptionClass>` only (a
    message may carry a secret). `would_fire` / `would_block` are filled by `--dry-run` alone."""

    model_config = ConfigDict(extra="forbid")

    tick_at: datetime
    dry_run: bool = False
    exit_code: int = Field(0, ge=0, le=3)
    records: list[SlotRecord] = Field(default_factory=list)
    would_fire: list[str] = Field(default_factory=list)
    would_block: list[str] = Field(default_factory=list)
    would_block_reasons: dict[str, str] = Field(default_factory=dict)  # slot key -> why (dry run)
    invalid: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

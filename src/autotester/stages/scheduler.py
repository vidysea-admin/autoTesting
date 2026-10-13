"""The scheduler core (G5): which slots are due, who may claim them, and what a tick records.

`due()` is pure (clock, markers and lower bound are arguments). `tick_project()` is the one
stateless pass over one project: it claims slots atomically (`schedule_store.claim`), asks the
injected queue for the project's active entries, and hands the winner to the injected
`enqueue` callable. It never starts a browser and imports no runner (TS6): the only way a run
begins is `deps.enqueue`, which the wiring slice points at the one launcher and the T-203 queue.

Rules implemented here: exactly one claim per slot (TS2); at most one catch-up per project per
tick, inside the grace window, the earlier in-window slots `missed` with `superseded_by`, every
older slot `missed` and never backfilled (TS3); a busy project records `skipped_overlap` and
enqueues nothing (TS4); an enqueue error records `failed` with its cause (TS7); a claim whose
winner died before recording is re-driven once it is older than `redrive_after_s` (TS2).
`deps.owner_guard` (HO24: the owner's rights at fire time, else `refused`) then `deps.gate` (TS5)
are asked before the queue is touched.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from autotester.schema.schedule import (
    ScheduleConfig,
    ScheduleMode,
    SchedulerHealth,
    SlotClaim,
    SlotOutcome,
    SlotRecord,
    slot_key,
)
from autotester.stages.schedule_store import (
    append_record,
    claim,
    claim_path,
    list_claims,
    read_records,
)
from autotester.stages.schedule_time import slot_instants

DEFAULT_GRACE_MINUTES = 60
DEFAULT_TICK_INTERVAL_S = 60
ON_TIME_S = 120
REDRIVE_AFTER_S = 120
MAX_LOOKBACK = timedelta(days=31)
DAILY_STALE_AFTER = timedelta(hours=48)
GRACE_ENV = "AUTOTESTER_SCHEDULE_GRACE_MINUTES"
TICK_INTERVAL_ENV = "AUTOTESTER_TICK_INTERVAL_S"
_KEY = re.compile(r"^(?P<project>.+):(?P<mode>fixed|custom):(?P<ts>\d{4}-\d\d-\d\dT\d\d:\d\dZ)$")


@dataclass(frozen=True)
class Slot:
    key: str
    instant: datetime
    mode: ScheduleMode


@dataclass(frozen=True)
class MissedSlot:
    slot: Slot
    superseded_by: str | None


@dataclass(frozen=True)
class Due:
    fire: Slot | None
    late: bool
    missed: tuple[MissedSlot, ...]


@dataclass(frozen=True)
class QueueSnapshot:
    """One run-queue entry as the scheduler needs it. `active` = queued or running, decided by
    whoever builds the snapshot from the real queue (T-203), so no status string is copied here."""

    id: str
    project: str
    active: bool
    slot_key: str | None = None


@dataclass(frozen=True)
class SchedulerStatus:
    state: SchedulerHealth
    since: datetime | None


@dataclass(frozen=True)
class TickDeps:
    claim_dir: Path
    records_path: Path  # THIS project's file (`schedule_store.project_records_path`)
    enqueue: Callable[[Slot], str]
    queue: Callable[[], Iterable[QueueSnapshot]]
    gate: Callable[[Slot], str | None]  # TS5: a refusal reason, or None. Required: no default allow
    scrub: Callable[[str], str]  # required like gate: a cause is never recorded unscrubbed
    owner_guard: Callable[[Slot], str | None] | None = None  # HO24: a refusal reason, or None


def _aware(stamp: datetime) -> datetime:
    if stamp.tzinfo is None:
        raise ValueError("clock values must be timezone-aware")
    return stamp.astimezone(UTC)


def due(
    schedule: ScheduleConfig,
    now: datetime,
    markers: Collection[str],
    *,
    project: str,
    since: datetime,
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
    on_time_s: int = ON_TIME_S,
) -> Due:
    """Pure. Slots with `since <= instant <= now` whose key is not in `markers`, split by grace."""
    now, since = _aware(now), _aware(since)
    if schedule.mode is ScheduleMode.MANUAL or schedule.paused:
        return Due(None, False, ())
    clock = now.replace(second=0, microsecond=0)
    grace = timedelta(minutes=grace_minutes)
    start = max(since, clock - MAX_LOOKBACK)
    pending = [Slot(slot_key(project, schedule.mode, i), i, schedule.mode)
               for i in slot_instants(schedule, start, now)]
    pending = [s for s in pending if s.key not in markers]
    inside = [s for s in pending if clock - s.instant <= grace]
    fire = inside[-1] if inside else None
    missed = [MissedSlot(s, None) for s in pending if clock - s.instant > grace]
    if fire is not None:
        missed += [MissedSlot(s, fire.key) for s in inside[:-1]]
    late = fire is not None and (now - fire.instant).total_seconds() >= on_time_s
    return Due(fire, late, tuple(sorted(missed, key=lambda m: m.slot.instant)))


def blocking_entry(entries: Iterable[QueueSnapshot], project: str) -> QueueSnapshot | None:
    return next((e for e in entries if e.active and e.project == project), None)


def _record(slot: Slot, project: str, now: datetime, outcome: SlotOutcome, **extra: str | None
            ) -> SlotRecord:
    return SlotRecord(slot_key=slot.key, project=project, mode=slot.mode, instant=slot.instant,
                      recorded_at=now, outcome=outcome, **extra)


def _fire(project: str, slot: Slot, intended: SlotOutcome, now: datetime, deps: TickDeps
          ) -> SlotRecord:
    """Decide a claimed slot: reuse its own entry, skip if busy, else enqueue; never raise."""
    try:
        snapshot = list(deps.queue())
        own = next((e for e in snapshot if e.slot_key == slot.key), None)
        if own is not None:
            return _record(slot, project, now, intended, entry_id=own.id)
        denied = deps.owner_guard(slot) if deps.owner_guard else None
        if denied is not None:  # HO24: the owner no longer holds the rights; nothing is enqueued
            return _record(slot, project, now, SlotOutcome.REFUSED,
                           detail=deps.scrub(denied)[:500])
        refusal = deps.gate(slot)  # before any queue or run work: a refusal leaves no trace
        if refusal is not None:
            return _record(slot, project, now, SlotOutcome.BLOCKED_NO_CREDENTIALS,
                           detail=deps.scrub(refusal)[:500])
        blocker = blocking_entry(snapshot, project)
        if blocker is not None:
            return _record(slot, project, now, SlotOutcome.SKIPPED_OVERLAP,
                           blocking_entry_id=blocker.id)
        return _record(slot, project, now, intended, entry_id=deps.enqueue(slot))
    except Exception as exc:  # recorded, never swallowed: a failed slot is shown, not absent
        cause = deps.scrub(f"{type(exc).__name__}: {exc}")[:500]
        return _record(slot, project, now, SlotOutcome.FAILED, detail=cause)


def _decide(project: str, now: datetime, deps: TickDeps, body: SlotClaim) -> SlotRecord | None:
    """Claim then record one slot. None when another tick won the claim."""
    if not claim(deps.claim_dir, body.slot_key, body):
        return None
    return _write(project, now, deps, body)


def _write(project: str, now: datetime, deps: TickDeps, body: SlotClaim) -> SlotRecord | None:
    """Decide and record one claimed slot. None when its record was already written."""
    slot = Slot(body.slot_key, body.instant, body.mode)
    if body.intended is SlotOutcome.MISSED:
        rec = _record(slot, project, now, SlotOutcome.MISSED, superseded_by=body.superseded_by)
    else:
        rec = _fire(project, slot, body.intended, now, deps)
    return rec if append_record(deps.records_path, rec) else None


def _rebuilt(deps: TickDeps, key: str, grace: timedelta) -> SlotClaim | None:
    """A claim file the winner never finished writing: rebuild its decision from the key."""
    m = _KEY.match(key)
    if m is None:
        return None
    instant = datetime.strptime(m["ts"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=UTC)
    mtime = datetime.fromtimestamp(claim_path(deps.claim_dir, key).stat().st_mtime, tz=UTC)
    intended = SlotOutcome.MISSED if mtime - instant > grace else SlotOutcome.ENQUEUED
    return SlotClaim(slot_key=key, mode=ScheduleMode(m["mode"]), instant=instant,
                     claimed_at=mtime, intended=intended)


def _redrive(project: str, now: datetime, deps: TickDeps,
             old: Mapping[str, SlotClaim | None], grace: timedelta, after_s: int
             ) -> list[SlotRecord]:
    """Finish claims whose winner died before writing a record (TS2 crash safety)."""
    done = {r.slot_key for r in read_records(deps.records_path)}
    out = []
    for key, body in old.items():
        if key in done or not key.startswith(f"{project}:"):
            continue
        body = body or _rebuilt(deps, key, grace)
        if body is None or (now - body.claimed_at).total_seconds() < after_s:
            continue
        rec = _write(project, now, deps, body)
        if rec is not None:
            out.append(rec)
    return out


def tick_project(
    project: str,
    schedule: ScheduleConfig,
    now: datetime,
    deps: TickDeps,
    *,
    since: datetime,
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
    redrive_after_s: int = REDRIVE_AFTER_S,
) -> list[SlotRecord]:
    """One stateless pass for one project. Returns the records this call wrote."""
    now = _aware(now)
    if schedule.mode is ScheduleMode.MANUAL or schedule.paused:
        return []
    old = list_claims(deps.claim_dir)
    result = due(schedule, now, set(old), project=project, since=since,
                 grace_minutes=grace_minutes)
    out: list[SlotRecord] = []
    for m in result.missed:
        body = SlotClaim(slot_key=m.slot.key, mode=m.slot.mode, instant=m.slot.instant,
                         claimed_at=now, intended=SlotOutcome.MISSED,
                         superseded_by=m.superseded_by)
        out += [r for r in [_decide(project, now, deps, body)] if r is not None]
    if result.fire is not None:
        label = SlotOutcome.CATCH_UP if result.late else SlotOutcome.ENQUEUED
        body = SlotClaim(slot_key=result.fire.key, mode=result.fire.mode,
                         instant=result.fire.instant, claimed_at=now, intended=label)
        out += [r for r in [_decide(project, now, deps, body)] if r is not None]
    out += _redrive(project, now, deps, old, timedelta(minutes=grace_minutes), redrive_after_s)
    return out


def _int_env(environ: Mapping[str, str], key: str, default: int, lo: int, hi: int
             ) -> tuple[int, str | None]:
    raw = environ.get(key)
    if raw is None:
        return default, None
    try:
        value = int(raw.strip())
    except ValueError:
        value = lo - 1
    if not lo <= value <= hi:
        return default, f"{key}={raw!r} is not an integer {lo}..{hi}; using {default}"
    return value, None


def grace_from_env(environ: Mapping[str, str]) -> tuple[int, str | None]:
    """Grace minutes (1..1440, default 60) and a warning when the env value was unusable."""
    return _int_env(environ, GRACE_ENV, DEFAULT_GRACE_MINUTES, 1, 1440)


def tick_interval_from_env(environ: Mapping[str, str]) -> int:
    return _int_env(environ, TICK_INTERVAL_ENV, DEFAULT_TICK_INTERVAL_S, 1, 86400)[0]


def scheduler_health(
    schedule: ScheduleConfig, last_tick: datetime | None, now: datetime, *,
    tick_interval_s: int = DEFAULT_TICK_INTERVAL_S,
) -> SchedulerStatus:
    """Stale once `now - last_tick` exceeds two intervals: 48 h for a daily rule, two tick-timer
    intervals for a custom (weekly / one-off) schedule. Never healthy before the first tick."""
    if schedule.mode is ScheduleMode.MANUAL:
        return SchedulerStatus(SchedulerHealth.NOT_APPLICABLE, None)
    if last_tick is None:
        return SchedulerStatus(SchedulerHealth.NEVER_TICKED, None)
    limit = (DAILY_STALE_AFTER if schedule.mode is ScheduleMode.FIXED
             else timedelta(seconds=2 * tick_interval_s))
    last = _aware(last_tick)
    if _aware(now) - last > limit:
        return SchedulerStatus(SchedulerHealth.STALE, last)
    return SchedulerStatus(SchedulerHealth.HEALTHY, last)

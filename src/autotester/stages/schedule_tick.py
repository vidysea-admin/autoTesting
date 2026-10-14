"""One stateless pass over every scheduled project, plus the heartbeat and `--dry-run` (TS7).

`run_tick` is what `autotester schedule tick` calls: for each `ScheduledProject` it asks
`tick_project` to claim, gate, enqueue and record (or, in a dry run, only asks `due()` what
would fire: no claim, no record, no enqueue, no heartbeat). It never starts a browser and
imports no runner (TS6). A project that raises is reported by exception class and the pass
carries on; the heartbeat is written at the end of every real tick, even a failing one, so
"stale" means the scheduler stopped, not that it had bad news.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from autotester.schema.schedule import ScheduleConfig, SlotOutcome, TickReport
from autotester.stages.schedule_store import list_claims, write_heartbeat
from autotester.stages.scheduler import DEFAULT_GRACE_MINUTES, TickDeps, due, tick_project

_BAD = (SlotOutcome.BLOCKED_NO_CREDENTIALS, SlotOutcome.REFUSED, SlotOutcome.FAILED)


@dataclass(frozen=True)
class ScheduledProject:
    project: str
    schedule: ScheduleConfig
    since: datetime


def _exit_code(report: TickReport) -> int:
    if report.invalid:
        return 3
    bad = any(r.outcome in _BAD for r in report.records)
    return 2 if bad or report.errors or report.would_block else 0


def run_tick(
    items: Iterable[ScheduledProject], now: datetime, *,
    deps_for: Callable[[str], TickDeps], heartbeat_path: Path | None,
    dry_run: bool = False, invalid: Sequence[str] = (),
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
    preview: Callable[[str], str | None] | None = None,
) -> TickReport:
    """`heartbeat_path=None` writes no heartbeat (a pass over one project proves nothing about
    the rest). `invalid` names the projects whose stored schedule failed to load (exit 3).
    `preview(project)` is the read-only credential check a dry run uses in place of the gate."""
    report = TickReport(tick_at=now, dry_run=dry_run, invalid=list(invalid))
    for item in items:
        try:
            deps = deps_for(item.project)
            if dry_run:
                _preview(report, item, now, deps, grace_minutes, preview)
            else:
                report.records += tick_project(item.project, item.schedule, now, deps,
                                               since=item.since, grace_minutes=grace_minutes)
        except Exception as exc:  # one broken project must not stop the rest
            report.errors.append(f"{item.project}: {type(exc).__name__}")
    report.exit_code = _exit_code(report)
    if not dry_run and heartbeat_path is not None:
        write_heartbeat(heartbeat_path, now)
    return report


def _preview(report: TickReport, item: ScheduledProject, now: datetime, deps: TickDeps,
             grace_minutes: int, preview: Callable[[str], str | None] | None) -> None:
    result = due(item.schedule, now, set(list_claims(deps.claim_dir)), project=item.project,
                 since=item.since, grace_minutes=grace_minutes)
    if result.fire is None:
        return
    why = preview(item.project) if preview is not None else None
    if why is None:
        report.would_fire.append(result.fire.key)
        return
    report.would_block.append(result.fire.key)
    report.would_block_reasons[result.fire.key] = why[:500]

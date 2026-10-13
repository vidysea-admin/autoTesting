"""Wires the scheduler core to the real world: the projects on disk, the run queue, the TS5 gate.

One job: turn "the projects that have a schedule" plus "a queue" into one `tick_all` pass.
`stages/scheduler.py` stays pure and queue-agnostic; this module is the only place that knows
where claims, records and the heartbeat live (`<data root>/.work/team/schedule/`), which
project files carry a schedule, and how a due slot becomes a queue entry.

A due slot is submitted with `trigger="schedule"`, the schedule owner as `requested_by` and its
`slot_key` (the queue's idempotency key, HO23). The queue's executor hands that origin to the
one launcher (`stages/run_launcher.py::launch_run`), which re-checks every gate. This module
holds no runner and starts nothing itself (TS6). `queue` is anything with `submit` and
`snapshot`; `persisted` lists another process's queue entries (the server's file), so a
tick that runs in its own process still sees a busy project (TS4).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple, Protocol

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths, repo_root, team_path
from autotester.schema.run_queue import ACTIVE, QueueEntry
from autotester.schema.schedule import ScheduleMode, TickReport
from autotester.stages.schedule_gate import credential_gate, refusal_for
from autotester.stages.schedule_owner import owner_guard
from autotester.stages.schedule_store import project_records_path, read_heartbeat
from autotester.stages.schedule_tick import ScheduledProject, run_tick
from autotester.stages.scheduler import DEFAULT_GRACE_MINUTES, QueueSnapshot, Slot, TickDeps
from autotester.store.project_store import ProjectStore


class Submitter(Protocol):
    """What the scheduler needs of the run queue (`ui/run_queue.py::RunQueue` satisfies it)."""

    def submit(self, project: str, *, requested_by: str | None = ..., trigger: str = ...,
               slot_key: str | None = ...) -> QueueEntry: ...

    def snapshot(self, project: str | None = None) -> list[QueueEntry]: ...


class NullQueue:
    """The queue of a `--dry-run`: it answers "nothing running" and refuses any submit."""

    def submit(self, project: str, **_: object) -> QueueEntry:
        raise RuntimeError("a dry run never enqueues")

    def snapshot(self, project: str | None = None) -> list[QueueEntry]:
        return []


class LazyQueue:
    """Opens the real queue on first use, so a tick with nothing to enqueue never builds one."""

    def __init__(self, open_queue: Callable[[], Submitter]) -> None:
        self._open, self._queue = open_queue, None

    def _get(self) -> Submitter:
        if self._queue is None:
            self._queue = self._open()
        return self._queue

    def submit(self, project: str, **kw: object) -> QueueEntry:
        return self._get().submit(project, **kw)  # type: ignore[arg-type]

    def snapshot(self, project: str | None = None) -> list[QueueEntry]:
        return self._get().snapshot(project)


class SchedulePaths(NamedTuple):
    claims: Path      # one marker file per claimed slot, all projects
    records: Path     # one `<project>.jsonl` of slot records per project
    heartbeat: Path   # `last_tick`, written at the end of every real tick


def schedule_paths(root: Path | None = None) -> SchedulePaths:
    return SchedulePaths(team_path("schedule", "claims", root=root),
                         team_path("schedule", "records", root=root),
                         team_path("schedule", "heartbeat.json", root=root))


def scheduled_projects(root: Path | None = None) -> tuple[list[ScheduledProject], list[str]]:
    """Every project whose schedule is not `manual`, and the slugs whose file cannot be loaded.

    `since` is when the project file was last written, but never later than the last heartbeat:
    an unrelated edit during an outage must not move the bound past a slot the scheduler never
    saw (it is then recorded `missed`, not dropped). The core's lookback still bounds it. The
    exact bound needs a `saved_at` on the schedule, set by the save route (held)."""
    heartbeat = read_heartbeat(schedule_paths(root).heartbeat)
    base = (root or repo_root()) / "projects"
    items: list[ScheduledProject] = []
    invalid: list[str] = []
    for config in sorted(base.glob("*/project.json")) if base.is_dir() else []:
        slug = config.parent.name
        try:
            project = ProjectStore(slug, root).load_project()
            since = datetime.fromtimestamp(config.stat().st_mtime, tz=UTC)
            since = min(since, heartbeat) if heartbeat else since
        except (ValueError, OSError):
            invalid.append(slug)
            continue
        if project and project.schedule and project.schedule.mode is not ScheduleMode.MANUAL:
            items.append(ScheduledProject(slug, project.schedule, since))
    return items, invalid


def _snapshots(queue: Submitter, persisted: Callable[[], list[QueueEntry]]
               ) -> list[QueueSnapshot]:
    seen: dict[str, QueueEntry] = {}
    for entry in [*queue.snapshot(), *persisted()]:
        seen.setdefault(entry.id, entry)
    return [QueueSnapshot(id=e.id, project=e.project, active=e.status in ACTIVE,
                          slot_key=e.slot_key) for e in seen.values()]


def real_gate(slug: str, root: Path | None) -> Callable[[Slot], str | None]:
    """The TS5 gate over the project as it is on disk right now."""
    store = ProjectStore(slug, root)
    project = store.load_project()
    if project is None:
        return lambda _slot: f"project '{slug}' no longer exists"
    return credential_gate(project, store)


def real_preview(slug: str, root: Path | None) -> str | None:
    """The read-only TS5 check a `--dry-run` uses in place of the gate."""
    store = ProjectStore(slug, root)
    project = store.load_project()
    return f"project '{slug}' no longer exists" if project is None else refusal_for(project, store)


def _scrubber(slug: str, root: Path | None) -> Callable[[str], str]:
    store = ProjectStore(slug, root)
    project = store.load_project()
    if project is None:
        return lambda text: text
    return SecretStore.load(project, ProjectPaths(slug, root).env_file, strict=False
                            ).redactor().scrub


def tick_all(
    now: datetime, *, queue: Submitter, root: Path | None = None,
    persisted: Callable[[], list[QueueEntry]] = list, only: str | None = None,
    dry_run: bool = False, grace_minutes: int = DEFAULT_GRACE_MINUTES,
    gate_for: Callable[[str], Callable[[Slot], str | None]] | None = None,
    preview: Callable[[str], str | None] | None = None,
) -> TickReport:
    """One stateless pass over every scheduled project (or `only` that one)."""
    paths = schedule_paths(root)
    items, invalid = scheduled_projects(root)
    if only is not None:
        items = [i for i in items if i.project == only]
        invalid = [slug for slug in invalid if slug == only]
    owners = {i.project: i.schedule.owner for i in items}

    def deps_for(slug: str) -> TickDeps:
        return TickDeps(
            claim_dir=paths.claims, records_path=project_records_path(paths.records, slug),
            enqueue=lambda slot: queue.submit(slug, requested_by=owners[slug], trigger="schedule",
                                              slot_key=slot.key).id,
            queue=lambda: _snapshots(queue, persisted),
            gate=(gate_for or (lambda s: real_gate(s, root)))(slug),
            scrub=_scrubber(slug, root),
            owner_guard=owner_guard(slug, owners[slug], ProjectStore(slug, root)))

    return run_tick(items, now, deps_for=deps_for, heartbeat_path=None if only else paths.heartbeat,
                    dry_run=dry_run, invalid=invalid, grace_minutes=grace_minutes,
                    preview=preview or (lambda slug: real_preview(slug, root)))

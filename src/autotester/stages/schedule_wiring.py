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

from autotester.auth.loopback import auth_disabled
from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired, require_project_approval
from autotester.core.paths import ProjectPaths, repo_root, team_path
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.schema.run_queue import ACTIVE, QueueEntry
from autotester.schema.schedule import ScheduleMode, SlotOutcome, TickReport
from autotester.stages.schedule_gate import credential_gate, refusal_for
from autotester.stages.schedule_owner import owner_guard, owner_refusal
from autotester.stages.schedule_store import (
    amend_record,
    project_records_path,
    read_heartbeat,
)
from autotester.stages.schedule_sweep import sweep_dead_enqueued
from autotester.stages.schedule_tick import ScheduledProject, run_tick
from autotester.stages.scheduler import DEFAULT_GRACE_MINUTES, QueueSnapshot, Slot, TickDeps
from autotester.store.filestore import exists_path, list_children, mtime_path
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
    for slug in list_children(base):
        config = base / slug / "project.json"
        if not exists_path(config):
            continue
        try:
            project = ProjectStore(slug, root).load_project()
            stamp = mtime_path(config)
            if stamp is None:
                raise FileNotFoundError(config)  # gone since the listing: named as invalid
            since = datetime.fromtimestamp(stamp, tz=UTC)
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
    if project is None:
        return f"project '{slug}' no longer exists"
    return (refusal_for(project, store) or _production_refusal(project, store)
            or (None if auth_disabled() else owner_refusal(slug, project.schedule.owner
                                                           if project.schedule else None)))


def _production_refusal(project: Project, store: ProjectStore) -> str | None:
    """Read-only twin of the real gate's D-088 step: a production project needs a human-granted
    signed row (`require_project_approval`); the preview must not say "would run" without one."""
    if not project.production:
        return None
    try:
        require_project_approval(store.list_approvals(), project=project,
                                 kind=ApprovalKind.LIVE_CASE, target=project.base_url)
    except ApprovalRequired as exc:
        return f"approval_required: {str(exc).splitlines()[0]}"
    return None


def record_worker_end(entry: QueueEntry, exc: BaseException, root: Path | None = None) -> bool:
    """TS7: a scheduled run's worker died after the enqueue, so its slot record (still
    `enqueued`) is rewritten `failed` with the exception CLASS only (a message may carry a
    secret). Never raises: the queue entry's own terminal state is what the caller keeps."""
    if entry.trigger != "schedule" or not entry.slot_key:
        return False
    outcome = SlotOutcome.REFUSED if type(exc).__name__ == "RunRefused" else SlotOutcome.FAILED
    detail = "run refused at start" if outcome is SlotOutcome.REFUSED else (
        f"worker ended: {type(exc).__name__}")
    try:
        path = project_records_path(schedule_paths(root).records, entry.project)
        return amend_record(path, entry.slot_key, outcome, detail)
    except OSError:
        return False


def _scrubber(slug: str, root: Path | None) -> Callable[[str], str]:
    store = ProjectStore(slug, root)
    project = store.load_project()
    if project is None:
        return lambda text: text
    return SecretStore.load(project, ProjectPaths(slug, root).env_file, strict=False
                            ).redactor().scrub


def _sweep(items: list[ScheduledProject], now: datetime, paths: SchedulePaths,
           queue: Submitter, persisted: Callable[[], list[QueueEntry]], root: Path | None) -> None:
    """TS7: amend slot records whose run was killed unseen. Never stops the tick."""
    for item in items:
        try:
            sweep_dead_enqueued(
                item.project, paths.records, now,
                lambda: {s.id for s in _snapshots(queue, persisted) if s.active},
                ProjectStore(item.project, root))
        except Exception:  # an unreadable queue means "unknown": leave the record as it is
            continue


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

    if not dry_run:
        _sweep(items, now, paths, queue, persisted, root)
    return run_tick(items, now, deps_for=deps_for, heartbeat_path=None if only else paths.heartbeat,
                    dry_run=dry_run, invalid=invalid, grace_minutes=grace_minutes,
                    preview=preview or (lambda slug: real_preview(slug, root)))

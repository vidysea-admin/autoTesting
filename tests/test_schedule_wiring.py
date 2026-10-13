"""T-200 wiring (TS6, HO23): a due slot becomes ONE entry in the real run queue, stamped with its
origin, and the queue's executor hands that origin to the one launcher.

Real `RunQueue` (manual spawner, no threads, no sleeps), real `ProjectStore` under a temp
root, a fake clock. Nothing here reaches a browser, a model or the network.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval
from schedule_fakes import daily, utc

from autotester.browser.session import BrowserSession
from autotester.schema.auth import Principal, all_permissions
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result, Trigger
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.run_queue import QueueEntry, QueueStatus
from autotester.schema.schedule import ScheduleConfig, SlotOutcome
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams
from autotester.stages.schedule_store import list_claims, project_records_path, read_records
from autotester.stages.schedule_wiring import (
    NullQueue,
    schedule_paths,
    scheduled_projects,
    tick_all,
)
from autotester.store.project_store import ProjectStore
from autotester.ui.run_queue import RunQueue

DUE = utc(2026, 10, 8, 9, 0, 10)
SAVED = utc(2026, 10, 7, 12)
ALLOW = lambda _project: (lambda _slot: None)  # noqa: E731  (the TS5 gate is tested in test_schedule_gate)


class Manual:
    """A spawner that holds workers until the test runs them."""

    def __init__(self) -> None:
        self.pending: list[Callable[[], None]] = []

    def __call__(self, job: Callable[[], None]) -> None:
        self.pending.append(job)

    def run_next(self) -> None:
        self.pending.pop(0)()


def _queue(runner: Callable[[QueueEntry], None] | None = None, path: Path | None = None,
           ) -> tuple[RunQueue, Manual]:
    manual = Manual()
    return RunQueue(limit=lambda: 2, spawn=manual, runner=runner or (lambda e: None),
                    path=(lambda: path) if path else None), manual


def _saved_at(store: ProjectStore, when: datetime) -> None:
    os.utime(store.paths.config, (when.timestamp(), when.timestamp()))


def _scheduled(root: Path, slug: str = "demo", schedule: ScheduleConfig | None = None,
               saved: datetime = SAVED) -> None:
    store = ProjectStore(slug, root)
    store.save_project(Project(
        slug=slug, name=slug, base_url="https://demo.test", allowed_domains=["demo.test"],
        schedule=schedule if schedule is not None else daily()))
    _saved_at(store, saved)


def _tick(root: Path, queue, now: datetime = DUE, **kw):
    return tick_all(now, root=root, queue=queue, gate_for=ALLOW, **kw)


# --- the queue's own idempotency key (HO23) -----------------------------------------------
def test_one_slot_key_is_one_queue_entry_even_across_a_restart(tmp_path: Path) -> None:
    file = tmp_path / "queue.json"
    queue, _ = _queue(path=file)
    first = queue.submit("demo", trigger="schedule", requested_by="u1", slot_key="demo:fixed:A")
    again = queue.submit("demo", trigger="schedule", requested_by="u1", slot_key="demo:fixed:A")
    assert again.id == first.id and len(queue.snapshot()) == 1
    restarted, _ = _queue(path=file)
    restarted.recover()
    third = restarted.submit("demo", trigger="schedule", requested_by="u1",
                             slot_key="demo:fixed:A")
    assert third.id == first.id and len(restarted.snapshot()) == 1


# --- the tick enqueues through the queue, stamped with its origin -------------------------
def test_a_due_slot_is_one_schedule_entry_stamped_with_owner_and_slot(tmp_path: Path) -> None:
    _scheduled(tmp_path)
    queue, manual = _queue()
    report = _tick(tmp_path, queue)
    entry = queue.snapshot()[0]
    assert report.exit_code == 0 and len(queue.snapshot()) == 1 and len(manual.pending) == 1
    assert (entry.trigger, entry.requested_by) == ("schedule", "u1")
    assert entry.slot_key == "demo:fixed:2026-10-08T09:00Z"
    assert [r.outcome for r in report.records] == [SlotOutcome.ENQUEUED]
    assert report.records[0].entry_id == entry.id


def test_two_ticks_for_one_slot_make_one_entry(tmp_path: Path) -> None:
    _scheduled(tmp_path)
    queue, _ = _queue()
    _tick(tmp_path, queue)
    second = _tick(tmp_path, queue, DUE.replace(second=40))
    assert len(queue.snapshot()) == 1 and second.records == []


def test_a_crash_between_claim_and_enqueue_is_redriven_into_one_entry(tmp_path: Path) -> None:
    _scheduled(tmp_path)
    paths = schedule_paths(tmp_path)
    queue, _ = _queue()
    boom = _queue()[0]
    boom.submit = lambda *a, **k: (_ for _ in ()).throw(SystemExit(1))  # type: ignore[method-assign]
    with pytest.raises(SystemExit):
        _tick(tmp_path, boom)
    assert len(list_claims(paths.claims)) == 1 and read_records(
        project_records_path(paths.records, "demo")) == []
    _tick(tmp_path, queue, DUE.replace(minute=3))          # past the 120 s re-drive age
    assert len(queue.snapshot()) == 1


def test_a_busy_project_in_the_servers_persisted_queue_is_a_skipped_overlap(
    tmp_path: Path,
) -> None:
    _scheduled(tmp_path)
    queue, manual = _queue()
    other = QueueEntry(id="run-busy", project="demo", status=QueueStatus.RUNNING)
    report = _tick(tmp_path, queue, persisted=lambda: [other])
    assert [r.outcome for r in report.records] == [SlotOutcome.SKIPPED_OVERLAP]
    assert report.records[0].blocking_entry_id == "run-busy"
    assert queue.snapshot() == [] and manual.pending == []


def test_three_days_down_runs_at_most_one_and_records_the_rest_missed(tmp_path: Path) -> None:
    _scheduled(tmp_path)
    queue, _ = _queue()
    later = utc(2026, 10, 11, 9, 20)                 # the slot 20 minutes ago is inside grace
    report = _tick(tmp_path, queue, later)
    outcomes = sorted(r.outcome.value for r in report.records)
    assert outcomes.count("catch_up") + outcomes.count("enqueued") == 1
    assert outcomes.count("missed") == 3 and len(queue.snapshot()) == 1


def test_a_gate_refusal_enqueues_nothing_and_is_recorded(tmp_path: Path) -> None:
    _scheduled(tmp_path)
    queue, manual = _queue()
    report = tick_all(DUE, root=tmp_path, queue=queue,
                      gate_for=lambda p: (lambda slot: "no_secretref: declare credentials"))
    assert [r.outcome for r in report.records] == [SlotOutcome.BLOCKED_NO_CREDENTIALS]
    assert report.exit_code == 2 and queue.snapshot() == [] and manual.pending == []


def test_a_dry_run_names_what_would_fire_and_touches_nothing(tmp_path: Path) -> None:
    _scheduled(tmp_path)
    paths = schedule_paths(tmp_path)
    report = tick_all(DUE, root=tmp_path, queue=NullQueue(), dry_run=True, gate_for=ALLOW,
                      preview=lambda _slug: None)
    assert report.would_fire == ["demo:fixed:2026-10-08T09:00Z"] and report.dry_run
    assert not paths.claims.exists() and not paths.heartbeat.exists()


def test_only_limits_the_pass_to_one_project(tmp_path: Path) -> None:
    _scheduled(tmp_path, "alpha")
    _scheduled(tmp_path, "beta")
    queue, _ = _queue()
    _tick(tmp_path, queue, only="beta")
    assert [e.project for e in queue.snapshot()] == ["beta"]


# --- which projects are scheduled ----------------------------------------------------------
def test_manual_and_unscheduled_projects_are_not_listed_and_a_broken_one_is_named(
    tmp_path: Path,
) -> None:
    _scheduled(tmp_path, "daily")
    _scheduled(tmp_path, "manual", ScheduleConfig())
    ProjectStore("plain", tmp_path).save_project(Project(
        slug="plain", name="p", base_url="https://demo.test", allowed_domains=["demo.test"]))
    broken = ProjectStore("broken", tmp_path)
    _scheduled(tmp_path, "broken")
    data = json.loads(broken.paths.config.read_text(encoding="utf-8"))
    data["schedule"]["timezone"] = "America/New_York"
    broken.paths.config.write_text(json.dumps(data), encoding="utf-8")
    items, invalid = scheduled_projects(tmp_path)
    assert [i.project for i in items] == ["daily"] and invalid == ["broken"]
    assert items[0].since.tzinfo is not None


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import autotester.ui.routes_runs as routes_runs
    import autotester.ui.run_execution as run_execution
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setattr(routes_runs, "principal_for_email", lambda email: Principal(
        user_id=1, email=email, permissions=frozenset(all_permissions())))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="t",
                        steps=[Step(order=0, action=Action.CLICK, target="#go")]))

    class Judge:
        trace = None

        def __init__(self, project: Project) -> None:
            self.project = project

        def available(self) -> bool:
            return True

    def fake_run_and_grade(case_, session, judge, run_id, store_):
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", fake_run_and_grade)
    plan = ParallelPlan(1, 1, 1, "config", 99999.0, 8)
    seams = RunSeams(judge_factory=Judge, planner=lambda *a, **kw: plan)
    monkeypatch.setattr(routes_runs, "_seams", lambda *a, **kw: seams)
    return store, routes_runs


def _entry(trigger: str, slot_key: str | None = None, requested_by: str | None = "u1"):
    return QueueEntry(id="run-q1", project="demo", trigger=trigger,  # type: ignore[arg-type]
                      requested_by=requested_by, slot_key=slot_key)


def test_a_scheduler_entry_becomes_a_run_stamped_schedule_with_its_slot(world) -> None:
    store, routes_runs = world
    grant_live_case_approval(store)
    routes_runs._run_queued(_entry("schedule", "demo:fixed:2026-10-08T09:00Z"))
    run = store.load_run("run-q1")
    assert run is not None and run.trigger is Trigger.SCHEDULE
    assert (run.requested_by, run.slot_key) == ("u1", "demo:fixed:2026-10-08T09:00Z")


def test_a_button_entry_is_still_stamped_manual(world) -> None:
    store, routes_runs = world
    grant_live_case_approval(store)
    routes_runs._run_queued(_entry("button"))
    run = store.load_run("run-q1")
    assert run is not None and run.trigger is Trigger.MANUAL and run.slot_key is None


def test_a_scheduled_entry_without_an_approval_is_refused_by_the_launcher(world, tmp_path) -> None:
    from autotester.ui.run_queue import RunRefused

    store, routes_runs = world
    with pytest.raises(RunRefused):
        routes_runs._run_queued(_entry("schedule", "demo:fixed:2026-10-08T09:00Z"))
    assert not store.paths.runs_dir.exists() and store.list_approvals() == []


# --- review findings (senior-software-engineer, 2026-10-12) ---------------------------------
def test_an_edit_after_a_missed_slot_does_not_hide_it(tmp_path: Path) -> None:
    """`since` is the project file's mtime; an unrelated edit after the outage began must not
    move the lower bound past a slot the scheduler never saw (never silently dropped)."""
    from autotester.stages.schedule_store import write_heartbeat

    _scheduled(tmp_path, saved=utc(2026, 10, 8, 12))            # edited after the 09:00 slot
    write_heartbeat(schedule_paths(tmp_path).heartbeat, utc(2026, 10, 8, 8, 0))
    queue, _ = _queue()
    report = _tick(tmp_path, queue, utc(2026, 10, 8, 18))       # outside grace
    assert [r.outcome for r in report.records] == [SlotOutcome.MISSED]
    assert queue.snapshot() == []


def test_a_tick_for_one_project_does_not_refresh_the_global_heartbeat(tmp_path: Path) -> None:
    _scheduled(tmp_path, "alpha")
    _scheduled(tmp_path, "beta")
    queue, _ = _queue()
    _tick(tmp_path, queue, only="beta")
    assert not schedule_paths(tmp_path).heartbeat.exists()
    _tick(tmp_path, queue)
    assert schedule_paths(tmp_path).heartbeat.exists()


def test_a_scheduled_run_refused_at_start_leaves_a_line_on_stderr(
    world, capsys: pytest.CaptureFixture[str],
) -> None:
    from autotester.ui.run_queue import RunRefused

    _store, routes_runs = world
    queue = routes_runs.tick_queue()
    with pytest.raises(RunRefused):
        routes_runs.tick_runner(_entry("schedule", "demo:fixed:2026-10-08T09:00Z"))
    assert "demo:fixed:2026-10-08T09:00Z" in capsys.readouterr().err and queue is not None

"""TA8: a schedule fires once, through the same queue and launcher as the button, and feeds the
same bug. The injected clock is the only time source. The schedule is set on the project file
directly for the tick rows; the save route and the schedule card (T-200) are driven through the app
in TS1 and TS5. The tick, the queue, the gate and the launcher are the repo's own."""

from __future__ import annotations

from datetime import datetime

from auth_harness import user_id
from rig import HTML, SLUG, World, email, press
from schedule_support import BEFORE, SLOT, schedule
from team_run_fakes import runnable_project

from autotester.auth.access import set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.enums import Trigger
from autotester.schema.run_queue import QueueEntry, QueueStatus
from autotester.schema.team_enums import SlotOutcome
from autotester.stages.bug_run import process_run
from autotester.stages.schedule_wiring import tick_all
from autotester.ui.run_queue import get_queue


def tick(world: World, now: datetime, **kw):
    return tick_all(now, root=world.root, queue=get_queue(), **kw)


def test_nothing_before_the_slot_one_enqueue_at_it_and_a_second_tick_adds_nothing(
        world: World) -> None:
    schedule(world)
    assert tick(world, BEFORE).records == []
    assert world.counters.graded == 0
    first = tick(world, SLOT)
    assert [r.outcome for r in first.records] == [SlotOutcome.ENQUEUED]
    assert tick(world, SLOT.replace(second=40)).records == []
    other_instance = tick(world, SLOT.replace(second=50))            # a second scheduler instance
    assert other_instance.records == []
    entries = [e for e in get_queue().snapshot(SLUG) if e.trigger == "schedule"]
    assert len(entries) == 1 and entries[0].requested_by == "subadmin@team.test"
    run = world.store().load_run(entries[0].id)
    assert run is not None and run.trigger is Trigger.SCHEDULE
    assert world.counters.graded == 1                                # the same launcher ran it


def test_a_scheduled_failure_and_a_button_failure_share_one_bug(world: World) -> None:
    schedule(world)
    process_run(world.store(), world.bugs(), press(world, "dev"))
    tick(world, SLOT)
    [entry] = [e for e in get_queue().snapshot(SLUG) if e.trigger == "schedule"]
    process_run(world.store(), world.bugs(), entry.id)
    [bug] = world.bugs().bugs().values()
    assert bug.count == 2 and bug.evidence_run_id == entry.id


def test_a_project_without_a_credential_pair_is_blocked_with_zero_requests(world: World) -> None:
    runnable_project(world.root, "nocred")
    set_relation("nocred", user_id(email("subadmin")), ProjectRelation.ASSIGNED, True)
    schedule(world, "nocred")
    report = tick(world, SLOT, only="nocred")
    assert [r.outcome for r in report.records] == [SlotOutcome.BLOCKED_NO_CREDENTIALS]
    assert world.counters.graded == 0 and world.counters.sessions == 0
    assert get_queue().snapshot("nocred") == []
    assert world.egress.blocked == []


def test_a_busy_project_is_skipped_overlap(world: World) -> None:
    schedule(world)
    busy = QueueEntry(id="run-busy", project=SLUG, status=QueueStatus.RUNNING)
    report = tick(world, SLOT, persisted=lambda: [busy])
    assert [r.outcome for r in report.records] == [SlotOutcome.SKIPPED_OVERLAP]
    assert world.counters.graded == 0


def test_ts1_subadmin_saves_a_schedule_and_tester_cannot(world: World) -> None:
    body = {"mode": "fixed", "fixed_at": "09:00", "timezone": "UTC"}
    assert world.users["tester"].post(f"/projects/{SLUG}/schedule", data=body).status_code in (
        403, 404)
    assert world.users["subadmin"].post(f"/projects/{SLUG}/schedule", data=body).status_code == 303
    saved = world.store().load_project()
    assert saved is not None and saved.schedule is not None
    assert saved.schedule.owner == email("subadmin")


def test_ts5_the_schedule_card_shows_the_slot_and_next_fire_times(world: World) -> None:
    schedule(world)
    resp = world.users["subadmin"].get(f"/projects/{SLUG}/schedule", headers=HTML)
    assert resp.status_code == 200
    assert "Next run" in resp.text and "every day at 09:00 UTC" in resp.text

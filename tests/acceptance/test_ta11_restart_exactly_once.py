"""TA11: a restart keeps the world and repeats nothing. A "restart" here is what one does to the
objects: new queue over the same persisted file, new HTTP clients (fresh cookie jars, new sign-in),
new store objects over the same data root. Nothing is carried in memory across it."""

from __future__ import annotations

import hashlib
from pathlib import Path

from auth_harness import login
from rig import SLUG, World, email, press, with_origin
from schedule_support import SLOT, schedule
from team_run_fakes import listing

from autotester.stages.bug_run import process_run
from autotester.stages.schedule_wiring import tick_all
from autotester.ui import run_queue

OUTBOX_FILES = "*.eml"
HEARTBEAT = ".work/team/schedule/heartbeat.json"


def persisted(world: World) -> Path:
    return world.root / ".work" / "run_queue.json"


def boot_queue(world: World, monkeypatch) -> run_queue.RunQueue:
    """The server's queue: file-backed, recovered on start, jobs run inline (no threads)."""
    queue = run_queue.RunQueue(spawn=lambda job: job(), runner=run_queue._registered_runner,
                               path=lambda: persisted(world))
    queue.recover()
    monkeypatch.setattr("autotester.ui.run_queue._QUEUE", queue)
    return queue


def restart(world: World, monkeypatch) -> None:
    boot_queue(world, monkeypatch)
    world.users = {role: with_origin(login(email(role))) for role in world.users}


def dump(world: World) -> dict:
    runs = sorted(p.name for p in world.store().paths.runs_dir.glob("run-*"))
    files = {k: v for k, v in listing(world.root).items() if k != HEARTBEAT}   # liveness, not state
    return {"files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}, "runs": runs,
            "bugs": {k: (b.count, b.status.value) for k, b in world.bugs().bugs().items()},
            "outbox": sorted(p.name for p in world.outbox.glob(OUTBOX_FILES))}


def test_the_world_survives_a_restart_and_nothing_is_repeated(world: World, monkeypatch) -> None:
    boot_queue(world, monkeypatch)
    schedule(world)
    run_id = press(world, "dev")
    process_run(world.store(), world.bugs(), run_id)
    tick_all(SLOT, root=world.root, queue=run_queue.get_queue())
    scheduled = [e for e in run_queue.get_queue().snapshot(SLUG) if e.trigger == "schedule"]
    assert len(scheduled) == 1
    process_run(world.store(), world.bugs(), scheduled[0].id)
    before, graded = dump(world), world.counters.graded

    restart(world, monkeypatch)
    assert dump(world) == before                                        # the same world
    assert tick_all(SLOT.replace(second=45), root=world.root,
                    queue=run_queue.get_queue()).records == []           # same slot: no new run
    for run in (run_id, scheduled[0].id):
        assert process_run(world.store(), world.bugs(), run).applied == 0   # no second bug row
    assert dump(world) == before and world.counters.graded == graded
    assert world.users["dev"].get(f"/projects/{SLUG}/runs/{run_id}").status_code == 200


def test_a_queued_run_survives_a_restart_as_resumed_or_interrupted_never_lost(
        world: World, monkeypatch) -> None:
    held: list = []
    first = run_queue.RunQueue(spawn=held.append, runner=run_queue._registered_runner,
                               path=lambda: persisted(world))
    monkeypatch.setattr("autotester.ui.run_queue._QUEUE", first)
    queued = press(world, "dev")
    assert held and not world.counters.graded
    restarted = run_queue.RunQueue(spawn=held.append, runner=run_queue._registered_runner,
                                   path=lambda: persisted(world))
    restarted.recover()
    monkeypatch.setattr("autotester.ui.run_queue._QUEUE", restarted)
    entries = {e.id: e for e in restarted.snapshot(SLUG)}
    assert queued in entries and entries[queued].status.value in {"queued", "running",
                                                                  "interrupted"}

"""TS2 (claim half): a slot fires exactly once, across two OS processes and across a crash.

The claim is the thing under test, so the fake queue is non-idempotent in the concurrency test:
one entry can only mean one claim won. The crash tests use the idempotent queue HO23 promises.
"""

from __future__ import annotations

import ast
import dataclasses
import multiprocessing as mp
import os
from pathlib import Path

import pytest
from schedule_fakes import daily, make_deps, utc

from autotester.schema.schedule import ScheduleMode, SlotClaim, SlotOutcome
from autotester.stages import schedule_store, schedule_time, scheduler
from autotester.stages.schedule_store import claim, list_claims, read_records
from autotester.stages.scheduler import tick_project

NOW = utc(2026, 10, 8, 9, 0, 20)
SINCE = utc(2026, 10, 7, 12)
KEY = "p:fixed:2026-10-08T09:00Z"


def _tick_in_child(barrier, base: str) -> None:
    deps, _ = make_deps(Path(base), "p", idempotent=False)
    barrier.wait(timeout=60)
    tick_project("p", daily(), NOW, deps, since=SINCE)


def test_claim_is_won_by_exactly_one_caller_and_the_name_is_path_safe(tmp_path: Path) -> None:
    """Two schedulers see the same due slot (HO23): only the first claim wins."""
    body = SlotClaim(slot_key=KEY, mode=ScheduleMode.FIXED, instant=utc(2026, 10, 8, 9),
                     claimed_at=NOW, intended=SlotOutcome.ENQUEUED)
    assert claim(tmp_path, KEY, body) is True
    assert claim(tmp_path, KEY, body) is False
    names = [p.name for p in tmp_path.iterdir()]
    assert len(names) == 1
    assert ":" not in names[0]  # a colon is illegal in a Windows file name
    assert list(list_claims(tmp_path)) == [KEY]


def test_two_processes_ticking_one_slot_enqueue_exactly_one_run(tmp_path: Path) -> None:
    """A tick timer and a hand-run `schedule tick` fire in the same second (spawn = Windows too)."""
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(2)
    procs = [ctx.Process(target=_tick_in_child, args=(barrier, str(tmp_path))) for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=120)
        assert p.exitcode == 0  # the loser exits 0 and records nothing
    _, q = make_deps(tmp_path, "p")
    assert len(q) == 1
    assert [r.slot_key for r in read_records(tmp_path / "records.jsonl")] == [KEY]


def test_tick_that_dies_between_claim_and_enqueue_is_redriven_to_one_entry(
    tmp_path: Path,
) -> None:
    """The process is killed after writing the claim but before the queue entry exists."""
    deps, q = make_deps(tmp_path, "p", idempotent=True)
    real = deps.enqueue

    def die(_slot: scheduler.Slot) -> str:
        raise SystemExit(1)

    with pytest.raises(SystemExit):
        tick_project("p", daily(), NOW, _with(deps, die), since=SINCE)
    assert len(q) == 0
    assert list(list_claims(deps.claim_dir)) == [KEY]
    assert read_records(deps.records_path) == []

    # a tick right after the crash must not re-drive a claim that may still be in flight
    assert tick_project("p", daily(), utc(2026, 10, 8, 9, 0, 50), deps, since=SINCE) == []
    assert len(q) == 0

    later = utc(2026, 10, 8, 9, 5)  # past the re-drive age
    out = tick_project("p", daily(), later, _with(deps, real), since=SINCE)
    assert len(q) == 1
    assert [r.slot_key for r in out] == [KEY]
    assert tick_project("p", daily(), utc(2026, 10, 8, 9, 6), deps, since=SINCE) == []
    assert len(q) == 1


def test_tick_that_dies_after_the_entry_exists_does_not_enqueue_or_skip_twice(
    tmp_path: Path,
) -> None:
    """Killed after the queue accepted the entry but before the slot record was written: the
    re-drive must find its own entry, not mistake it for a busy project (TS4) or add a second."""
    deps, q = make_deps(tmp_path, "p", idempotent=True)
    real = deps.enqueue

    def enqueue_then_die(slot: scheduler.Slot) -> str:
        real(slot)
        raise SystemExit(1)

    with pytest.raises(SystemExit):
        tick_project("p", daily(), NOW, _with(deps, enqueue_then_die), since=SINCE)
    assert len(q) == 1
    out = tick_project("p", daily(), utc(2026, 10, 8, 9, 5), deps, since=SINCE)
    assert len(q) == 1
    assert [r.outcome.value for r in out] == ["enqueued"]  # the label the claim decided
    assert out[0].entry_id == q.entries()[0]["id"]


def test_new_modules_use_no_posix_only_primitive() -> None:
    """R65: the scheduler runs on Windows and Ubuntu, so no fcntl / flock / pwd / fork."""
    banned = {"fcntl", "pwd", "flock", "fork", "forkpty"}
    for mod in (schedule_store, schedule_time, scheduler):
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.module}
        assert not (banned & (names | attrs | imported)), mod.__name__


def _with(deps: scheduler.TickDeps, enqueue) -> scheduler.TickDeps:
    return dataclasses.replace(deps, enqueue=enqueue)


def test_a_claim_file_torn_before_its_body_was_written_is_still_driven_to_one_entry(
    tmp_path: Path,
) -> None:
    """The process died between creating the claim file and writing into it (empty file)."""
    deps, q = make_deps(tmp_path, "p", idempotent=True)
    deps.claim_dir.mkdir(parents=True)
    path = schedule_store.claim_path(deps.claim_dir, KEY)
    path.write_bytes(b"")
    stamp = NOW.timestamp()
    os.utime(path, (stamp, stamp))
    assert list(list_claims(deps.claim_dir).values()) == [None]
    assert tick_project("p", daily(), NOW, deps, since=SINCE) == []  # too young to re-drive
    out = tick_project("p", daily(), utc(2026, 10, 8, 9, 5), deps, since=SINCE)
    assert [r.slot_key for r in out] == [KEY]
    assert len(q) == 1

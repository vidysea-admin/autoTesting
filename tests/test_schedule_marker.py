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

from autotester.schema.schedule import ScheduleMode, SlotClaim, SlotOutcome, SlotRecord
from autotester.stages import schedule_store, schedule_time, scheduler
from autotester.stages.schedule_store import (
    append_record,
    claim,
    list_claims,
    project_records_path,
    purge_project,
    read_records,
)
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


# --- purge of a deleted project (TS1 clause HO24 leaves open) ------------------------------------
def _slot(project: str) -> tuple[str, SlotClaim, SlotRecord]:
    key = f"{project}:fixed:2026-10-08T09:00Z"
    when = utc(2026, 10, 8, 9)
    return (key, SlotClaim(slot_key=key, mode=ScheduleMode.FIXED, instant=when, claimed_at=NOW,
                           intended=SlotOutcome.ENQUEUED),
            SlotRecord(slot_key=key, project=project, mode=ScheduleMode.FIXED, instant=when,
                       recorded_at=NOW, outcome=SlotOutcome.ENQUEUED))


def _seed(base: Path, project: str) -> Path:
    key, body, rec = _slot(project)
    path = project_records_path(base / "records", project)
    assert claim(base / "claims", key, body) and append_record(path, rec)
    return path


def test_purge_removes_only_that_projects_markers_and_record_file_and_is_idempotent(
    tmp_path: Path,
) -> None:
    a, pp = _seed(tmp_path, "p"), _seed(tmp_path, "pp")  # "pp" merely starts like "p"
    purge_project(tmp_path / "claims", a, "p")
    assert list(list_claims(tmp_path / "claims")) == ["pp:fixed:2026-10-08T09:00Z"]
    assert not a.exists() and len(read_records(pp)) == 1
    purge_project(tmp_path / "claims", a, "p")  # nothing left: still fine
    assert len(read_records(pp)) == 1


def test_purge_refuses_a_records_file_shared_with_another_project_and_changes_nothing(
    tmp_path: Path,
) -> None:
    """The old layout (one file for every project) cannot be purged without rewriting other
    projects' lines, which loses their concurrent appends: refuse instead of risking it."""
    shared = _seed(tmp_path, "p")
    append_record(shared, _slot("q")[2])
    before = shared.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="shared"):
        purge_project(tmp_path / "claims", shared, "p")
    assert shared.read_text(encoding="utf-8") == before
    assert list(list_claims(tmp_path / "claims")) == ["p:fixed:2026-10-08T09:00Z"]


def test_a_purge_that_fails_part_way_leaves_markers_and_records_together_and_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _seed(tmp_path, "p")
    key2, body2, _ = _slot("p")
    key2 = "p:fixed:2026-10-09T09:00Z"
    claim(tmp_path / "claims", key2, body2.model_copy(update={"slot_key": key2}))
    before = sorted(str(f.relative_to(tmp_path)) for f in tmp_path.rglob("*") if f.is_file())
    real, calls = os.replace, []

    def flaky(src, dst):
        calls.append(src)
        if len(calls) == 2:
            raise PermissionError("in use by another process")
        return real(src, dst)

    monkeypatch.setattr(schedule_store.os, "replace", flaky)
    with pytest.raises(PermissionError):
        purge_project(tmp_path / "claims", path, "p")
    monkeypatch.undo()
    after = sorted(str(f.relative_to(tmp_path)) for f in tmp_path.rglob("*") if f.is_file())
    assert after == before and len(read_records(path)) == 1  # neither half moved, nothing leaked
    assert not [d for d in tmp_path.iterdir() if d.name.startswith(".purge")]
    purge_project(tmp_path / "claims", path, "p")  # and a retry then succeeds
    assert list_claims(tmp_path / "claims") == {} and not path.exists()


def _append_for_b(base: str, count: int, out: str) -> None:
    path = project_records_path(Path(base) / "records", "b")
    ok = 0
    for n in range(count):
        key = f"b:custom:2026-10-{8 + n // 1440:02d}T{n // 60 % 24:02d}:{n % 60:02d}Z"
        rec = _slot("b")[2].model_copy(update={"slot_key": key})
        ok += bool(append_record(path, rec))
    Path(out).write_text(str(ok), encoding="utf-8")


def test_every_acknowledged_append_by_a_neighbour_survives_purges_of_another_project(
    tmp_path: Path,
) -> None:
    """B ticks (appends) in another OS process while A is purged again and again."""
    ctx = mp.get_context("spawn")
    count, out = 150, tmp_path / "acked.txt"
    child = ctx.Process(target=_append_for_b, args=(str(tmp_path), count, str(out)))
    child.start()
    purges = 0
    while child.is_alive() or purges == 0:
        a = _seed(tmp_path, "a")
        purge_project(tmp_path / "claims", a, "a")
        purges += 1
    child.join(timeout=120)
    assert child.exitcode == 0
    b = project_records_path(tmp_path / "records", "b")
    assert int(out.read_text(encoding="utf-8")) == count == len(read_records(b))
    assert not list((tmp_path / "records").glob(".*tmp")) and purges >= 1

"""T-199b: the four checker findings of the T-199a core that a run directory makes reachable.

P3 one read per batch, P4 a bad event file is contained and named, P8 the event time is bounded and
the fold is deterministic when one fact is written with two times, P9 `bug_key` is clean and a
store-only replay leaves the count alone. Contract: qa/contracts/team-bug-loop.md TB2, TB6.
"""

from __future__ import annotations

import itertools
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
from bug_loop_fixture import KEY, T0, at, event
from pydantic import ValidationError

import autotester.store.bug_store as module
from autotester.schema.tracked_bug import BugEvent, BugStatus, EventKind
from autotester.stages.bug_loop import Effect, Refusal, fold
from autotester.store.bug_store import BugStore

K = EventKind
S = BugStatus
NOW = T0 + timedelta(days=1)


def _store(root: Path, **kw) -> BugStore:
    return BugStore(root, clock=lambda: NOW, **kw)


def _counting(monkeypatch) -> dict[str, int]:
    calls, real = {"n": 0}, module.read_json

    def counted(path, model_cls):
        calls["n"] += 1
        return real(path, model_cls)

    monkeypatch.setattr(module, "read_json", counted)
    return calls


# -- P3: one read of the store per batch --------------------------------------------------------

def test_p3_a_batch_of_new_events_reads_each_stored_file_exactly_once(
        tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    store.apply_all([event(K.FAIL, n) for n in range(1, 31)])
    calls = _counting(monkeypatch)
    store.apply_all([event(K.FAIL, n) for n in range(31, 41)])
    assert calls["n"] == 30                       # the 30 stored files, once; not 30 + 10 again


def test_p3_a_snapshot_taken_by_the_caller_is_reused_not_read_again(
        tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    store.apply_all([event(K.FAIL, n) for n in range(1, 11)])
    calls = _counting(monkeypatch)
    snap = store.snapshot()
    store.apply_all([event(K.FAIL, 11)], snapshot=snap)
    assert calls["n"] == 10


# -- P4: a bad event file is contained, named, and loses no valid event -------------------------

@pytest.mark.parametrize(
    "content", ["", '{"schema_version": 1, "event_id": "bev_', "[]", "\x00\x01"])
def test_p4_a_corrupt_event_file_does_not_stop_the_store_and_is_named(
        tmp_path: Path, content: str) -> None:
    store = _store(tmp_path)
    store.apply_all([event(K.FAIL, 1), event(K.FAIL, 2)])
    (store.dir / "bev_torn.json").write_text(content, encoding="utf-8")
    assert store.get(KEY).count == 2 and len(store.events()) == 2
    assert [b.name for b in store.snapshot().bad] == ["bev_torn.json"]
    assert store.apply(event(K.FAIL, 3)).effect is Effect.APPLIED
    assert store.get(KEY).count == 3


def test_p4_a_file_whose_name_is_not_its_event_id_is_bad_not_trusted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.apply(event(K.FAIL, 1))
    real = next(store.dir.glob("bev_*.json"))
    (store.dir / "bev_planted.json").write_bytes(real.read_bytes())
    snap = store.snapshot()
    assert [b.name for b in snap.bad] == ["bev_planted.json"] and len(snap.events) == 1


def test_p4_the_same_event_applied_again_repairs_its_own_zero_length_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.apply(event(K.FAIL, 1))
    target = next(store.dir.glob("bev_*.json"))
    target.write_bytes(b"")                       # a power cut after the rename
    assert store.snapshot().bad[0].name == target.name and store.bugs() == {}
    assert store.apply(event(K.FAIL, 1)).effect is Effect.APPLIED
    assert store.snapshot().bad == [] and store.get(KEY).count == 1


def test_p4_a_persistent_permission_denial_still_raises_it_is_not_corruption(
        tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    store.apply(event(K.FAIL, 1))
    monkeypatch.setattr(module, "read_json", lambda *a: (_ for _ in ()).throw(PermissionError(13)))
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    with pytest.raises(PermissionError):
        store.bugs()


# -- P8: the event time is bounded; one fact written with two times folds the same --------------

def test_p8_a_future_dated_fail_is_refused_and_cannot_reopen_a_closed_bug(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.apply_all([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)])
    assert store.get(KEY).status is S.FIXED
    far = event(K.FAIL, 9, minutes=60 * 24 * 365 * 70)           # year ~2096
    got = store.apply(far)
    assert (got.effect, got.reason) == (Effect.REFUSED, Refusal.IMPLAUSIBLE_TIME)
    assert store.get(KEY).status is S.FIXED and len(store.events()) == 3


def test_p8_the_bounds_are_a_few_minutes_ahead_and_the_product_epoch(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ok = event(K.FAIL, 1, minutes=int((NOW - T0).total_seconds() / 60) + 4)
    late = event(K.FAIL, 2, minutes=int((NOW - T0).total_seconds() / 60) + 30)
    old = event(K.FAIL, 3, minutes=-60 * 24 * 365 * 7)
    got = store.apply_all([ok, late, old])
    assert [g.effect for g in got] == [Effect.APPLIED, Effect.REFUSED, Effect.REFUSED]
    assert {g.reason for g in got[1:]} == {Refusal.IMPLAUSIBLE_TIME}


def test_p8_a_refused_time_writes_nothing_and_is_accepted_once_its_time_has_come(
        tmp_path: Path) -> None:
    future = event(K.FAIL, 1, minutes=int((NOW - T0).total_seconds() / 60) + 600)
    early = BugStore(tmp_path, clock=lambda: NOW)
    assert early.apply(future).effect is Effect.REFUSED and list(early.dir.glob("*")) == []
    later = BugStore(tmp_path, clock=lambda: NOW + timedelta(days=2))
    assert later.apply(future).effect is Effect.APPLIED


def _two_times() -> list[BugEvent]:
    one = event(K.FAIL, 1, ref="run1/x", minutes=5)
    return [one, event(K.FAIL, 1, ref="run1/x", minutes=9)]       # same id, two times


def test_p8_one_fact_written_with_two_times_keeps_both_files_and_folds_once(
        tmp_path: Path) -> None:
    one, two = _two_times()
    assert one.event_id == two.event_id
    store = _store(tmp_path)
    store._write(one)
    store._write(two)                             # what a racing second process does
    assert len(store.events()) == 2 and store.get(KEY).count == 1


@pytest.mark.parametrize("order", list(itertools.permutations(range(3))))
def test_p8_the_fold_does_not_depend_on_which_of_the_racing_copies_landed_first(
        tmp_path: Path, order) -> None:
    a, b = _two_times()
    c = event(K.PASS, 2, minutes=20)
    copies = [a, b, c]
    reference = fold(copies)
    store = _store(tmp_path)
    for i in order:
        store._write(copies[i])
    assert store.bugs() == reference
    assert reference[KEY].first_seen == at(5) and reference[KEY].pass_streak == 1


def _race_worker(args: tuple[str, int]) -> int:
    root, minutes = args
    BugStore(Path(root), clock=lambda: NOW).apply(event(K.FAIL, 1, ref="run1/x", minutes=minutes))
    return minutes


def test_p8_processes_racing_one_fact_with_different_times_converge(tmp_path: Path) -> None:
    times = [3, 4, 5, 6, 7, 8]
    with ProcessPoolExecutor(max_workers=6) as pool:
        assert sorted(pool.map(_race_worker, [(str(tmp_path), m) for m in times])) == times
    store = _store(tmp_path)
    kept = store.events()                         # 1..6 copies, depending on who really raced
    assert 1 <= len(kept) <= 6 and store.snapshot().bad == []
    assert store.get(KEY).count == 1 and store.get(KEY).first_seen == min(e.at for e in kept)


# -- P9: bug_key is clean; a store-only replay leaves the count alone ---------------------------

@pytest.mark.parametrize("bad", ["", "bug_ab\ncd", "bug_x\x00y", "k" * 201, "bug_\x7f"])
def test_p9_a_bug_key_with_a_control_character_or_over_length_is_refused(bad: str) -> None:
    with pytest.raises(ValidationError):
        BugEvent(bug_key=bad, kind=K.PASS, ref="r", at=at(1), actor="system:bug-loop", run_id="r")


def test_p9_replaying_a_run_through_the_store_alone_leaves_count_and_files_unchanged(
        tmp_path: Path) -> None:
    store = _store(tmp_path)
    events = [event(K.FAIL, 1), event(K.FAIL, 2), event(K.PASS, 3)]
    store.apply_all(events)
    before = {p.name: p.read_bytes() for p in sorted(store.dir.glob("*.json"))}
    for _ in range(3):
        got = store.apply_all(events)
        assert {g.effect for g in got} == {Effect.DUPLICATE}
    assert store.get(KEY).count == 2
    assert {p.name: p.read_bytes() for p in sorted(store.dir.glob("*.json"))} == before

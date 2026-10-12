"""T-199a: racing writers on the bug event store (TB6) -- real threads and real processes.

Nothing may be lost, torn or raised, and the state is judged by the files and the fold.
"""

from __future__ import annotations

import threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from bug_loop_fixture import KEY, event

from autotester.schema.tracked_bug import BugEvent, EventKind
from autotester.stages.bug_loop import fold
from autotester.store.bug_store import BugStore

K = EventKind


def _fails(count: int) -> list[BugEvent]:
    return [event(K.FAIL, n) for n in range(1, count + 1)]


def _unique(worker: int, count: int) -> list[BugEvent]:
    return [event(K.FAIL, 1000 * (worker + 1) + n) for n in range(count)]


def test_concurrent_threads_lose_no_event_and_never_corrupt_a_file(tmp_path: Path) -> None:
    errors: list[BaseException] = []

    def work(worker: int) -> None:
        try:
            BugStore(tmp_path).apply_all([*_fails(5), *_unique(worker, 25)])
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    store = BugStore(tmp_path)
    assert len(store.events()) == 5 + 6 * 25 and store.bugs()[KEY].count == 5 + 6 * 25
    assert fold(store.events())[KEY] == store.bugs()[KEY]


def _process_worker(args: tuple[str, int]) -> int:
    root, worker = args
    BugStore(Path(root)).apply_all([*_fails(5), *_unique(worker, 40)])
    return worker


def test_concurrent_processes_lose_no_event_and_never_corrupt_a_file(tmp_path: Path) -> None:
    with ProcessPoolExecutor(max_workers=6) as pool:
        done = list(pool.map(_process_worker, [(str(tmp_path), i) for i in range(6)]))
    assert sorted(done) == list(range(6))
    store = BugStore(tmp_path)
    assert len(store.events()) == 5 + 6 * 40            # every event survived, every file parses
    assert store.bugs()[KEY].count == 5 + 6 * 40


def _same_events_worker(args: tuple[str, int]) -> int:
    root, _ = args
    store = BugStore(Path(root))
    store.apply_all(_fails(30))
    store.bugs()
    return 0


def test_processes_racing_on_the_same_events_never_raise(tmp_path: Path) -> None:
    with ProcessPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(_same_events_worker, [(str(tmp_path), i) for i in range(8)])) == 0
    assert BugStore(tmp_path).bugs()[KEY].count == 30

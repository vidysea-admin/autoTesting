"""T-199a: the append-only bug store and the Issue adapter (TB1, TB5, TB6).

Contract: qa/contracts/team-bug-loop.md. Racing writers are real threads and real processes; the
file is judged by its bytes and by the fold, never by what a writer thought it saw.
"""

from __future__ import annotations

import re
import threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest
from bug_loop_fixture import KEY, event, seed

from autotester.schema.issue import Issue
from autotester.schema.tracked_bug import BugEvent, BugStatus, EventKind
from autotester.stages.bug_loop import Effect, Refusal, fold
from autotester.stages.issues import issue_to_bug_event
from autotester.store.bug_store import BugStore

K = EventKind


def _fails(count: int) -> list[BugEvent]:
    return [event(K.FAIL, n) for n in range(1, count + 1)]


def _bytes(store: BugStore) -> bytes:
    return store.path.read_bytes() if store.path.exists() else b""


def test_an_empty_or_missing_directory_is_an_empty_store(tmp_path: Path) -> None:
    store = BugStore(tmp_path / "does" / "not" / "exist")
    assert store.bugs() == {} and store.get(KEY) is None and store.history(KEY) == []


def test_tb1_three_runs_failing_the_same_criterion_are_one_bug(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply_all(_fails(3))
    bugs = store.bugs()
    assert list(bugs) == [KEY] and bugs[KEY].count == 3 and bugs[KEY].status is BugStatus.OPEN


def test_tb1_two_failing_criteria_on_one_case_are_two_bugs(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    second = seed(crit="C2")
    store.apply_all([event(K.FAIL, 1), event(K.FAIL, 2, seed_obj=second)])
    assert len(store.bugs()) == 2


def test_tb6_applying_an_event_twice_changes_nothing_and_writes_nothing(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    fail = event(K.FAIL, 1)
    assert store.apply(fail).effect is Effect.APPLIED
    before = _bytes(store)
    again = store.apply(fail)
    assert again.effect is Effect.DUPLICATE and _bytes(store) == before
    assert store.apply(event(K.PASS, 1, ref=fail.ref)).effect is Effect.DUPLICATE
    assert _bytes(store) == before


def test_tb6_processing_a_whole_run_twice_gives_byte_identical_stores(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    batch = [*_fails(2), event(K.PASS, 3), event(K.INCONCLUSIVE, 4),
             event(K.ASSIGN, 5, assignee="Priya")]
    first = store.apply_all(batch)
    snapshot = _bytes(store)
    second = store.apply_all(batch)
    assert _bytes(store) == snapshot
    applied, dup, same = Effect.APPLIED, Effect.DUPLICATE, Effect.UNCHANGED
    assert [r.effect for r in first] == [applied] * 3 + [same, applied]
    assert [r.effect for r in second] == [dup] * 3 + [same, dup]


def test_tb6_a_crash_after_bug_one_of_two_converges_on_retry(tmp_path: Path) -> None:
    other = seed(crit="C2")
    run = [event(K.FAIL, 1), event(K.FAIL, 1, seed_obj=other)]
    clean = BugStore(tmp_path / "clean")
    clean.apply_all(run)
    crashed = BugStore(tmp_path / "crashed")
    crashed.apply_all(run[:1])           # the process died after bug 1
    crashed.apply_all(run)               # the whole run is retried
    assert _bytes(crashed) == _bytes(clean)
    assert sorted(b.count for b in crashed.bugs().values()) == [1, 1]


def test_history_is_never_rewritten_only_appended(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply_all(_fails(2))
    prefix = _bytes(store)
    store.apply_all([event(K.PASS, 3), event(K.PASS, 4), event(K.FAIL, 5), event(K.ASSIGN, 6)])
    assert _bytes(store).startswith(prefix)
    assert len(store.history(KEY)) == 6 and store.get(KEY).status is BugStatus.REOPENED


def test_a_refused_event_writes_nothing(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    result = store.apply(event(K.PASS, 1))
    assert (result.effect, result.reason) == (Effect.REFUSED, Refusal.NO_BUG)
    assert not store.path.exists()


def test_two_stores_in_two_directories_do_not_see_each_other(tmp_path: Path) -> None:
    BugStore(tmp_path / "a").apply(event(K.FAIL, 1))
    assert BugStore(tmp_path / "b").bugs() == {}


def test_a_torn_tail_line_is_loud_not_silent(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply(event(K.FAIL, 1))
    with store.path.open("ab") as handle:
        handle.write(b'{"schema_version": 1, "event_id": "bev_')
    with pytest.raises(ValueError, match=r"bug_events\.jsonl:2"):
        store.bugs()


def test_close_passes_below_one_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        BugStore(tmp_path, close_passes=0)
    store = BugStore(tmp_path, close_passes=3)
    store.apply_all([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)])
    assert store.get(KEY).status is BugStatus.OPEN


def test_concurrent_threads_never_corrupt_the_file_or_double_count(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    shared = _fails(10)
    errors: list[BaseException] = []

    def work(offset: int) -> None:
        try:
            for _ in range(2):
                BugStore(tmp_path).apply_all([*shared, event(K.FAIL, 100 + offset)])
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert store.bugs()[KEY].count == 10 + 6
    assert all(line.startswith("{") and line.endswith("}") for line in
               store.path.read_text(encoding="utf-8").splitlines())
    assert fold(store.events())[KEY] == store.bugs()[KEY]


def _process_worker(args: tuple[str, int]) -> int:
    root, offset = args
    BugStore(Path(root)).apply_all([*_fails(8), event(K.FAIL, 200 + offset)])
    return offset


def test_concurrent_processes_never_corrupt_the_file_or_double_count(tmp_path: Path) -> None:
    with ProcessPoolExecutor(max_workers=3) as pool:
        done = list(pool.map(_process_worker, [(str(tmp_path), i) for i in range(3)]))
    assert sorted(done) == [0, 1, 2]
    store = BugStore(tmp_path)
    assert store.bugs()[KEY].count == 8 + 3
    for line in store.path.read_text(encoding="utf-8").splitlines():
        BugEvent.model_validate_json(line)


def _issue(title: str = "Save button silent", at_s: float = 12.0, source: str = "src_1") -> Issue:
    return Issue(project="demo", source_id=source, recording_label="rec", at_s=at_s,
                 screen="Settings", title=title, what_is_wrong="nothing happens")


def test_tb5_a_video_found_issue_becomes_one_bug_keyed_by_its_fingerprint(tmp_path: Path) -> None:
    issue = _issue()
    opening = issue_to_bug_event(issue)
    assert opening.bug_key == issue.id and re.fullmatch(r"iss_[0-9a-f]{12}", issue.id)
    store = BugStore(tmp_path)
    assert store.apply(opening).effect is Effect.APPLIED
    assert store.apply(issue_to_bug_event(_issue())).effect is Effect.DUPLICATE
    bug = store.get(issue.id)
    assert (bug.case_id, bug.screen, bug.status, bug.severity) == (None, "Settings", BugStatus.OPEN,
                                                                   issue.severity)
    assert len(store.bugs()) == 1


def test_tb5_a_different_issue_is_a_different_bug_and_its_key_holds_no_time(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply_all([issue_to_bug_event(_issue()), issue_to_bug_event(_issue("Other thing broke"))])
    assert len(store.bugs()) == 2
    assert not re.search(r"\d{4}-\d{2}", issue_to_bug_event(_issue()).bug_key)


def test_tb5_the_adapter_is_the_only_key_derivation_from_an_issue() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "autotester"
    makers = [p.relative_to(src).as_posix() for p in src.rglob("*.py")
              if re.search(r"^def \w*bug_key\w*\(", p.read_text(encoding="utf-8"), re.M)]
    assert makers == ["schema/tracked_bug.py"]
    issues_py = (src / "stages" / "issues.py").read_text(encoding="utf-8")
    assert "def issue_to_bug_event" in issues_py and len(issues_py.splitlines()) <= 300

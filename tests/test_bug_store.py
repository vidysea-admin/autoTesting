"""T-199a: the bug event store and the Issue adapter (TB1, TB5, TB6).

Contract: qa/contracts/team-bug-loop.md. Racing writers are real threads and real processes; the
store is judged by its files and by the fold, never by what a writer thought it saw.
"""

from __future__ import annotations

import itertools
import re
import threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest
from bug_loop_fixture import KEY, event, seed

from autotester.schema.issue import Issue
from autotester.schema.tracked_bug import BugEvent, BugStatus, EventKind
from autotester.stages.bug_loop import Effect, Refusal, fold, trace
from autotester.stages.issues import issue_to_bug_event
from autotester.store.bug_store import BugStore

K = EventKind
S = BugStatus


def _fails(count: int) -> list[BugEvent]:
    return [event(K.FAIL, n) for n in range(1, count + 1)]


def _snapshot(store: BugStore) -> dict[str, bytes]:
    if not store.dir.exists():
        return {}
    return {p.name: p.read_bytes() for p in sorted(store.dir.glob("*.json"))}


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
    before = _snapshot(store)
    again = store.apply(fail)
    assert again.effect is Effect.DUPLICATE and _snapshot(store) == before
    assert store.apply(event(K.PASS, 1, ref=fail.ref)).effect is Effect.DUPLICATE
    assert _snapshot(store) == before


def test_tb6_processing_a_whole_run_twice_gives_identical_stores(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    batch = [*_fails(2), event(K.PASS, 3), event(K.INCONCLUSIVE, 4),
             event(K.ASSIGN, 5, assignee="Priya")]
    first = store.apply_all(batch)
    snapshot = _snapshot(store)
    second = store.apply_all(batch)
    assert _snapshot(store) == snapshot
    applied, dup, same = Effect.APPLIED, Effect.DUPLICATE, Effect.UNCHANGED
    assert [r.effect for r in first] == [applied] * 3 + [same, applied]
    assert [r.effect for r in second] == [dup] * 3 + [same, dup]
    assert store.get(KEY).assignee == "Priya"


def test_tb6_the_same_event_twice_in_one_batch_is_applied_once(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    fail = event(K.FAIL, 1)
    assert [r.effect for r in store.apply_all([fail, fail])] == [Effect.APPLIED, Effect.DUPLICATE]
    assert store.get(KEY).count == 1


def test_tb6_a_crash_after_bug_one_of_two_converges_on_retry(tmp_path: Path) -> None:
    other = seed(crit="C2")
    run = [event(K.FAIL, 1), event(K.FAIL, 1, seed_obj=other)]
    clean = BugStore(tmp_path / "clean")
    clean.apply_all(run)
    crashed = BugStore(tmp_path / "crashed")
    crashed.apply_all(run[:1])           # the process died after bug 1
    crashed.apply_all(run)               # the whole run is retried
    assert _snapshot(crashed) == _snapshot(clean)
    assert sorted(b.count for b in crashed.bugs().values()) == [1, 1]


def test_tb6_replaying_an_old_pass_after_a_later_fail_cannot_close_the_bug(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply_all([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.PASS, 4)])
    assert store.get(KEY).status is BugStatus.FIXED
    store.apply(event(K.FAIL, 5))
    assert store.get(KEY).status is BugStatus.REOPENED
    store.apply(event(K.PASS, 4))                     # the old run is processed again
    store.apply(event(K.PASS, 6))
    got = store.get(KEY)
    assert (got.status, got.pass_streak) == (BugStatus.REOPENED, 1)


def test_a_late_event_is_judged_in_time_order_not_arrival_order(tmp_path: Path) -> None:
    late_first, in_order = BugStore(tmp_path / "late"), BugStore(tmp_path / "ordered")
    events = [event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.FAIL, 4)]
    for e in reversed(events):                        # arrival order is the reverse of time
        late_first.apply(e)
    in_order.apply_all(events)
    assert late_first.bugs() == in_order.bugs()
    assert late_first.get(KEY).status is BugStatus.REOPENED


def test_a_pass_older_than_the_latest_fail_does_not_count_toward_closing() -> None:
    got = fold([event(K.FAIL, 1), event(K.PASS, 2, minutes=50), event(K.FAIL, 3, minutes=100)])
    assert (got[KEY].status, got[KEY].pass_streak, got[KEY].count) == (BugStatus.OPEN, 0, 2)


def test_history_is_never_rewritten_only_added_to(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply_all(_fails(2))
    before = _snapshot(store)
    store.apply_all([event(K.PASS, 3), event(K.PASS, 4), event(K.FAIL, 5), event(K.ASSIGN, 6)])
    after = _snapshot(store)
    assert all(after[name] == data for name, data in before.items()) and len(after) == 6
    assert len(store.history(KEY)) == 6 and store.get(KEY).status is BugStatus.REOPENED


def test_a_refused_event_writes_nothing_but_a_state_dependent_one_is_kept(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    bad = store.apply(event(K.FAIL, 1, actor="user:umesh"))
    assert (bad.effect, bad.reason) == (Effect.REFUSED, Refusal.ACTOR_NOT_ALLOWED)
    assert _snapshot(store) == {}
    early = store.apply(event(K.PASS, 2))             # no bug yet: refused now, kept for later
    assert (early.effect, early.reason) == (Effect.REFUSED, Refusal.NO_BUG)
    store.apply(event(K.FAIL, 1))                     # the FAIL that was earlier in time arrives
    assert store.get(KEY).pass_streak == 1


def test_two_stores_in_two_directories_do_not_see_each_other(tmp_path: Path) -> None:
    BugStore(tmp_path / "a").apply(event(K.FAIL, 1))
    assert BugStore(tmp_path / "b").bugs() == {}


def test_a_corrupt_event_file_is_loud_not_silent(tmp_path: Path) -> None:
    store = BugStore(tmp_path)
    store.apply(event(K.FAIL, 1))
    (store.dir / "bev_torn.json").write_text('{"schema_version": 1, "event_id": "bev_',
                                             encoding="utf-8")
    with pytest.raises(ValueError, match=r"bev_torn\.json"):
        store.bugs()


def test_close_passes_below_one_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        BugStore(tmp_path, close_passes=0)
    store = BugStore(tmp_path, close_passes=3)
    store.apply_all([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)])
    assert store.get(KEY).status is BugStatus.OPEN


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


def test_the_fold_is_a_function_of_the_event_set_not_of_its_order() -> None:
    events = [event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.FAIL, 4),
              event(K.PASS, 5), event(K.ASSIGN, 6, assignee="Priya")]
    want = fold(events)
    for order in itertools.permutations(events):
        assert fold(order) == want
    assert (want[KEY].status, want[KEY].pass_streak, want[KEY].assignee) == (S.REOPENED, 1, "Priya")


def test_trace_says_what_each_event_did_in_time_order() -> None:
    first, second, third = event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)
    _, applied = trace([third, first, second])
    assert [applied[e.event_id].effect for e in (first, second, third)] == [Effect.APPLIED] * 3
    assert applied[third.event_id].bug.status is S.FIXED


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

"""AT-979: replaying an older run after a criterion edit must not rewrite history.

A `case_changed` event is detected by whichever run happens to be processed after the edit, so it
must never be stamped earlier than what the store already holds for that bug (qa/issues.jsonl
AT-979; contract TB4, TB6). The store, cases and rubrics are real files in a temp project.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from bug_loop_fixture import PROJECT, T0, at
from bug_run_fixture import add_case, finished_run, make_store, set_criteria, verdict

from autotester.schema.enums import Result
from autotester.schema.tracked_bug import BugStatus, EventKind, case_bug_key
from autotester.stages.bug_run import process_run
from autotester.store.bug_store import BugStore

R = Result
NOW = T0 + timedelta(days=1)


def _fail_twice_then_edit(tmp_path: Path):
    store = make_store(tmp_path)
    bugs = BugStore(tmp_path / "bugs", clock=lambda: NOW)
    case = add_case(store)
    for n in (1, 2):
        finished_run(store, f"r{n}", n, [verdict(case, f"r{n}", R.FAIL)], [case])
        process_run(store, bugs, f"r{n}")
    set_criteria(store, case, (("C1", "Pay button submits the order, always"),))
    return store, bugs, case_bug_key(PROJECT, case.id, "C1")


def test_at979_replaying_an_old_run_after_an_edit_does_not_refuse_the_later_fail(
        tmp_path: Path) -> None:
    store, bugs, key = _fail_twice_then_edit(tmp_path)
    process_run(store, bugs, "r1")                       # replay of the OLD run after the edit
    report = process_run(store, bugs, "r2")              # the later FAIL, seen again
    bug = bugs.get(key)
    assert report.refused == []
    assert (bug.status, bug.count, bug.last_seen) == (BugStatus.STALE, 2, at(2))


def test_at979_the_case_changed_event_is_never_earlier_than_the_bugs_own_history(
        tmp_path: Path) -> None:
    store, bugs, _ = _fail_twice_then_edit(tmp_path)
    process_run(store, bugs, "r1")
    changed = [e for e in bugs.events() if e.kind is EventKind.CASE_CHANGED]
    assert [e.at for e in changed] == [at(2)]

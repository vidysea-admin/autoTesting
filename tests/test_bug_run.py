"""T-199b: `process_run` turns a finished run's verdicts into bug events (TB3, TB4, TB6).

Contract: qa/contracts/team-bug-loop.md. The store, the cases and the rubrics are real files in a
temp project; the only fake is the clock. Two product questions are pinned by tests whose names
start `test_p1_` and `test_p2_`: they record today's behaviour, and are HUMAN_GATE questions.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from bug_loop_fixture import KEY, PROJECT, T0, at
from bug_run_fixture import add_case, finished_run, make_store, set_criteria, verdict

from autotester.schema.bug_run import RunOutcome
from autotester.schema.enums import Result
from autotester.schema.run import RawResult
from autotester.schema.tracked_bug import BugStatus, case_bug_key
from autotester.stages.bug_run import process_run
from autotester.store.bug_store import BugStore
from autotester.store.project_store import PinnedCaseError

R = Result
S = BugStatus
NOW = T0 + timedelta(days=1)


def _bugs(root: Path) -> BugStore:
    return BugStore(root / "bugs", clock=lambda: NOW)


def _files(bugs: BugStore) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(bugs.dir.glob("*.json"))}


def _setup(tmp_path: Path):
    store = make_store(tmp_path)
    return store, _bugs(tmp_path), add_case(store)


def _key(case, crit: str = "C1") -> str:
    return case_bug_key(PROJECT, case.id, crit)


# -- TB3: verdicts only -------------------------------------------------------------------------

def test_tb3_a_run_with_only_raw_results_and_no_verdict_changes_nothing(tmp_path: Path) -> None:
    from autotester.schema.enums import Outcome
    store, bugs, case = _setup(tmp_path)
    store.save_result("run1", RawResult(case_id=case.id, outcome=Outcome.ASSERTION_FAILED))
    finished_run(store, "run1", 1, [], [case])
    report = process_run(store, bugs, "run1")
    assert report.outcome is RunOutcome.PROCESSED and report.no_verdict_cases == [case.id]
    assert bugs.bugs() == {} and _files(bugs) == {}


def test_tb3_a_failed_verdict_opens_one_bug_per_failing_criterion(tmp_path: Path) -> None:
    store, bugs, _ = _setup(tmp_path)
    case = add_case(store, "profile", criteria=(("C1", "Name saves"), ("C2", "Photo saves")))
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL, failing=("C1", "C2"), total=2)],
                 [case])
    report = process_run(store, bugs, "run1")
    got = bugs.bugs()
    assert set(got) == {_key(case, "C1"), _key(case, "C2")} and report.applied == 2
    one = got[_key(case, "C1")]
    assert (one.status, one.count, one.first_seen, one.evidence_run_id) == (
        S.OPEN, 1, at(1), "run1")
    assert one.title.startswith("profile happy path") and "Name saves" in one.title
    assert one.criterion_fp and one.severity == case.severity


def test_tb3_a_replayed_run_with_a_judge_verdict_counts_like_any_other(tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case])
    for n in (2, 3):                      # runs 2 and 3 replay the recorded script (D-072)
        finished_run(store, f"run{n}", n, [verdict(case, f"run{n}", R.PASS)], [case])
    [process_run(store, bugs, f"run{n}") for n in (1, 2, 3)]
    bug = bugs.get(_key(case))
    assert bug.status is S.FIXED and bug.closed_by_runs == ["run2", "run3"]
    assert bug.closed_by_verdicts == [f"run2/{case.id}", f"run3/{case.id}"]


@pytest.mark.parametrize("make", [
    lambda c: verdict(c, "run2", R.PASS, met=0, total=1),                   # criteria not all met
    lambda c: verdict(c, "run2", R.PASS, total=0, met=0),                   # nothing was judged
    lambda c: verdict(c, "run2", R.PASS, images=(3, 1)),                 # partial evidence
    lambda c: verdict(c, "run2", R.INCONCLUSIVE),
    lambda c: verdict(c, "run2", R.BLOCKED),
], ids=["unmet", "no-criteria", "partial-evidence", "inconclusive", "blocked"])
def test_tb3_a_pass_that_does_not_cite_evidence_and_a_run_that_could_not_judge_close_nothing(
        tmp_path: Path, make) -> None:
    store, bugs, case = _setup(tmp_path)
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case])
    finished_run(store, "run2", 2, [make(case)], [case])
    finished_run(store, "run3", 3, [make(case)], [case])
    [process_run(store, bugs, f"run{n}") for n in (1, 2, 3)]
    bug = bugs.get(_key(case))
    assert (bug.status, bug.pass_streak, bug.count) == (S.OPEN, 0, 1)


def test_p2_choice_pinned_an_uncited_fail_does_not_break_a_pass_streak(tmp_path: Path) -> None:
    """HUMAN_GATE P2: a FAIL verdict that names no criterion is `inconclusive` (kept as-is), so
    F, P, uncited-FAIL, P closes the bug. If the owner rules otherwise, flip this test."""
    store, bugs, case = _setup(tmp_path)
    plan = [(1, verdict(case, "run1", R.FAIL)), (2, verdict(case, "run2", R.PASS)),
            (3, verdict(case, "run3", R.FAIL, failing=())), (4, verdict(case, "run4", R.PASS))]
    for n, v in plan:
        finished_run(store, f"run{n}", n, [v], [case])
        process_run(store, bugs, f"run{n}")
    assert bugs.get(_key(case)).status is S.FIXED


def test_p1_choice_pinned_a_new_fail_on_a_stale_key_is_refused_not_reopened(
        tmp_path: Path) -> None:
    """HUMAN_GATE P1: today a FAIL on a key that went stale is refused `stale_bug`. If the owner
    rules that it must open or reopen the bug, this test is the one to flip."""
    store, bugs, case = _setup(tmp_path)
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case])
    process_run(store, bugs, "run1")
    store.delete_case(case.id)
    finished_run(store, "run2", 2, [], [])
    process_run(store, bugs, "run2")
    assert bugs.get(_key(case)).status is S.STALE
    finished_run(store, "run3", 3, [verdict(case, "run3", R.FAIL)], [])
    report = process_run(store, bugs, "run3")
    assert bugs.get(_key(case)).status is S.STALE and bugs.get(_key(case)).count == 1
    assert any("stale_bug" in line for line in report.refused)


def test_a_run_that_is_not_finished_or_belongs_to_another_project_applies_nothing(
        tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    store.save_verdict("run1", verdict(case, "run1", R.FAIL))          # no run.json yet
    assert process_run(store, bugs, "run1").outcome is RunOutcome.NOT_FINISHED
    other = make_store(tmp_path / "other")
    finished_run(other, "run2", 2, [], [])
    other.paths.run_dir("run2").joinpath("run.json").write_text(
        other.paths.run_dir("run2").joinpath("run.json").read_text(encoding="utf-8").replace(
            f'"{PROJECT}"', '"someone-else"'), encoding="utf-8")
    assert process_run(other, bugs, "run2").outcome is RunOutcome.WRONG_PROJECT
    assert _files(bugs) == {}


# -- TB4: an honest close -----------------------------------------------------------------------

def test_tb4_a_case_deleted_after_a_fail_makes_the_bug_stale_at_the_next_run(
        tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    other = add_case(store, "login")
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case, other])
    process_run(store, bugs, "run1")
    assert store.delete_case(case.id)
    finished_run(store, "run2", 2, [verdict(other, "run2", R.PASS)], [other])
    report = process_run(store, bugs, "run2")
    assert bugs.get(_key(case)).status is S.STALE and report.case_changed == [_key(case)]
    finished_run(store, "run3", 3, [verdict(other, "run3", R.PASS)], [other])
    process_run(store, bugs, "run3")
    assert bugs.get(_key(case)).status is S.STALE and bugs.get(_key(case)).closed_by_runs == []


def test_tb4_an_edited_criterion_makes_the_bug_stale_never_fixed(tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case])
    process_run(store, bugs, "run1")
    set_criteria(store, case, (("C1", "Pay button submits the order and shows a receipt"),))
    for n in (2, 3):                       # two clean passes against the NEW bar prove nothing
        finished_run(store, f"run{n}", n, [verdict(case, f"run{n}", R.PASS)], [case])
        process_run(store, bugs, f"run{n}")
    bug = bugs.get(_key(case))
    assert bug.status is S.STALE and bug.closed_by_runs == [] and bug.closed_by_verdicts == []


def test_tb4_an_unchanged_case_and_criterion_leave_the_bug_alone(tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    for n in (1, 2):
        finished_run(store, f"run{n}", n, [verdict(case, f"run{n}", R.FAIL)], [case])
        report = process_run(store, bugs, f"run{n}")
        assert report.case_changed == [] and report.unverifiable == []
    assert (bugs.get(_key(case)).status, bugs.get(_key(case)).count) == (S.OPEN, 2)


def test_tb4_a_removed_criterion_is_a_change(tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case])
    process_run(store, bugs, "run1")
    set_criteria(store, case, (("C9", "something else"),))
    finished_run(store, "run2", 2, [], [case])
    assert process_run(store, bugs, "run2").case_changed == [_key(case)]


def test_tb4_a_rubric_that_cannot_be_loaded_is_reported_not_guessed(tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    finished_run(store, "run1", 1, [verdict(case, "run1", R.FAIL)], [case])
    process_run(store, bugs, "run1")
    store.paths.rubrics_dir.joinpath(f"{case.rubric_ref}.json").unlink()
    finished_run(store, "run2", 2, [], [case])
    report = process_run(store, bugs, "run2")
    assert report.unverifiable == [_key(case)] and bugs.get(_key(case)).status is S.OPEN


def test_tb4_a_closed_bug_is_not_swept_to_stale_when_its_case_goes(tmp_path: Path) -> None:
    store, bugs, case = _setup(tmp_path)
    for n, res in ((1, R.FAIL), (2, R.PASS), (3, R.PASS)):
        finished_run(store, f"run{n}", n, [verdict(case, f"run{n}", res)], [case])
        process_run(store, bugs, f"run{n}")
    assert bugs.get(_key(case)).status is S.FIXED
    store.delete_case(case.id)
    finished_run(store, "run4", 4, [], [])
    process_run(store, bugs, "run4")
    assert bugs.get(_key(case)).status is S.FIXED


def test_tb4_closing_a_bug_never_deletes_its_pinned_case(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    bugs, case = _bugs(tmp_path), add_case(store, pinned=True)
    before = store.paths.cases.read_bytes()
    for n, res in ((1, R.FAIL), (2, R.PASS), (3, R.PASS)):
        finished_run(store, f"run{n}", n, [verdict(case, f"run{n}", res)], [case])
        process_run(store, bugs, f"run{n}")
    assert bugs.get(_key(case)).status is S.FIXED
    assert store.paths.cases.read_bytes() == before and store.get_case(case.id) is not None
    with pytest.raises(PinnedCaseError):
        store.delete_case(case.id)


def test_tb4_a_change_and_a_pass_at_one_instant_go_stale_not_fixed(tmp_path: Path) -> None:
    """Replay order puts a changed case before a PASS at the same instant (a PASS on a bar that
    no longer exists proves nothing), whatever the two event ids hash to."""
    from bug_loop_fixture import event

    from autotester.schema.tracked_bug import EventKind as K
    from autotester.stages.bug_loop import fold
    events = [event(K.FAIL, 1), event(K.PASS, 2, minutes=5), event(K.PASS, 3, minutes=5),
              event(K.CASE_CHANGED, 4, minutes=5, run="run4")]
    assert fold(events)[KEY].status is S.STALE

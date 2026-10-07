"""TB1-TB3 (qa/contracts/team-bug-loop.md): the bug key, the lifecycle table and verdict-only input.

Each test names the real caller or situation that reaches it: a nightly regression that keeps
failing the same criterion, a run the judge could not finish, a replayed run, a case a human
deleted, a tester who changed the rubric.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from bug_loop_fixture import PROJECT, add_case, bug_of, make_store, save_run, verdict

from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, Outcome, Result
from autotester.schema.issue import Issue
from autotester.schema.run import RawResult, Run
from autotester.schema.tracked_bug import BugStatus, TrackedBug, case_bug_key
from autotester.stages.bug_loop import (
    CLOSE_PASSES_DEFAULT,
    TRANSITIONS,
    BugSignal,
    Move,
    adopt_issue,
    load_bugs,
    process_run,
    signal_of,
    step,
)
from autotester.stages.issues import bug_from_issue

T0 = datetime(2026, 10, 7, tzinfo=UTC)


# -- TB1: the key is stable --------------------------------------------------------------------

def test_tb1_three_nightly_runs_failing_one_criterion_are_one_bug(tmp_path: Path) -> None:
    """The nightly regression fails C1 on the same case three times."""
    store = make_store(tmp_path)
    case = add_case(store)
    for n in (1, 2, 3):
        process_run(store, save_run(store, f"run-{n}", verdict(f"run-{n}", case, Result.FAIL,
                                                               failing=("C1",))))
    bug = bug_of(store)
    assert bug.bug_key == case_bug_key(PROJECT, case.id, "C1")
    assert (bug.status, bug.count) == (BugStatus.OPEN, 3)


def test_tb1_two_failing_criteria_on_one_case_are_two_bugs(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    case = add_case(store, criteria=(("C1", "a"), ("C2", "b")))
    process_run(store, save_run(store, "run-1", verdict("run-1", case, Result.FAIL,
                                                        failing=("C1", "C2"), total=2)))
    assert {b.criterion_id for b in load_bugs(store)} == {"C1", "C2"}
    assert len({b.bug_key for b in load_bugs(store)}) == 2


def test_tb1_the_key_depends_on_project_case_and_criterion_only() -> None:
    """Same failure -> same key; a different criterion or project -> a different bug."""
    assert case_bug_key(PROJECT, "case_1", "C1") == case_bug_key(PROJECT, "case_1", "C1")
    assert case_bug_key(PROJECT, "case_1", "C1") != case_bug_key(PROJECT, "case_1", "C2")
    assert case_bug_key(PROJECT, "case_1", "C1") != case_bug_key("other", "case_1", "C1")


def test_tb1_a_secret_planted_in_case_text_is_not_in_the_key(tmp_path: Path) -> None:
    """A tester typed a password into a step value; it must not surface through the bug key."""
    store = make_store(tmp_path)
    case = add_case(store, target="/login?pw=hunter2-SECRET")
    process_run(store, save_run(store, "run-1", verdict("run-1", case, Result.FAIL,
                                                        failing=("C1",))))
    assert "hunter2" not in bug_of(store).bug_key


# -- TB2: the lifecycle, every cell ------------------------------------------------------------

def a_bug(status: BugStatus | None, streak: int = 0) -> TrackedBug | None:
    if status is None:
        return None
    return TrackedBug(bug_key="bug_k", project=PROJECT, case_id="c", criterion_id="C1",
                      title="t", status=status, count=2, first_seen=T0, last_seen=T0,
                      pass_streak=streak)


CELLS = [
    # (state, signal, expected status, expected count, expected streak)
    (None, BugSignal.FAIL, BugStatus.OPEN, 1, 0),
    (BugStatus.OPEN, BugSignal.FAIL, BugStatus.OPEN, 3, 0),
    (BugStatus.REOPENED, BugSignal.FAIL, BugStatus.REOPENED, 3, 0),
    (BugStatus.FIXED, BugSignal.FAIL, BugStatus.REOPENED, 3, 0),
    (BugStatus.STALE, BugSignal.FAIL, BugStatus.OPEN, 1, 0),
    (BugStatus.OPEN, BugSignal.PASS, BugStatus.OPEN, 2, 1),
    (BugStatus.REOPENED, BugSignal.PASS, BugStatus.REOPENED, 2, 1),
    (BugStatus.FIXED, BugSignal.PASS, BugStatus.FIXED, 2, 0),
    (BugStatus.STALE, BugSignal.PASS, BugStatus.STALE, 2, 0),
    (None, BugSignal.PASS, None, 0, 0),
    *[(s, BugSignal.NONE, s, 2, 0) for s in (None, *BugStatus)
      if s is not None],
]


@pytest.mark.parametrize("state, signal, status, count, streak", CELLS)
def test_tb2_every_cell_of_the_table(state, signal, status, count, streak) -> None:
    """Each (state, signal) pair a real run can produce lands where the contract says."""
    bug = step(a_bug(state), signal, project=PROJECT, case_id="c", criterion_id="C1",
               fp="fp", title="t", at=T0, run_id="run-9", ref="run-9/c", close_passes=2)
    if status is None:
        assert bug is None
        return
    assert (bug.status, bug.count, bug.pass_streak) == (status, count, streak)


def test_tb2_the_table_is_total_over_states_and_signals() -> None:
    for state in (None, *BugStatus):
        for signal in BugSignal:
            assert (state, signal) in TRANSITIONS, (state, signal)
    assert Move.NOOP in TRANSITIONS.values()


def test_tb2_default_n_is_two_and_the_streak_closes_on_the_nth_pass() -> None:
    assert CLOSE_PASSES_DEFAULT == 2
    bug = a_bug(BugStatus.OPEN)
    kw = dict(project=PROJECT, case_id="c", criterion_id="C1", fp="", title="t", at=T0,
              close_passes=2)
    bug = step(bug, BugSignal.PASS, run_id="r1", ref="r1/c", **kw)
    assert bug.status is BugStatus.OPEN  # k=1 < N
    bug = step(bug, BugSignal.PASS, run_id="r2", ref="r2/c", **kw)
    assert bug.status is BugStatus.FIXED
    assert (bug.closed_by_runs, bug.closed_by_verdicts) == (["r1", "r2"], ["r1/c", "r2/c"])


def test_tb2_a_fail_between_two_passes_resets_the_streak(tmp_path: Path) -> None:
    """PASS, FAIL, PASS is not 'two consecutive passes' (the nightly flaked in the middle)."""
    store = make_store(tmp_path)
    case = add_case(store)
    plan = [("r1", Result.FAIL), ("r2", Result.PASS), ("r3", Result.FAIL), ("r4", Result.PASS)]
    for run_id, result in plan:
        fails = ("C1",) if result is Result.FAIL else ()
        process_run(store, save_run(store, run_id, verdict(run_id, case, result, failing=fails)))
    assert bug_of(store).status is BugStatus.OPEN
    process_run(store, save_run(store, "r5", verdict("r5", case, Result.PASS)))
    assert bug_of(store).status is BugStatus.FIXED


@pytest.mark.parametrize("result", [Result.INCONCLUSIVE, Result.BLOCKED])
def test_tb2_a_run_that_could_not_judge_neither_closes_nor_opens(tmp_path: Path, result) -> None:
    """The judge errored (INCONCLUSIVE) or the executor needed a human (BLOCKED)."""
    store = make_store(tmp_path)
    case = add_case(store)
    process_run(store, save_run(store, "r0", verdict("r0", case, Result.FAIL, failing=("C1",))))
    before = bug_of(store).model_dump()
    process_run(store, save_run(store, "r1", verdict("r1", case, result, total=0, met=0)))
    after = bug_of(store).model_dump()
    assert after["status"] == before["status"] and after["count"] == before["count"]
    assert after["pass_streak"] == 0
    other = add_case(store, "/other")
    process_run(store, save_run(store, "r2", verdict("r2", other, result, total=0, met=0)))
    assert len(load_bugs(store)) == 1  # nothing was opened for the case that could not judge


def test_tb2_a_fixed_bug_that_fails_again_is_reopened(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    case = add_case(store)
    plan = [("r1", Result.FAIL), ("r2", Result.PASS), ("r3", Result.PASS), ("r4", Result.FAIL)]
    for run_id, result in plan:
        fails = ("C1",) if result is Result.FAIL else ()
        process_run(store, save_run(store, run_id, verdict(run_id, case, result, failing=fails)))
    bug = bug_of(store)
    assert (bug.status, bug.count) == (BugStatus.REOPENED, 2)
    assert bug.last_seen >= bug.first_seen


# -- TB3: verdicts only ------------------------------------------------------------------------

def test_tb3_a_run_with_only_a_raw_result_changes_nothing(tmp_path: Path) -> None:
    """The judge never ran (crash between execute and grade): a RawResult says assertion_failed."""
    store = make_store(tmp_path)
    case = add_case(store)
    store.save_run(Run(id="r1", project=PROJECT, case_ids=[case.id]))
    store.save_result("r1", RawResult(case_id=case.id, outcome=Outcome.ASSERTION_FAILED))
    process_run(store, "r1")
    assert load_bugs(store) == []


def test_tb3_a_replayed_run_with_a_judge_verdict_counts_like_any_other(tmp_path: Path) -> None:
    """D-072: a script replay is still graded; its FAIL opens a bug and its PASSes close it."""
    store = make_store(tmp_path)
    case = add_case(store)
    for run_id, result in [("r1", Result.FAIL), ("r2", Result.PASS), ("r3", Result.PASS)]:
        fails = ("C1",) if result is Result.FAIL else ()
        save_run(store, run_id, verdict(run_id, case, result, failing=fails))
        store.save_result(run_id, RawResult(case_id=case.id, outcome=Outcome.COMPLETED,
                                            used_script=True))
        process_run(store, run_id)
    assert bug_of(store).status is BugStatus.FIXED


def test_tb3_a_pass_that_cites_no_evidence_does_not_count_toward_closing(tmp_path: Path) -> None:
    """A PASS whose scoreboard shows 0 of N criteria met, or that rested on screenshots the
    judge never saw, is not evidence a fix landed (the grade rule is not weakened)."""
    store = make_store(tmp_path)
    case = add_case(store)
    process_run(store, save_run(store, "r1", verdict("r1", case, Result.FAIL, failing=("C1",))))
    process_run(store, save_run(store, "r2", verdict("r2", case, Result.PASS, met=0)))
    process_run(store, save_run(store, "r3", verdict("r3", case, Result.PASS, seen=0, asked=2)))
    bug = bug_of(store)
    assert (bug.status, bug.pass_streak) == (BugStatus.OPEN, 0)
    process_run(store, save_run(store, "r4", verdict("r4", case, Result.PASS)))
    process_run(store, save_run(store, "r5", verdict("r5", case, Result.PASS)))
    assert bug_of(store).status is BugStatus.FIXED


def test_tb3_signal_of_reads_only_a_verdict() -> None:
    case = Case(project=PROJECT, flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="t")
    assert signal_of(verdict("r", case, Result.PASS)) is BugSignal.PASS
    assert signal_of(verdict("r", case, Result.INCONCLUSIVE)) is BugSignal.NONE


# -- TB1/TB5: the Issue -> TrackedBug adapter lives in stages/issues.py -------------------------

def test_tb5_a_video_found_issue_becomes_a_bug_keyed_by_its_fingerprint(tmp_path: Path) -> None:
    """A tester's recording was analysed twice (a re-run of the video stage)."""
    store = make_store(tmp_path)
    issue = Issue(project=PROJECT, source_id="src_1", recording_label="rec", at_s=93.0,
                  screen="Dashboard", title="Heading missing", what_is_wrong="no heading")
    twin = Issue(project=PROJECT, source_id="src_1", recording_label="rec", at_s=93.0,
                 screen="Dashboard", title="Heading missing", what_is_wrong="no heading")
    bug = bug_from_issue(issue)
    assert bug.bug_key == issue.id == bug_from_issue(twin).bug_key
    assert (bug.status, bug.case_id, bug.count) == (BugStatus.OPEN, None, 1)
    adopt_issue(store, issue)
    adopt_issue(store, twin)
    assert [b.bug_key for b in load_bugs(store)] == [issue.id]

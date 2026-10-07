"""TB4 (an honest close) and TB6 (idempotent per run) of qa/contracts/team-bug-loop.md.

Real situations: a developer fixes a bug and two nightlies pass; a tester deletes or rewrites
the case a bug was filed against; the scheduler delivers run R twice; the server dies mid-run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bug_loop_fixture import add_case, bug_of, make_store, save_run, set_criteria, verdict

from autotester.schema.enums import Result
from autotester.schema.tracked_bug import BugStatus
from autotester.stages import bug_loop
from autotester.stages.bug_loop import load_bugs, process_run
from autotester.store.project_store import PinnedCaseError


def run_plan(store, case, plan) -> None:
    for run_id, result in plan:
        fails = ("C1",) if result is Result.FAIL else ()
        process_run(store, save_run(store, run_id, verdict(run_id, case, result, failing=fails)))


# -- TB4 ---------------------------------------------------------------------------------------

def test_tb4_a_fixed_bug_lists_the_runs_and_verdicts_that_closed_it(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    case = add_case(store)
    run_plan(store, case, [("r1", Result.FAIL), ("r2", Result.PASS), ("r3", Result.PASS)])
    bug = bug_of(store)
    assert bug.status is BugStatus.FIXED
    assert bug.closed_by_runs == ["r2", "r3"]
    assert bug.closed_by_verdicts == [f"r2/{case.id}", f"r3/{case.id}"]


def test_tb4_a_deleted_case_makes_its_open_bug_stale_not_fixed(tmp_path: Path) -> None:
    """A tester pruned the case after it failed; the next run cannot say the bug is fixed."""
    store = make_store(tmp_path)
    case = add_case(store)
    run_plan(store, case, [("r1", Result.FAIL)])
    assert store.delete_case(case.id)
    process_run(store, save_run(store, "r2"))
    assert bug_of(store).status is BugStatus.STALE


def test_tb4_a_changed_criterion_makes_the_bug_stale_even_if_the_next_runs_pass(
    tmp_path: Path,
) -> None:
    """The rubric was rewritten after the failure: later PASSes judge a different bar."""
    store = make_store(tmp_path)
    case = add_case(store)
    run_plan(store, case, [("r1", Result.FAIL)])
    set_criteria(store, case, (("C1", "heading is shown AND the date is current"),))
    run_plan(store, case, [("r2", Result.PASS), ("r3", Result.PASS)])
    bug = bug_of(store)
    assert bug.status is BugStatus.STALE
    assert bug.closed_by_runs == []


def test_tb4_closing_a_bug_never_deletes_its_pinned_regression_case(tmp_path: Path) -> None:
    """A case pinned from a confirmed issue (R15) stays when its bug closes."""
    store = make_store(tmp_path)
    case = add_case(store, pinned=True)
    run_plan(store, case, [("r1", Result.FAIL), ("r2", Result.PASS), ("r3", Result.PASS)])
    assert bug_of(store).status is BugStatus.FIXED
    assert store.get_case(case.id) is not None
    with pytest.raises(PinnedCaseError):
        store.delete_case(case.id)


# -- TB6 ---------------------------------------------------------------------------------------

def test_tb6_processing_the_same_run_twice_leaves_the_store_byte_identical(
    tmp_path: Path,
) -> None:
    """The scheduler redelivers run r2 after a restart."""
    store = make_store(tmp_path)
    case = add_case(store)
    run_plan(store, case, [("r1", Result.FAIL), ("r2", Result.FAIL)])
    before = store.paths.bugs.read_bytes()
    process_run(store, "r2")
    assert store.paths.bugs.read_bytes() == before
    assert bug_of(store).count == 2


def test_tb6_without_the_marker_the_applied_refs_still_stop_a_double_count(
    tmp_path: Path,
) -> None:
    """The marker file was lost (a restored backup): the bug itself remembers r2."""
    store = make_store(tmp_path)
    case = add_case(store)
    run_plan(store, case, [("r1", Result.FAIL), ("r2", Result.FAIL)])
    store.paths.bug_run_marker("r2").unlink()
    process_run(store, "r2")
    assert bug_of(store).count == 2


def test_tb6_a_crash_after_bug_one_of_two_converges_on_retry(tmp_path: Path, monkeypatch) -> None:
    """The process dies after saving the first of two bugs from one run."""
    store = make_store(tmp_path)
    case = add_case(store, criteria=(("C1", "a"), ("C2", "b")))
    save_run(store, "r1", verdict("r1", case, Result.FAIL, failing=("C1", "C2"), total=2))
    real, calls = bug_loop._save, []

    def dying_save(s, bug) -> None:
        if calls:
            raise OSError("disk gone")
        calls.append(bug.bug_key)
        real(s, bug)

    monkeypatch.setattr(bug_loop, "_save", dying_save)
    with pytest.raises(OSError):
        process_run(store, "r1")
    assert len(load_bugs(store)) == 1 and not store.paths.bug_run_marker("r1").exists()
    monkeypatch.setattr(bug_loop, "_save", real)
    process_run(store, "r1")
    assert sorted(b.count for b in load_bugs(store)) == [1, 1]
    assert store.paths.bug_run_marker("r1").exists()


def test_tb6_the_close_threshold_is_a_stored_project_value(tmp_path: Path) -> None:
    """A team that wants three clean runs sets it on the project; the default stays two."""
    store = make_store(tmp_path)
    project = store.load_project()
    assert project.bug_close_passes == 2
    store.save_project(project.model_copy(update={"bug_close_passes": 3}))
    case = add_case(store)
    run_plan(store, case, [("r1", Result.FAIL), ("r2", Result.PASS), ("r3", Result.PASS)])
    assert bug_of(store).status is BugStatus.OPEN
    run_plan(store, case, [("r4", Result.PASS)])
    assert bug_of(store).status is BugStatus.FIXED

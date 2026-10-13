"""TA7: a failure becomes one bug, closes only on evidence, reopens on the same key. The runs
are real presses on the stub product; each finished run is applied with `bug_run.process_run`
(nothing on master calls it from the run path yet, so the rig calls it exactly as the TB tests
do). The tracker page row (TB7) is xfail(strict) until T-199 adds the page."""

from __future__ import annotations

from rig import SLUG, World, press

from autotester.schema.tracked_bug import BugStatus
from autotester.stages.bug_run import process_run


def _run(world: World, mode: str) -> str:
    world.set_stub(mode)
    run_id = press(world, "dev")
    process_run(world.store(), world.bugs(), run_id)
    return run_id


def _only_bug(world: World):
    bugs = world.bugs().bugs()
    assert len(bugs) == 1, list(bugs)
    return next(iter(bugs.values()))


def test_one_bug_with_a_stable_key_and_a_second_press_raises_the_count(world: World) -> None:
    first = _run(world, "defect")
    bug = _only_bug(world)
    assert bug.count == 1 and bug.evidence_run_id == first and bug.status is BugStatus.OPEN
    key = bug.bug_key
    _run(world, "defect")
    again = _only_bug(world)
    assert again.bug_key == key and again.count == 2


def test_closes_only_after_two_consecutive_passes_inconclusive_closes_nothing(
        world: World) -> None:
    _run(world, "defect")
    key = _only_bug(world).bug_key
    _run(world, "ok")
    assert _only_bug(world).status is BugStatus.OPEN          # one pass is not enough
    _run(world, "inconclusive")
    assert _only_bug(world).status is not BugStatus.FIXED     # unjudged closes nothing
    _run(world, "ok")
    _run(world, "ok")
    closed = _only_bug(world)
    assert closed.status is BugStatus.FIXED and closed.bug_key == key
    assert len(closed.closed_by_runs) >= 2 and closed.closed_by_verdicts
    _run(world, "defect")
    reopened = _only_bug(world)
    assert reopened.status is BugStatus.REOPENED and reopened.bug_key == key


def test_processing_a_run_twice_changes_nothing(world: World) -> None:
    run_id = _run(world, "defect")
    before = {p.name: p.read_bytes() for p in world.bugs().dir.glob("*.json")}
    report = process_run(world.store(), world.bugs(), run_id)
    assert report.applied == 0
    assert {p.name: p.read_bytes() for p in world.bugs().dir.glob("*.json")} == before


def test_a_run_in_one_project_does_not_touch_another_projects_bugs(world: World) -> None:
    _run(world, "defect")
    assert world.bugs("other").bugs() == {}


def test_tb7_dev_subadmin_admin_see_the_tracker_tester_only_shared_other_nothing(
        world: World) -> None:
    _run(world, "defect")
    for who in ("dev", "subadmin", "admin"):
        assert world.users[who].get(f"/projects/{SLUG}/tracker").status_code == 200

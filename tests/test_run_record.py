"""T-136c: run_record stamps measured started/finished and prints the run id (fakes, no browser)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from autotester.stages.run_record import now_utc, record_run, run_id_lines
from autotester.store.project_store import ProjectStore


def test_record_run_persists_both_timestamps(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    t0 = datetime(2026, 10, 13, 9, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=42)
    record_run(store, "run-X", "pathlynks", ["c1", "c2"], t0, t1)
    loaded = store.load_run("run-X")
    assert loaded is not None
    assert loaded.started_at == t0 and loaded.finished_at == t1
    assert loaded.case_ids == ["c1", "c2"]


def test_record_run_rejects_backwards_clock(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    t0 = now_utc()
    with pytest.raises(ValueError):
        record_run(store, "run-Y", "pathlynks", [], t0, t0 - timedelta(seconds=1))
    assert store.load_run("run-Y") is None


def test_now_utc_is_timezone_aware() -> None:
    assert now_utc().tzinfo is not None


def test_run_id_lines_print_explicit_run_id() -> None:
    lines = run_id_lines("run-ABC", Path("x") / "run-ABC")
    assert lines[1] == "run_id: run-ABC"
    assert lines[0].startswith("run: ")


def test_record_run_feeds_the_bug_loop_like_launch_run(tmp_path: Path) -> None:
    """A script-driven run (run_pathlynks_first_cases -> record_run) reaches the tracker too."""
    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind, Result
    from autotester.schema.flowspec import Step
    from autotester.schema.verdict import Failure, Verdict
    from autotester.store.bug_store import BugStore

    store = ProjectStore("pathlynks", tmp_path)
    case = Case(project="pathlynks", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="Login works", steps=[Step(order=0, action=Action.CLICK, target="#go")])
    store.add_case(case)
    store.save_verdict("run-B", Verdict(
        run_id="run-B", case_id=case.id, result=Result.FAIL, criteria_met=0, criteria_total=1,
        grader_provider="mock", failures=[Failure(criterion_id="C1", reason="no redirect")]))
    t0 = now_utc()
    record_run(store, "run-B", "pathlynks", [case.id], t0, t0 + timedelta(seconds=1))
    (bug,) = BugStore(store.paths.dir).bugs().values()
    assert bug.evidence_run_id == "run-B" and bug.count == 1

"""E4.1 (qa/contracts/e2e-fixes.md, AT-1421): the wall-clock bound stops the run, the unstarted
cases are INCONCLUSIVE with the reason `wall_clock_s`, the run records why it stopped, and the
Run bounds card on the run page shows the D-112 arithmetic. Fakes and an injected clock only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from e2e_run_fixture import fake_clock, seams, store_for, wire_browser
from fastapi.testclient import TestClient

from autotester.core.trace import read_spans
from autotester.schema.enums import Result
from autotester.schema.run import Run, RunBounds
from autotester.schema.trace import StageSpan
from autotester.stages.run_launcher import launch_run
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

WALL = 170.0  # the gate asks 3 x 8 s + 3 x 45 s = 159 s for three one-step cases


def test_a_run_whose_acting_time_reaches_the_bound_stops_and_names_the_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = fake_clock(monkeypatch)
    log = wire_browser(monkeypatch, on_case=lambda: setattr(clock, "now", clock.now + 200.0))
    store = store_for(tmp_path, monkeypatch, "http://127.0.0.1:9/", cases=3, wall_clock_s=WALL)
    run = launch_run("demo", seams=seams())
    verdicts = store.load_verdicts(run.id)
    held = [v for v in verdicts if v.result is Result.INCONCLUSIVE]
    assert log.count("case") == 1  # case 1 ran and burnt the clock; 2 and 3 never started
    assert len(verdicts) == 3 and len(held) == 2
    assert all("wall_clock_s" in (v.note or "") for v in held)  # not FAIL, not silently absent
    assert [v.result for v in verdicts].count(Result.FAIL) == 0
    assert run.stop_reason == "wall_clock_s"
    execute = [s for s in read_spans(store.paths.run_trace(run.id))
               if isinstance(s, StageSpan) and s.stage.value == "execute"]
    assert [(s.status, s.error) for s in execute] == [
        ("failed", "run budget exhausted: wall_clock_s")]


def test_a_run_inside_its_bound_records_no_stop_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_clock(monkeypatch)
    wire_browser(monkeypatch)
    store_for(tmp_path, monkeypatch, "http://127.0.0.1:9/", cases=2, wall_clock_s=WALL)
    assert launch_run("demo", seams=seams()).stop_reason is None


def test_the_run_records_the_acting_time_beside_what_was_held_off_the_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = fake_clock(monkeypatch)
    wire_browser(monkeypatch, on_case=lambda: setattr(clock, "now", clock.now + 30.0))
    store_for(tmp_path, monkeypatch, "http://127.0.0.1:9/", cases=1, wall_clock_s=WALL)
    run = launch_run("demo", seams=seams())
    assert run.excluded_s is not None and run.excluded_s["acting"] == pytest.approx(30.0)


# --- the run page ---------------------------------------------------------------------------

def _page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **fields) -> str:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    from autotester.schema.project import Project
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.save_run(Run(id="run-e4-page", project="demo", **fields))
    response = TestClient(app).get("/projects/demo/runs/run-e4-page")
    assert response.status_code == 200
    return response.text


BOUNDS = RunBounds(approval_id="appr-1", max_actions=100, max_probes=0, wall_clock_s=170.0)


def test_the_bounds_card_states_acting_time_judge_and_housekeeping_seconds_and_the_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _page(tmp_path, monkeypatch, bounds=BOUNDS, stop_reason="wall_clock_s", excluded_s={
        "judging": 40.0, "housekeeping": 20.0, "total": 60.0, "acting": 171.5,
        "acted_during_exclusion": 0.0})
    assert "170.0s" in text  # the bound itself
    assert "acting 171.5s" in text
    assert "judging 40.0s" in text and "housekeeping 20.0s" in text
    assert "wall_clock_s" in text  # why it stopped


def test_a_run_from_before_d112_says_not_recorded_never_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _page(tmp_path, monkeypatch, bounds=BOUNDS, excluded_s=None)
    assert "clock accounting NOT RECORDED" in text
    assert "judging 0" not in text


def test_a_run_recorded_before_the_acting_figure_still_renders_its_held_off_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _page(tmp_path, monkeypatch, bounds=BOUNDS, excluded_s={
        "judging": 40.0, "housekeeping": 20.0, "total": 60.0, "acted_during_exclusion": 0.0})
    assert "judging 40.0s" in text and "acting time NOT RECORDED" in text


def test_a_target_that_never_answered_is_not_described_as_cases_that_still_ran(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    msg = "target demo.test did not answer within 10 s from this server"
    text = _page(tmp_path, monkeypatch, bounds=BOUNDS, preflight_warnings=[msg],
                 stop_reason="target_unreachable")
    assert msg in text and text.count(msg) == 1
    assert "every case below still ran" not in text
    assert "no case was run" in text

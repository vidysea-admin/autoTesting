"""E4.2 (qa/contracts/e2e-fixes.md, AT-1421), through `launch_run`: a target that does not answer
ends the run fast with ONE message and every case INCONCLUSIVE, with zero browser launches; a
target that answers 500 runs as before. Local stubs (`e2e_target_stub`), fakes only.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from e2e_run_fixture import seams, store_for, wire_browser
from e2e_target_stub import responder, silent

from autotester.browser.session import BrowserSession
from autotester.core.trace import read_spans
from autotester.schema.enums import Result
from autotester.schema.trace import StageSpan
from autotester.stages import reachability
from autotester.stages.reachability import probe_target
from autotester.stages.run_launcher import launch_run


def _no_browser(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    launched: list[str] = []

    def boom(self):
        launched.append("start")
        raise AssertionError("a browser was started for an unreachable target")

    monkeypatch.setattr(BrowserSession, "start", boom)
    return launched


def test_an_unreachable_target_ends_the_run_fast_with_one_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reachability, "PROBE_TOTAL_S", 1.0)  # the 10 s constant: test_target_probe
    launched = _no_browser(monkeypatch)
    with silent() as stub:
        store = store_for(tmp_path, monkeypatch, stub.url, cases=3)
        started = time.monotonic()
        run = launch_run("demo", seams=seams(target_probe=probe_target))
        assert time.monotonic() - started < 15
    message = "target 127.0.0.1 did not answer within 1 s from this server [stage=timeout]"
    assert launched == []
    assert run.preflight_warnings == [message]
    assert run.stop_reason == "target_unreachable"
    verdicts = store.load_verdicts(run.id)
    assert len(verdicts) == 3 and {v.result for v in verdicts} == {Result.INCONCLUSIVE}
    assert all(message in (v.note or "") for v in verdicts)  # the cause, not 3 goto timeouts
    assert len(store.load_results(run.id)) == 3
    artefacts = [p for p in store.paths.run_dir(run.id).rglob("*")
                 if p.suffix in {".png", ".webm"}]
    assert artefacts == []  # a case that never ran produced no screenshot and no video
    execute = [s for s in read_spans(store.paths.run_trace(run.id))
               if isinstance(s, StageSpan) and s.stage.value == "execute"]
    assert [s.status for s in execute] == ["failed"]


def test_the_stopped_run_records_zero_acting_time_not_a_missing_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The acting clock must not start before the probe: the 1 s the probe spends waiting is not
    time acting on the target (the run page showed 'acting 1.0s' for a run that never acted)."""
    from fastapi.testclient import TestClient

    from autotester.ui.app import app

    monkeypatch.setattr(reachability, "PROBE_TOTAL_S", 1.0)
    _no_browser(monkeypatch)
    with silent() as stub:
        store_for(tmp_path, monkeypatch, stub.url)
        run = launch_run("demo", seams=seams(target_probe=probe_target))
    assert run.excluded_s is not None
    assert run.excluded_s["acting"] == 0.0 and run.excluded_s["total"] == 0.0
    page = TestClient(app).get(f"/projects/demo/runs/{run.id}").text
    assert "acting 0.0s" in page and "acting 1." not in page


def test_a_probe_bug_lets_the_run_proceed_and_says_why_on_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import urllib.request

    def boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", boom)
    log = wire_browser(monkeypatch)
    store = store_for(tmp_path, monkeypatch, "http://127.0.0.1:9/", cases=2)
    run = launch_run("demo", seams=seams(target_probe=probe_target))
    assert log.count("case") == 2 and run.stop_reason is None
    assert len(run.preflight_warnings) == 1 and "RuntimeError" in run.preflight_warnings[0]
    assert {v.result for v in store.load_verdicts(run.id)} == {Result.PASS}


def test_a_target_answering_500_runs_the_cases_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = wire_browser(monkeypatch)
    with responder(500) as stub:
        store = store_for(tmp_path, monkeypatch, stub.url, cases=2)
        run = launch_run("demo", seams=seams(target_probe=probe_target))
    assert log.count("case") == 2 and "start" in log
    assert run.preflight_warnings == [] and run.stop_reason is None
    assert {v.result for v in store.load_verdicts(run.id)} == {Result.PASS}


def test_the_probe_runs_once_per_run_not_per_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire_browser(monkeypatch)
    with responder(200) as stub:
        store_for(tmp_path, monkeypatch, stub.url, cases=3)
        launch_run("demo", seams=seams(target_probe=probe_target))
        assert len(stub.requests) == 1


def test_the_default_seam_reaches_the_probe_by_late_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`RunSeams()` carries a probe by default, so every launch path (button, schedule, queue)
    is guarded; the late binding is what lets the suite switch the network off in one place."""
    from autotester.schema.project import Project
    from autotester.stages.run_launcher import DEFAULT_SEAMS

    project = Project(slug="demo", name="Demo", base_url="https://demo.test")
    monkeypatch.setattr(reachability, "probe_target", lambda _project, _notes=None: "X")
    assert DEFAULT_SEAMS.target_probe(project, []) == "X"

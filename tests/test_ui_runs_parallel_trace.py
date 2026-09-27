"""AT-562/AT-564: the live run route wired to `run_cases` + `StageContext`.
Split from `test_ui_runs.py` at doctor's 300-line cap.

Before this unit, nothing in `src/` outside `stages/orchestrate*.py`
constructed a `StageContext`, and no live run path called
`stages.parallel_run.run_cases` -- so a real CLI/UI run wrote no
`trace.jsonl` and could never actually execute cases in parallel or record
`Run.parallel_n`/`parallel_bound_by`. These tests drive the REAL
`/projects/{slug}/run` route (fakes only for the browser and the grading
call) to prove that gap is closed. Contracts: qa/contracts/run-trace.md,
qa/contracts/parallel-run.md.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ui_runs import _onboard_demo, _only_run_id

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import SecretRef
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _non_entry_case(idx: int) -> Case:
    """A case whose first step does not navigate to the project's base_url --
    never mistaken for the dedicated-profile entry-screen case (AT-044)."""
    return Case(
        project="demo", flow_id=f"flow-{idx}", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title=f"case-{idx}", steps=[Step(order=1, action=Action.CLICK, target=f"#thing-{idx}")],
    )


def test_a_real_run_writes_a_trace_with_at_least_one_span(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-564: `trigger_run` must build a `StageContext` and write
    `trace.jsonl` for a real run -- before this unit, nothing in `src/`
    constructed a `StageContext` outside `stages/orchestrate*.py`, so this
    endpoint (the only real CLI/UI run path) wrote no trace at all."""
    from autotester.browser.session import BrowserSession
    from autotester.providers.mock import MockProvider

    _onboard_demo(client)
    store = ProjectStore("demo", scratch_root)
    store.add_case(_non_entry_case(0))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    judge = MockProvider(model="mock")

    def fake_run_and_grade_case_resilient(case_, session, judge_, run_id, store_):
        judge_.record(role="agent", input_tokens=3, output_tokens=3, fed_id=f"case-{case_.id}")
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", lambda: judge)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303

    run_id = _only_run_id(store)
    trace_path = store.paths.run_trace(run_id)
    assert trace_path.exists()
    lines = [json.loads(ln) for ln in trace_path.read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    assert len(lines) >= 1
    assert all(ln["trace_id"] == run_id for ln in lines)
    # the EXECUTE stage span _execute_with_trace itself records -- distinct
    # from the LLM-call span the fake grading call also leaves behind
    stage_spans = [ln for ln in lines if ln.get("kind") == "stage"]
    assert [s["stage"] for s in stage_spans] == ["execute"]
    assert stage_spans[0]["status"] == "done"


def test_a_declared_fake_secret_never_appears_raw_in_the_trace(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-564/AT-561: `StageContext` must be built with the project's real
    `SecretStore` (its `secrets=` param) -- without it, the auto-built trace
    degrades to an unredacted `Redactor({})` and a real secret value would
    reach `trace.jsonl` raw."""
    from autotester.browser.session import BrowserSession
    from autotester.providers.mock import MockProvider

    secret_value = "sk-fake-AT564-9f2c7a1b"
    (scratch_root / ".env").write_text(f"DEMO_FAKE_KEY={secret_value}\n", encoding="utf-8")

    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    project = store.load_project()
    assert project is not None
    store.save_project(project.model_copy(update={"secrets": [SecretRef(key="DEMO_FAKE_KEY")]}))
    store.add_case(_non_entry_case(0))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    judge = MockProvider(model="mock")

    def fake_run_and_grade_case_resilient(case_, session, judge_, run_id, store_):
        judge_.record(role="agent", input_tokens=3, output_tokens=3,
                      fed_id=f"leaked-{secret_value}")
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", lambda: judge)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303

    run_id = _only_run_id(store)
    raw = store.paths.run_trace(run_id).read_text(encoding="utf-8")
    assert secret_value not in raw
    assert "REDACTED" in raw


def test_run_records_parallel_n_and_bound_by_even_when_serial(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-562/PR1: every run must record its width and what bound it -- even
    the default (`max_parallel=1`) serial run, not only one that fans out."""
    from autotester.browser.session import BrowserSession

    _onboard_demo(client)
    store = ProjectStore("demo", scratch_root)
    store.add_case(_non_entry_case(0))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    def fake_run_and_grade_case_resilient(case_, session, judge_, run_id, store_):
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303

    run = store.load_run(_only_run_id(store))
    assert run is not None
    assert run.parallel_n == 1
    assert run.parallel_bound_by in ("config", "budget", "write_policy")


def test_with_max_parallel_2_two_cases_run_concurrently(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-562/PR1-PR2: configuring `max_parallel=2` must make the live route
    actually fan cases out through `run_cases`, each on its own isolated
    session (`default_session_factory`) -- not just record a wider N while
    still running everything one at a time."""
    from autotester.browser.session import BrowserSession

    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    project = store.load_project()
    assert project is not None
    store.save_project(project.model_copy(update={"max_parallel": 2}))
    store.add_case(_non_entry_case(0))
    store.add_case(_non_entry_case(1))

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    concurrent = [0]
    peak = [0]
    lock = threading.Lock()
    # AT-579: a Barrier, not a sleep, proves overlap -- it only releases when both
    # cases are in flight at once, so a loaded host cannot turn a real fan-out into
    # a serial-looking run (the 50 ms sleep did), and a serial run cannot pass (the
    # lone case waits out the timeout, errors, and peak stays 1).
    both_in_flight = threading.Barrier(2, timeout=10)

    def fake_run_and_grade_case_resilient(case_, session, judge_, run_id, store_):
        with lock:
            concurrent[0] += 1
            peak[0] = max(peak[0], concurrent[0])
        try:
            both_in_flight.wait()
        finally:
            # always leave, even when the barrier breaks: otherwise a serial run's
            # timed-out first case never decrements and the second case reads 2.
            with lock:
                concurrent[0] -= 1
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module

    # plan_parallel_run's OWN measurement (real RAM/CPU) is exercised by
    # test_parallel_run.py; this fakes only the PLAN so the wiring test is
    # deterministic on any host, never on live memory (same principle as
    # stages/parallel_run.py's own test suite).
    fake_plan = ParallelPlan(config_ceiling=2, measured_budget=2, n=2, bound_by="config",
                             free_ram_mb=99999.0, cpu_count=8)
    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)
    monkeypatch.setattr(routes_runs_module, "plan_parallel_run", lambda project_: fake_plan)

    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303
    assert peak[0] == 2

    run = store.load_run(_only_run_id(store))
    assert run is not None
    assert (run.parallel_n, run.parallel_bound_by) == (2, "config")

"""T-203: the Test button enqueues and returns at once; the runs page shows queued/running.

The queue gets a manual spawner (no threads, no sleeps): a job only runs when the test calls it.
Scenarios: a member presses Test on an idle project; a second member presses it while the first
run is still going; a member opens the report while a first-ever run is waiting.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval

from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore
from autotester.ui import run_queue
from autotester.ui.app import app


class _Provider:
    def available(self) -> bool:
        return True


@pytest.fixture
def held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, list[Callable[[], None]], list[str]]:
    """A project with one case, a queue that holds jobs, and a fake browser/grader."""
    import autotester.ui.routes_runs as routes_runs
    import autotester.ui.run_execution as run_execution
    from autotester.browser.session import BrowserSession
    from autotester.schema.case import Case

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    client = TestClient(app)
    client.post("/onboard", data={"slug": "demo", "name": "Demo",
                                  "base_url": "https://demo.test", "allowed_domains": "demo.test"})
    store = ProjectStore("demo", tmp_path)
    store.add_case(Case(project="demo", flow_id="flow-home", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="Homepage loads",
                        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")]))
    grant_live_case_approval(store, target=store.load_project().base_url)
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(routes_runs, "LangChainFallbackProvider", _Provider)
    ran: list[str] = []

    def fake(case_, session, judge, run_id, store_):
        ran.append(run_id)
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", fake)
    jobs: list[Callable[[], None]] = []
    monkeypatch.setattr(run_queue, "_QUEUE", run_queue.RunQueue(spawn=jobs.append))
    return client, jobs, ran


def test_pressing_test_returns_the_redirect_before_the_run_has_executed(held) -> None:
    client, jobs, ran = held
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/demo/report"
    assert ran == []             # nothing ran inside the request
    assert len(jobs) == 1        # the queue handed one worker its job
    jobs.pop()()                 # the worker thread would do this
    assert len(ran) == 1


def test_report_shows_running_then_done_with_a_link_to_the_run(held) -> None:
    client, jobs, ran = held
    client.post("/projects/demo/run", follow_redirects=False)
    first = client.get("/projects/demo/report").text   # no run.json yet, but the queue shows it
    assert "Run queue" in first and ">running</span>" in first
    jobs.pop()()
    page = client.get("/projects/demo/report").text
    assert f"/projects/demo/runs/{ran[0]}" in page
    assert "Run queue" in page


def test_a_second_press_while_a_run_is_going_shows_queued_and_runs_after(held) -> None:
    client, jobs, ran = held
    client.post("/projects/demo/run", follow_redirects=False)
    client.post("/projects/demo/run", follow_redirects=False)
    assert len(jobs) == 1                                  # single-flight: second is not started
    assert "queued (#1)" in client.get("/projects/demo/report").text
    jobs.pop()()                                           # first finishes -> second dispatched
    assert len(jobs) == 1
    jobs.pop()()
    assert len(ran) == 2 and ran[0] != ran[1]


def test_a_refused_press_never_reaches_the_queue(held) -> None:
    client, jobs, _ran = held
    response = client.post("/projects/nope/run", follow_redirects=False)
    assert response.status_code == 404
    assert jobs == [] and run_queue.get_queue().snapshot() == []


def test_panel_is_absent_for_a_project_that_was_never_queued(held) -> None:
    client, _jobs, _ran = held
    assert "Run queue" not in client.get("/projects/demo/report").text


def test_a_member_pressing_test_over_and_over_gets_a_429_with_the_reason(held) -> None:
    client, _jobs, _ran = held
    codes = [client.post("/projects/demo/run", follow_redirects=False).status_code
             for _ in range(5)]                  # 1 running + 3 waiting, then refused
    assert codes == [303, 303, 303, 303, 429]
    assert "already waiting" in client.post("/projects/demo/run").text


def test_credentials_deleted_while_waiting_refuse_the_run_at_start_without_a_browser(
    held, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HO19: the queue re-runs every gate at start; a run that waited is not exempt."""
    import autotester.ui.routes_runs as routes_runs

    client, jobs, ran = held
    client.post("/projects/demo/run", follow_redirects=False)

    class _Gone:
        def available(self) -> bool:
            return False

    monkeypatch.setattr(routes_runs, "LangChainFallbackProvider", _Gone)
    jobs.pop()()
    assert ran == []                             # no browser, no case executed
    page = client.get("/projects/demo/report").text
    assert "refused" in page and "no AI provider" in page


def test_a_second_run_plans_against_the_ram_the_first_one_already_holds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HO20: two runs that start together must not each assume the whole host is free."""
    import autotester.ui.routes_runs as routes_runs
    from autotester.schema.project import Project
    from autotester.stages.parallel_run import ParallelPlan

    seen: list[dict] = []

    def fake_plan(project, **kwargs):
        seen.append(kwargs)
        return ParallelPlan(2, 2, 2, "config", kwargs.get("free_ram_mb", 9000.0), 4)

    monkeypatch.setattr(routes_runs, "plan_parallel_run", fake_plan)
    monkeypatch.setattr(routes_runs, "_free_ram_mb", lambda: 9000.0)
    monkeypatch.setattr(run_queue, "_QUEUE", run_queue.RunQueue(spawn=lambda job: None))
    project = Project(slug="demo", name="Demo", base_url="https://demo.test",
                      allowed_domains=["demo.test"])
    routes_runs._plan_under_shared_budget(project, "run-a")     # nothing else running
    routes_runs._plan_under_shared_budget(project, "run-b")     # run-a holds 2 contexts
    assert seen[0] == {"video_enabled": True}                   # identical to the old call
    assert 0 < seen[1]["free_ram_mb"] < 9000.0


def test_a_run_that_crashes_inside_the_suite_queue_fails_the_test_that_started_it() -> None:
    """AT-845: tests/conftest.py runs queued jobs inline so old UI tests keep their meaning.
    The queue records a crash as `failed` and moves on, which let three of them stay green over
    a run that never worked; the inline queue must re-raise so such a test goes red."""
    queue = run_queue.get_queue()           # the autouse fixture's inline queue
    original = run_queue._runner

    def crashing(entry: object) -> None:
        raise RuntimeError("the browser never opened")

    run_queue.set_runner(crashing)
    try:
        with pytest.raises(RuntimeError, match="never opened"):
            queue.submit("alpha")
    finally:
        run_queue._runner = original


def test_a_gate_refusal_inside_the_suite_queue_is_not_an_error() -> None:
    """A member whose credentials were deleted is refused with a reason: normal, not a crash."""
    queue = run_queue.get_queue()
    original = run_queue._runner

    def refusing(entry: object) -> None:
        raise run_queue.RunRefused("credentials are missing")

    run_queue.set_runner(refusing)
    try:
        assert queue.submit("alpha").status is run_queue.QueueStatus.REFUSED
    finally:
        run_queue._runner = original

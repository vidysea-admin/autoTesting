"""AT-576: the serial route (`ui/routes_runs.py::_run_cases_serially`) must
run every entry case to completion -- its own dedicated session -- BEFORE
the shared session (reused across the run's ordinary cases) is ever
started. Fast, fake-session regression test for the ORDERING decision
itself; `test_ui_runs_serial_entry_mix_live.py` proves the real defect (two
live sync-Playwright drivers on one thread) that only a real browser can
reach -- a fake `BrowserSession.start` cannot see it, which is exactly why
AT-576 shipped undetected. Contract: qa/contracts/ui-run.md RU1-RU4.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ui_runs_parallel_trace import _non_entry_case, client, scratch_root
from test_ui_runs_serial_resilience import _entry_case

from autotester.schema.enums import Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore

__all__ = ["client", "scratch_root"]


def test_entry_cases_start_before_the_shared_session_starts(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run mixing one entry case with one ordinary case: the entry case's
    dedicated session (`ProjectPaths` slug `demo-entry-test`) must start
    before the shared session (slug `demo`) ever starts -- never the shared
    session first. Before the fix, the shared session started FIRST for any
    run with at least one non-entry case, which is the exact precondition
    that made a live entry case start a second sync Playwright driver while
    the shared one was still running (500)."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    store.add_case(_entry_case())
    store.add_case(_non_entry_case(0))

    starts: list[str] = []

    import autotester.ui.routes_runs as routes_runs_module
    from autotester.browser.session import BrowserSession

    def fake_start(self):  # records WHICH session started, in call order
        starts.append(self.paths.slug)
        return self

    monkeypatch.setattr(BrowserSession, "start", fake_start)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)

    import autotester.stages.run_case_pipeline as pipeline_module

    def fake_run_case(case_, session):
        return RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)

    def fake_grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    monkeypatch.setattr(pipeline_module, "run_case", fake_run_case)
    monkeypatch.setattr(pipeline_module, "grade", fake_grade)

    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    assert starts == ["demo-entry-test", "demo"], (
        f"the entry case's own session must start before the shared session: {starts}"
    )

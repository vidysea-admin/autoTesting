"""A launched run with fakes for the E4 tests: a project, N cases, a patched browser. Not a test.

`wired_run` builds an approved project whose `base_url` is whatever the test serves, N one-step
cases, and fakes the browser (`BrowserSession.start/close`), the entry-profile wipe and the
per-case run+grade, so `launch_run` exercises the real gates, budget, pool and saved `Run`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest
from run_approval_fixture import grant_live_case_approval

import autotester.ui.run_execution as run_execution
from autotester.browser.session import BrowserSession
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages import run_budget
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams
from autotester.store.project_store import ProjectStore


class Judge:
    trace = None

    def __init__(self, project: Project) -> None:
        self.project = project

    def available(self) -> bool:
        return True


def store_for(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base_url: str, *,
              cases: int = 1, wall_clock_s: float = 100_000.0,
              domain: str = "127.0.0.1") -> ProjectStore:
    """An approved project at `base_url` with `cases` distinct one-step navigate cases."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url=base_url,
                               allowed_domains=[domain]))
    grant_live_case_approval(store, target=base_url, wall_clock_s=wall_clock_s)
    for n in range(cases):
        store.add_case(Case(
            project="demo", flow_id=f"f{n}", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
            title=f"Case {n}", steps=[Step(order=1, action=Action.NAVIGATE,
                                           target=f"{base_url}p{n}")]))
    return store


def seams(**extra: object) -> RunSeams:
    return RunSeams(judge_factory=Judge, free_ram_mb=lambda: 16000.0,
                    planner=lambda project, **_kw: ParallelPlan(1, 1, 1, "config", 16000.0, 4),
                    **extra)


def wire_browser(monkeypatch: pytest.MonkeyPatch, *,
                 on_case: Callable[[], None] = lambda: None) -> list[str]:
    """Fake every browser touch; `on_case` runs inside each case (a clock jump, say).
    Returns the list that records one 'start' per browser launch and one 'case' per case run."""
    log: list[str] = []

    def graded(case, session, judge, run_id, store_):
        log.append("case")
        on_case()
        return (RawResult(case_id=case.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(BrowserSession, "start", lambda self: log.append("start") or self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "_wipe_entry_profile", lambda _p: None)
    monkeypatch.setattr(run_execution, "reset_to_logged_out", lambda _s: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", graded)
    return log


def fake_clock(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """`RunBudget`'s clock, injected: tests advance `.now` instead of sleeping."""
    clock = SimpleNamespace(now=1000.0)
    monkeypatch.setattr(run_budget, "time", SimpleNamespace(monotonic=lambda: clock.now))
    return clock

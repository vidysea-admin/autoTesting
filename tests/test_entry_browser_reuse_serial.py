"""D-115 (1): the serial run hands the entry login to the logged-in cases that follow it.

Umesh 2026-10-29: login once, use it, do not log out again and again. Fakes only.
Pins, through `_run_cases_serially` with ONE pool across tiers (as `run_cases_traced` runs it):
1 launch and 1 real login for the Pathlynks shape (empty submit, wrong password, happy login),
the lent session for logged-in cases, and the fallback to the shared profile when the login
did not pass.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from test_entry_browser_reuse import PROJECT, FakeSession, _case
from test_entry_browser_reuse_run import _Store, _wire

import autotester.ui.run_execution as run_execution
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Result
from autotester.schema.flowspec import Step


@pytest.fixture(autouse=True)
def _fresh_launches() -> None:
    FakeSession.launched = []


def _logged_in_case(n: int) -> Case:
    return Case(project="demo", flow_id="dash", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title=f"Dashboard {n}",
                steps=[Step(order=1, action=Action.CLICK, target=f"#tab-{n}")])


def _serial(cases: list[Case], flags: list[bool], events: list[str], tmp_path: Path,
            pool=None) -> None:
    secrets = SimpleNamespace(redactor=lambda: Redactor({}))
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    run_execution._run_cases_serially(
        cases, flags, PROJECT, secrets, tmp_path, SimpleNamespace(slug="demo"), "demo",
        SimpleNamespace(trace=None), "r1", _Store(events), budget=budget, pool=pool)


def test_logged_in_cases_run_in_the_login_session_without_a_reset_or_a_second_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    ran_in = _wire(monkeypatch, events)
    wrong, login = _case(1, klass=CaseClass.AUTH_WRONG_CREDS), _case(2)
    dash = [_logged_in_case(1), _logged_in_case(2)]
    _serial([login, wrong, *dash], [True, True, False, False], events, tmp_path)
    assert len(FakeSession.launched) == 1  # was 2: an entry launch plus the shared one
    entry = FakeSession.launched[0]
    assert all(ran_in[c.id] is entry for c in dash)  # the same logged-in browser
    assert entry.state.evidence_prefix == ""  # ordinary cases keep the shared-run layout
    assert events.count("reset") == 1  # only the login case needed a logged-out page
    assert events.index("run " + login.id) < events.index("run " + dash[0].id)
    assert events[-1] == "close" and events.count("close") == 1


def test_the_pathlynks_shape_is_one_launch_and_one_real_login_across_tiers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    _wire(monkeypatch, events)
    secrets = SimpleNamespace(redactor=lambda: Redactor({}))
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    judge = SimpleNamespace(trace=None)
    pool = run_execution._entry_pool(PROJECT, secrets, tmp_path, "demo", judge, budget)
    empty = _case(1, klass=CaseClass.INPUT_EMPTY, keys=())
    login, wrong = _case(2), _case(3, klass=CaseClass.AUTH_WRONG_CREDS)
    try:
        _serial([login, empty], [True, True], events, tmp_path, pool)  # static tier
        _serial([wrong], [True], events, tmp_path, pool)  # adversarial tier, later
    finally:
        pool.close()
    assert len(FakeSession.launched) == 1 and events.count("wipe") == 1
    assert events.count(f"run {login.id}") == 1  # one real login
    assert [e for e in events if e.startswith("run ")] == [
        f"run {empty.id}", f"run {login.id}", f"run {wrong.id}"]
    assert events.count("close") == 1  # one bounded close, when the run ends


def test_a_login_that_did_not_pass_falls_back_to_the_shared_profile_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    login, dash = _case(1), _logged_in_case(1)
    ran_in = _wire(monkeypatch, events, verdicts={login.id: Result.FAIL})
    _serial([login, dash], [True, False], events, tmp_path)
    assert len(FakeSession.launched) == 2  # the entry browser, then the shared one
    assert ran_in[dash.id] is FakeSession.launched[1]
    assert FakeSession.launched[0].closed  # one live driver at a time (AT-576)
    assert FakeSession.launched[1].log[0] == "start"


def test_without_a_pool_the_serial_run_owns_and_closes_its_entry_browser(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    _wire(monkeypatch, events)
    _serial([_case(1)], [True], events, tmp_path)
    assert FakeSession.launched[0].closed and events.count("close") == 1


def test_a_launched_run_shares_one_entry_browser_across_its_tiers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Through `launch_run`: a static and an adversarial entry case cost ONE launch (was 2)."""
    from test_run_teardown_stall_wiring import _demo_store, _Judge

    from autotester.browser.session import BrowserSession
    from autotester.schema.enums import Outcome
    from autotester.schema.run import RawResult
    from autotester.schema.verdict import Verdict
    from autotester.stages.parallel_run import ParallelPlan
    from autotester.stages.run_launcher import RunSeams, launch_run

    store = _demo_store(tmp_path, monkeypatch)
    store.add_case(Case(
        project="demo", flow_id="home", kind=CaseKind.WORST, case_class=CaseClass.SERVER_ERROR,
        title="Home survives a 500",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test")]))
    started, closed = [], []

    def graded(case, session, judge, run_id, store_):
        return (RawResult(case_id=case.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(BrowserSession, "start", lambda self: started.append(1) or self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: closed.append(1))
    monkeypatch.setattr(run_execution, "_wipe_entry_profile", lambda _p: None)
    monkeypatch.setattr(run_execution, "reset_to_logged_out", lambda _s: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", graded)
    seams = RunSeams(judge_factory=_Judge, free_ram_mb=lambda: 16000.0,
                     planner=lambda project, **_kw: ParallelPlan(1, 1, 1, "config", 16000.0, 4))

    run = launch_run("demo", seams=seams)

    assert len(store.load_results(run.id)) == 2
    assert len(started) == 1 and len(closed) == 1  # two tiers, one browser, one close

"""D-115 (1) fix cycle 2: the lent login session survives an errored ordinary case, and only the
project's own login account is ever lent (checker B: F1 blocking, W1).

Fakes only. F1: `note_shared` used to close the session `_run_normal_cases` was still running on,
so every case after one error died "session not started". The fake session here raises on any
use after `close()`, so a closed-while-in-use session fails these tests the way it failed a run.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from test_entry_browser_reuse import PROJECT, FakeSession, _case, _done, _pool
from test_entry_browser_reuse_run import _Store

import autotester.ui.run_execution as run_execution
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.ui.entry_browser import EntryBrowserPool, order_entry_cases


@pytest.fixture(autouse=True)
def _fresh_launches() -> None:
    FakeSession.launched = []


class _StrictSession(FakeSession):
    """A session that, like the real one, is unusable once closed; relaunch re-opens it."""

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self.paths = SimpleNamespace(profile_dir=Path("p"))
        self.relaunches = 0

    def use(self) -> None:
        if self.closed:
            raise RuntimeError("session not started")

    def relaunch(self, cause: BaseException) -> None:
        self.use()
        self.relaunches += 1


def _ordinary(n: int) -> Case:
    return _case(n, keys=()).model_copy(update={"id": f"plain-{n}", "title": f"Plain {n}"})


def _login_then_ordinary(monkeypatch, tmp_path, plan: dict[str, RawResult]):
    """A passed login lends its session; run `_run_normal_cases` over `plan` in it. Returns
    (pool, the lent session, {case id: result saved}, ids that ran)."""
    ran: list[str] = []
    saved: dict[str, Result] = {}
    store = _Store([])
    store.save_verdict = lambda run_id, verdict: saved.update({verdict.case_id: verdict.result})
    monkeypatch.setattr(run_execution, "BrowserSession", _StrictSession)
    monkeypatch.setattr(run_execution, "_wipe_entry_profile", lambda _p: None)
    monkeypatch.setattr(run_execution, "reset_to_logged_out", lambda _s: None)

    def graded(case, session, judge, run_id, store_):
        session.use()  # a closed session raises here, exactly like the real browser
        ran.append(case.id)
        result = plan.get(case.id) or RawResult(case_id=case.id, outcome=Outcome.COMPLETED)
        return result, Verdict(run_id=run_id, case_id=case.id, grader_provider="mock",
                               result=Result.INCONCLUSIVE if result.outcome is Outcome.ERRORED
                               else Result.PASS)

    monkeypatch.setattr(run_execution, "_run_and_grade_resilient", graded)
    secrets = SimpleNamespace(redactor=lambda: Redactor({}))
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    judge = SimpleNamespace(trace=None)
    pool = run_execution._entry_pool(PROJECT, secrets, tmp_path, "demo", judge, budget)
    login = _case(1)
    session = pool.acquire(login)
    pool.release(login, session, _done(login), passed=True)
    cases = [_ordinary(n) for n in range(1, 4)]
    run_execution._run_normal_cases(cases, pool, PROJECT, secrets, tmp_path,
                                    SimpleNamespace(slug="demo"), judge, "r1", store,
                                    budget=budget)
    return pool, session, saved, ran


def test_an_errored_ordinary_case_does_not_close_the_session_the_next_cases_still_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    plan = {"plain-1": RawResult(case_id="plain-1", outcome=Outcome.ERRORED, error="NavRefused")}
    pool, session, saved, ran = _login_then_ordinary(monkeypatch, tmp_path, plan)
    assert ran == ["plain-1", "plain-2", "plain-3"]  # the cases after the error still ran
    assert saved["plain-2"] is Result.PASS and saved["plain-3"] is Result.PASS
    assert not session.closed  # the loop does not close what the pool still owns
    assert pool.lend() is None  # but it is no longer trusted for a later tier
    pool.close()
    assert session.closed and session.log.count("close") == 1  # closed once, at the run's end


def test_a_closed_browser_case_is_relaunched_and_the_relaunched_session_stays_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    plan = {"plain-1": RawResult(case_id="plain-1", outcome=Outcome.ERRORED,
                                 error="TargetClosedError: Target page has been closed")}
    pool, session, saved, ran = _login_then_ordinary(monkeypatch, tmp_path, plan)
    assert session.relaunches == 1 and not session.closed
    assert ran == ["plain-1", "case-1", "plain-2", "plain-3"]  # case-1: the login replay (W3)
    assert saved["plain-1"] is Result.INCONCLUSIVE  # browser closed: the case tested nothing
    assert saved["plain-2"] is Result.PASS and saved["plain-3"] is Result.PASS
    pool.close()
    assert session.log.count("close") == 1


def test_noting_an_errored_shared_case_never_closes_the_session() -> None:
    pool = _pool()
    login = _case(1)
    session = pool.acquire(login)
    pool.release(login, session, _done(login), passed=True)
    assert pool.lend() is session
    pool.note_shared(_done(_case(9), Outcome.ERRORED, "boom"))
    assert not session.closed and pool.lend() is None
    pool.close()
    assert session.closed


# --- W1: only the project's login account is lent -------------------------------------------

ACCOUNT_A = ("USER_A", "PASS_A")
ACCOUNT_B = ("USER_B", "PASS_B")


def _project(login_case_id: str) -> Project:
    return PROJECT.model_copy(update={"login_case_id": login_case_id})


def _account_pool(project: Project) -> EntryBrowserPool:
    return EntryBrowserPool(project, open_session=lambda case: FakeSession().start(),
                            reset=lambda session, case: session.log.append("reset"))


def _run_in_order(pool: EntryBrowserPool, cases: list[Case], project: Project) -> None:
    for case in order_entry_cases(cases, project):
        session = pool.acquire(case)
        pool.release(case, session, _done(case), passed=True)


def test_the_project_login_case_runs_last_and_its_account_is_the_one_lent() -> None:
    login_a = _case(1, keys=ACCOUNT_A)
    other_b = _case(2, keys=ACCOUNT_B)
    wrong_a = _case(3, klass=CaseClass.AUTH_WRONG_CREDS, keys=("USER_A",))
    project = _project(login_a.id)
    cases = [login_a, other_b, wrong_a]
    ordered = order_entry_cases(cases, project)
    assert [c.id for c in ordered] == [wrong_a.id, other_b.id, login_a.id]
    pool = _account_pool(project)
    _run_in_order(pool, cases, project)
    lent = pool.lend()
    assert lent is not None and lent.state.evidence_prefix == login_a.id  # A's, never B's


def test_another_accounts_passed_login_is_not_lent_when_the_project_names_its_login() -> None:
    login_a, other_b = _case(1, keys=ACCOUNT_A), _case(2, keys=ACCOUNT_B)
    pool = _account_pool(_project(login_a.id))
    session = pool.acquire(other_b)
    pool.release(other_b, session, _done(other_b), passed=True)
    assert pool.lend() is None  # B logged in, but the ordinary cases belong to A


def test_a_run_without_the_project_login_case_lends_nothing() -> None:
    other_b = _case(2, keys=ACCOUNT_B)
    pool = _account_pool(_project("not-in-this-run"))
    session = pool.acquire(other_b)
    pool.release(other_b, session, _done(other_b), passed=True)
    assert pool.lend() is None  # identity cannot be confirmed: fall back to the shared profile


# --- checker B cycle-2 W3: a relaunch of the lent session loses the login ----------------------

_CLOSED = RawResult(case_id="plain-1", outcome=Outcome.ERRORED,
                    error="TargetClosedError: Target page has been closed")


def test_a_relaunched_lent_session_replays_the_login_before_the_next_ordinary_case(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pool, session, saved, ran = _login_then_ordinary(monkeypatch, tmp_path, {"plain-1": _CLOSED})
    # the login case (case-1) ran again right after the relaunch, before plain-2 and plain-3
    assert ran == ["plain-1", "case-1", "plain-2", "plain-3"]
    assert session.relaunches == 1 and not session.closed
    assert saved["plain-2"] is Result.PASS and saved["plain-3"] is Result.PASS
    assert "case-1" not in saved  # the replay is not a second result for the login case
    assert session.state.evidence_prefix == ""  # ordinary cases keep the shared-run layout
    assert pool.lend() is session  # still a logged-in session
    pool.close()


def test_a_login_replay_that_fails_stops_the_tier_with_a_named_reason_not_a_logged_out_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    errors: dict[str, str | None] = {}
    monkeypatch.setattr(run_execution, "grade_errored_result", lambda case, result, judge, run_id,
                        store: Verdict(run_id=run_id, case_id=case.id, grader_provider="mock",
                                       result=Result.INCONCLUSIVE))
    monkeypatch.setattr(_Store, "save_result",
                        lambda self, run_id, r: errors.update({r.case_id: r.error}), raising=False)
    bad_login = RawResult(case_id="case-1", outcome=Outcome.ERRORED, error="login page changed")
    pool, _session, saved, ran = _login_then_ordinary(
        monkeypatch, tmp_path, {"plain-1": _CLOSED, "case-1": bad_login})
    assert ran == ["plain-1", "case-1"]  # plain-2 and plain-3 never ran logged out
    assert saved["plain-2"] is Result.INCONCLUSIVE and saved["plain-3"] is Result.INCONCLUSIVE
    for case_id in ("plain-2", "plain-3"):
        assert "login was lost" in (errors[case_id] or "") and "case-1" in (errors[case_id] or "")
    assert pool.lend() is None  # not trusted for a later tier either
    pool.close()


def test_relogin_resets_the_relaunched_browser_first_and_marks_it_logged_in_again() -> None:
    resets: list[str] = []
    pool = _pool(resets)
    login = _case(1)
    session = pool.acquire(login)
    pool.release(login, session, _done(login), passed=True)
    resets.clear()
    ran: list[tuple[str, str]] = []

    def grade(case: Case, sess: object) -> Verdict:
        ran.append((case.id, sess.state.evidence_prefix))
        return Verdict(run_id="r", case_id=case.id, grader_provider="mock", result=Result.PASS)

    assert pool.relogin(grade) is None
    assert resets == ["reset"] and ran == [("case-1", "case-1-relogin")]
    assert pool.lend() is session and session.state.evidence_prefix == ""


def test_relogin_leaves_the_screenshot_counter_where_the_ordinary_cases_had_it() -> None:
    """Checker B cycle-0 F1: the replay numbers its files under `<id>-relogin/`, so the lent
    session's running count must come back, or the next ordinary case overwrites earlier ones."""
    pool = _pool()
    login = _case(1)
    session = pool.acquire(login)
    pool.release(login, session, _done(login), passed=True)
    session.state.screenshots = 6  # ordinary cases already wrote 6 screenshots in the run root

    def grade(case: Case, sess: object) -> Verdict:
        assert sess.state.screenshots == 0  # the replay's own files start from 01 under its prefix
        sess.state.screenshots = 2
        return Verdict(run_id="r", case_id=case.id, grader_provider="mock", result=Result.PASS)

    assert pool.relogin(grade) is None
    assert session.state.screenshots == 6 and session.state.evidence_prefix == ""


def test_a_failed_replay_also_restores_the_screenshot_counter() -> None:
    pool = _pool()
    login = _case(1)
    session = pool.acquire(login)
    pool.release(login, session, _done(login), passed=True)
    session.state.screenshots = 6

    def grade(case: Case, sess: object) -> Verdict:
        sess.state.screenshots = 1
        raise RuntimeError("login page changed")

    assert "login page changed" in (pool.relogin(grade) or "")
    assert session.state.screenshots == 6


def test_relogin_with_no_remembered_login_case_names_the_reason() -> None:
    pool = _pool()
    reason = pool.relogin(lambda case, sess: pytest.fail("nothing to replay"))
    assert reason is not None and "login was lost" in reason

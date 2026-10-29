"""relogin-reset-fallback (checker B observation O1 of entry-reset-cache-relogin).

When the logged-out reset raises inside `EntryBrowserPool.relogin` (the HTTP cache cannot be
cleared), the tier used to stop. It now falls back the way `acquire` does: discard the browser,
launch ONE fresh wiped one, replay the login once in it. Bounded: one fallback per relogin, charged
against the tier's relaunch cap; a fallback that fails keeps the named-reason stop.

Fakes only -- no browser, no network.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

import pytest
from test_entry_browser_reuse import FakeSession, _case, _done, _pool
from test_entry_browser_reuse_lent import _CLOSED, _login_then_ordinary

import autotester.ui.run_execution as run_execution
from autotester.schema.case import Case
from autotester.schema.enums import Result
from autotester.schema.verdict import Verdict
from autotester.stages.browser_recovery import BrowserRecovery
from autotester.ui.entry_browser import EntryBrowserPool


@pytest.fixture(autouse=True)
def _fresh_launches() -> None:
    FakeSession.launched = []


def _passing(ran: list[tuple[str, str, FakeSession]]):
    def grade(case: Case, sess: FakeSession) -> Verdict:
        ran.append((case.id, sess.state.evidence_prefix, sess))
        return Verdict(run_id="r", case_id=case.id, grader_provider="mock", result=Result.PASS)
    return grade


def _lent_pool(**kw) -> tuple[EntryBrowserPool, FakeSession]:
    pool = _pool(reset_raises=True, **kw)
    login = _case(1)
    session = pool.acquire(login)  # a fresh launch: nothing to reset
    pool.release(login, session, _done(login), passed=True)
    return pool, session


def test_a_failed_reset_falls_back_to_one_fresh_launch_and_replays_the_login_there() -> None:
    pool, old = _lent_pool()
    old.state.screenshots = 6
    ran: list[tuple[str, str, FakeSession]] = []
    assert pool.relogin(_passing(ran)) is None
    assert len(FakeSession.launched) == 2 and old.closed  # the old one discarded, one new launch
    fresh = FakeSession.launched[1]
    assert [(c, p) for c, p, _s in ran] == [("case-1", "case-1-relogin")]
    assert ran[0][2] is fresh  # the replay ran in the fresh wiped browser, not the old one
    assert pool.lend() is fresh and not fresh.closed
    assert fresh.state.evidence_prefix == "" and fresh.state.screenshots == 6
    assert pool.live() is fresh
    pool.close()


def test_a_fallback_replay_that_does_not_pass_keeps_the_named_reason_and_does_not_loop() -> None:
    pool, old = _lent_pool()
    seen: list[str] = []

    def grade(case: Case, sess: FakeSession) -> Verdict:
        seen.append(case.id)
        return Verdict(run_id="r", case_id=case.id, grader_provider="mock", result=Result.FAIL)

    reason = pool.relogin(grade)
    assert reason is not None and "login was lost" in reason and "case-1" in reason
    assert "did not pass" in reason and "remaining cases not run" in reason
    assert seen == ["case-1"] and len(FakeSession.launched) == 2  # one replay, one fallback only
    assert pool.lend() is None and old.closed
    pool.close()


def test_a_relaunch_the_tier_may_not_spend_keeps_the_existing_stop_without_a_launch() -> None:
    pool, old = _lent_pool()
    reason = pool.relogin(lambda c, s: pytest.fail("no replay"), may_relaunch=lambda: False)
    assert reason is not None and "login was lost" in reason
    assert "page crashed during reset" in reason  # why: the reset failure is named
    assert len(FakeSession.launched) == 1 and not old.closed and pool.lend() is None
    pool.close()


def test_a_fallback_launch_that_itself_fails_is_named_not_raised() -> None:
    calls: list[int] = []

    def open_session(case: Case) -> FakeSession:
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("chromium would not start")
        return FakeSession().start()

    def reset(session: FakeSession, case: Case) -> None:
        raise RuntimeError("cache clear boom")

    pool = EntryBrowserPool(_pool().project, open_session=open_session, reset=reset)
    login = _case(1)
    session = pool.acquire(login)
    pool.release(login, session, _done(login), passed=True)
    reason = pool.relogin(lambda c, s: pytest.fail("no browser to replay in"))
    assert reason is not None and "chromium would not start" in reason and len(calls) == 2
    assert pool.lend() is None
    pool.close()


def _boom(_session: object) -> None:
    raise RuntimeError("cache clear boom")


def test_the_tier_loop_switches_to_the_fresh_browser_after_the_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pool, _old, saved, ran = _login_then_ordinary(monkeypatch, tmp_path, {"plain-1": _CLOSED},
                                                  reset=_boom)
    # the next ordinary cases ran in the fresh browser (a closed one raises "session not started")
    assert ran == ["plain-1", "case-1", "plain-2", "plain-3"]
    assert saved["plain-2"] is Result.PASS and saved["plain-3"] is Result.PASS
    assert "case-1" not in saved  # the replay is still not a second result
    assert pool.lend() is pool.live() and not pool.live().closed
    assert len(FakeSession.launched) == 2  # the lent one and exactly one fresh launch
    pool.close()


def test_the_fallback_launch_counts_against_the_tiers_relaunch_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(run_execution, "BrowserRecovery",
                        partial(BrowserRecovery, max_relaunches=1))
    monkeypatch.setattr(run_execution, "grade_errored_result", lambda case, result, judge, run_id,
                        store: Verdict(run_id=run_id, case_id=case.id, grader_provider="mock",
                                       result=Result.INCONCLUSIVE))
    pool, session, saved, ran = _login_then_ordinary(monkeypatch, tmp_path, {"plain-1": _CLOSED},
                                                     reset=_boom)
    assert ran == ["plain-1"]  # the one allowed relaunch was spent on the closed case
    assert saved["plain-2"] is Result.INCONCLUSIVE and saved["plain-3"] is Result.INCONCLUSIVE
    assert len(FakeSession.launched) == 1 and not session.closed  # no extra launch past the cap
    assert pool.lend() is None
    pool.close()

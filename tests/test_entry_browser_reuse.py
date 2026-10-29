"""D-115 (1): the entry browser pool (entry-browser-reuse): reuse, isolation, crash recovery.
The reset and the run wiring are in `test_entry_browser_reuse_run.py`.

Fakes only -- no browser, no network. A fake session counts launches, resets and closes, so the
tests pin: how many Chromium launches a run costs, that every reused case starts logged out
(a login case after a logged-in case still proves login), that a different identity, a
logged-out or an adversarial case gets its own browser, that a crashed case never poisons the
next, and that a graded case is saved before any teardown.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar

import pytest

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.ui.entry_browser import EntryBrowserPool, context_key

BASE = "https://demo.test"
PROJECT = Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["demo.test"])


def _case(n: int, *, klass: CaseClass = CaseClass.HAPPY, keys: tuple[str, ...] = ("USER",),
          preconditions: list[str] | None = None) -> Case:
    steps = [Step(order=1, action=Action.NAVIGATE, target=BASE)]
    for i, key in enumerate(keys, start=2):
        steps.append(Step(order=i, action=Action.FILL, target="input",
                          value="{{SECRET:" + key + "}}"))
    return Case(id=f"case-{n}", project="demo", flow_id="login", kind=CaseKind.BEST,
                case_class=klass, title=f"Case {n}", steps=steps,
                preconditions=preconditions or [])


class FakeSession:
    """Stands in for `BrowserSession`; every instance is one Chromium launch."""

    launched: ClassVar[list[FakeSession]] = []

    def __init__(self, *_a, **_k) -> None:
        self.state = SimpleNamespace(evidence_prefix="", screenshots=7, secret_locators=["x"],
                                     hitl="stale")
        self.budget = None
        self.trace = None
        self.log: list[str] = []
        self.closed = False
        FakeSession.launched.append(self)

    def start(self) -> FakeSession:
        self.log.append("start")
        return self

    def close(self) -> None:
        self.log.append("close")
        self.closed = True


@pytest.fixture(autouse=True)
def _fresh_launches() -> None:
    FakeSession.launched = []


def _pool(resets: list[str] | None = None, *, reset_raises: bool = False) -> EntryBrowserPool:
    def reset(session: FakeSession, case: Case) -> None:
        session.log.append("reset")
        if resets is not None:
            resets.append("reset")
        if reset_raises:
            raise RuntimeError("page crashed during reset")
    return EntryBrowserPool(PROJECT, open_session=lambda case: FakeSession().start(), reset=reset)


def _done(case: Case, outcome: Outcome = Outcome.COMPLETED, error: str | None = None) -> RawResult:
    return RawResult(case_id=case.id, outcome=outcome, error=error)


# --- the pool: reuse ------------------------------------------------------------------------

def test_cases_with_one_identity_share_one_browser_and_reset_before_each_reuse() -> None:
    pool, cases = _pool(), [_case(i) for i in range(4)]
    for case in cases:
        session = pool.acquire(case)
        pool.release(case, session, _done(case))
    pool.close()
    assert len(FakeSession.launched) == 1  # was 4 launches (one per entry case)
    only = FakeSession.launched[0]
    assert only.log == ["start", "reset", "reset", "reset", "close"]  # no reset on a fresh launch
    assert only.closed


def test_per_case_state_is_clean_and_evidence_is_nested_under_the_case() -> None:
    pool = _pool()
    first, second = _case(1), _case(2)
    session = pool.acquire(first)
    assert (session.state.evidence_prefix, session.state.screenshots) == ("case-1", 0)
    session.state.screenshots, session.state.secret_locators = 3, ["#pw"]
    pool.release(first, session, _done(first))
    again = pool.acquire(second)
    assert again is session
    assert again.state.evidence_prefix == "case-2" and again.state.screenshots == 0
    assert again.state.secret_locators == [] and again.state.hitl is None


def test_a_login_case_after_a_logged_in_case_is_reset_to_logged_out_first() -> None:
    order: list[str] = []
    pool = _pool(order)
    login_a, login_b = _case(1), _case(2)
    session = pool.acquire(login_a)
    order.append("case-1 runs and ends logged in")
    pool.release(login_a, session, _done(login_a))
    pool.acquire(login_b)
    order.append("case-2 runs")
    assert order == ["case-1 runs and ends logged in", "reset", "case-2 runs"]


def test_credential_free_cases_join_whatever_identity_the_browser_serves() -> None:
    pool = _pool()
    plain, user, other_plain = _case(1, keys=()), _case(2), _case(3, keys=())
    for case in (plain, user, other_plain):
        pool.release(case, pool.acquire(case), _done(case))
    pool.close()
    assert len(FakeSession.launched) == 1


# --- the pool: isolation --------------------------------------------------------------------

def test_a_different_identity_gets_its_own_browser() -> None:
    pool = _pool()
    student, counsellor = _case(1, keys=("STUDENT",)), _case(2, keys=("COUNSELLOR",))
    first = pool.acquire(student)
    pool.release(student, first, _done(student))
    second = pool.acquire(counsellor)
    assert second is not first and first.closed and len(FakeSession.launched) == 2
    assert "reset" not in second.log  # a fresh launch, not a reset


@pytest.mark.parametrize("make", [
    lambda n: _case(n, klass=CaseClass.AUTH_WRONG_CREDS),
    lambda n: _case(n, klass=CaseClass.SERVER_ERROR),
    lambda n: _case(n, klass=CaseClass.DEEPLINK_UNAUTH),
    lambda n: _case(n, preconditions=["user is logged out"]),
])
def test_adversarial_and_logged_out_cases_get_their_own_browser_closed_straight_after(
    make,
) -> None:
    pool = _pool()
    plain, special, after = _case(1), make(2), _case(3)
    s1 = pool.acquire(plain)
    pool.release(plain, s1, _done(plain))
    s2 = pool.acquire(special)
    assert s2 is not s1 and s1.closed  # not reused, and the shared one made way for it
    pool.release(special, s2, _done(special))
    assert s2.closed  # its own browser dies with it, never carried to a neighbour
    s3 = pool.acquire(after)
    assert s3 is not s2 and len(FakeSession.launched) == 3


def test_context_key_is_none_for_isolated_cases_and_the_sorted_secret_keys_otherwise() -> None:
    assert context_key(_case(1, keys=("B", "A"))) == "A,B"
    assert context_key(_case(1, keys=())) == ""
    assert context_key(_case(1, klass=CaseClass.AUTH_EXPIRED_SESSION)) is None
    assert context_key(_case(1, klass=CaseClass.DEEPLINK_UNAUTH)) is None


# --- the pool: a crash never poisons the next case ------------------------------------------

@pytest.mark.parametrize("outcome,error", [
    (Outcome.ERRORED, "Locator.click: Timeout 30000ms exceeded"),
    (Outcome.ERRORED, "Target page, context or browser has been closed"),
])
def test_an_errored_case_discards_the_browser_so_the_next_case_gets_a_fresh_one(
    outcome: Outcome, error: str,
) -> None:
    pool = _pool()
    crashed, next_case = _case(1), _case(2)
    s1 = pool.acquire(crashed)
    pool.release(crashed, s1, _done(crashed, outcome, error))
    assert s1.closed
    s2 = pool.acquire(next_case)
    assert s2 is not s1 and not s2.closed and "reset" not in s2.log


def test_a_latched_restore_error_discards_the_browser() -> None:
    pool = _pool()
    case = _case(1)
    session = pool.acquire(case)
    session._restore_error = "browser session died; relaunch limit reached"
    pool.release(case, session, _done(case))
    assert session.closed and pool.acquire(_case(2)) is not session


def test_a_failed_reset_falls_back_to_a_fresh_launch_once() -> None:
    pool = _pool(reset_raises=True)
    a, b = _case(1), _case(2)
    s1 = pool.acquire(a)
    pool.release(a, s1, _done(a))
    s2 = pool.acquire(b)
    assert s2 is not s1 and s1.closed and not s2.closed
    assert len(FakeSession.launched) == 2


def test_close_is_idempotent_and_a_close_error_is_swallowed() -> None:
    pool = _pool()
    case = _case(1)
    session = pool.acquire(case)
    session.close = lambda: (_ for _ in ()).throw(RuntimeError("hung driver"))  # type: ignore
    pool.release(case, session, _done(case))
    pool.close()
    pool.close()

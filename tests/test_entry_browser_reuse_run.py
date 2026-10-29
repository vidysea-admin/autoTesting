"""D-115 (1): the entry-browser reset and `ui/run_execution.py` wiring (entry-browser-reuse).

Fakes only -- no browser, no network. Pins the logged-out reset between two entry cases and the
launch / wipe / save / close counts of a run's entry leg; the pool rules are in
`test_entry_browser_reuse.py`.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from test_entry_browser_reuse import BASE, PROJECT, FakeSession, _case

import autotester.ui.run_execution as run_execution
from autotester.browser.entry_reset import reset_to_logged_out
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict


@pytest.fixture(autouse=True)
def _fresh_launches() -> None:
    FakeSession.launched = []


# --- the reset ------------------------------------------------------------------------------

class _Ctx:
    def __init__(self, log: list[str], pages: list[object]) -> None:
        self.log, self.pages = log, pages

    def clear_cookies(self) -> None:
        self.log.append("clear_cookies")

    def storage_state(self, **_kw) -> dict:
        return {"cookies": [], "origins": [{"origin": SSO, "localStorage": []}]}

    def new_cdp_session(self, _page):
        return SimpleNamespace(send=lambda m, a: self.log.append(f"cdp {m} {a['origin']}"),
                               detach=lambda: None)


SSO = "https://sso.demo.test"  # a second origin the previous case held web storage for


class _Page:
    def __init__(self, log: list[str], name: str) -> None:
        self.log, self.name = log, name

    def close(self) -> None:
        self.log.append(f"close {self.name}")


def _reset_session(log: list[str], *, cdp_ok: bool = True):
    keep, extra = _Page(log, "keep"), _Page(log, "popup")
    ctx = _Ctx(log, [keep, extra])
    if not cdp_ok:
        ctx.new_cdp_session = lambda _p: (_ for _ in ()).throw(RuntimeError("no cdp"))
    page = SimpleNamespace(
        evaluate=lambda js: log.append("evaluate storage"), url=BASE + "/signin")
    session = SimpleNamespace(
        project=PROJECT, _context=ctx, _page=keep, goto=lambda url: log.append(f"goto {url}"),
        page=page)
    return session


def test_reset_closes_stray_pages_clears_cookies_and_storage_then_lands_on_the_start_url() -> None:
    log: list[str] = []
    reset_to_logged_out(_reset_session(log))
    assert log == [
        "close popup", "clear_cookies", f"goto {BASE}",
        f"cdp Storage.clearDataForOrigin {BASE}",
        f"cdp Storage.clearDataForOrigin {SSO}",  # W1: every origin the context holds storage for
        "evaluate storage",  # F1: CDP has no sessionStorage type; the page clear always runs
        f"goto {BASE}",  # and the app then starts from the cleared state
    ]


def test_reset_still_clears_page_storage_when_the_devtools_clear_is_unavailable() -> None:
    log: list[str] = []
    reset_to_logged_out(_reset_session(log, cdp_ok=False))
    assert log[-2:] == ["evaluate storage", f"goto {BASE}"] and "clear_cookies" in log


def test_reset_fails_closed_when_the_page_storage_clear_fails() -> None:
    log: list[str] = []
    session = _reset_session(log)

    def broken(js: str) -> None:
        raise RuntimeError("page crashed")
    session.page.evaluate = broken
    with pytest.raises(RuntimeError, match="page crashed"):
        reset_to_logged_out(session)  # the pool then discards the browser (fail closed)


def test_reset_goes_through_the_session_so_allowed_domains_scoping_applies() -> None:
    # `session.goto` is the one navigation entry that runs `check_destination` (B6): a base_url
    # outside the allowed domains is refused there, and the reset surfaces it, never bypasses it
    log: list[str] = []
    session = _reset_session(log)

    def refuse(url: str) -> None:
        raise RuntimeError("outside allowed domains")
    session.goto = refuse
    with pytest.raises(RuntimeError, match="allowed domains"):
        reset_to_logged_out(session)


# --- run_execution wiring -------------------------------------------------------------------

def _wire(monkeypatch: pytest.MonkeyPatch, events: list[str],
          outcomes: dict[str, RawResult] | None = None,
          verdicts: dict[str, Result] | None = None) -> dict[str, object]:
    """Fake the browser and the grader; returns {case id: the session it ran in}."""
    ran_in: dict[str, object] = {}
    class Session(FakeSession):
        def __init__(self, *a, **k) -> None:
            super().__init__(*a, **k)
            self.paths = SimpleNamespace(profile_dir=Path("p"))

        def close(self) -> None:
            events.append("close")
            super().close()

    def graded(case, session, judge, run_id, store):
        events.append(f"run {case.id}")
        ran_in[case.id] = session
        result = (outcomes or {}).get(case.id) or RawResult(case_id=case.id,
                                                            outcome=Outcome.COMPLETED)
        return result, Verdict(run_id=run_id, case_id=case.id, grader_provider="mock",
                               result=(verdicts or {}).get(case.id, Result.PASS))

    monkeypatch.setattr(run_execution, "BrowserSession", Session)
    monkeypatch.setattr(run_execution, "_wipe_entry_profile", lambda _p: events.append("wipe"))
    monkeypatch.setattr(run_execution, "_run_and_grade_resilient", graded)
    monkeypatch.setattr(run_execution, "reset_to_logged_out",
                        lambda session: events.append("reset"))
    return ran_in


class _Store:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def save_result(self, run_id, result) -> None:
        self.events.append(f"save {result.case_id}")

    def save_verdict(self, run_id, verdict) -> None:
        pass


def _run_entry(cases: list[Case], events: list[str], tmp_path: Path) -> None:
    secrets = SimpleNamespace(redactor=lambda: Redactor({}))
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    judge = SimpleNamespace(trace=None)
    pool = run_execution._entry_pool(PROJECT, secrets, tmp_path, "demo", judge, budget)
    try:
        run_execution._run_entry_cases(cases, PROJECT, secrets, tmp_path, "demo", judge, "r1",
                                       _Store(events), budget=budget, pool=pool)
    finally:
        pool.close()


def test_six_entry_cases_of_one_identity_cost_one_launch_one_wipe_one_close(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    _wire(monkeypatch, events)
    _run_entry([_case(i) for i in range(6)], events, tmp_path)
    assert len(FakeSession.launched) == 1  # before this unit: 6
    assert events.count("wipe") == 1 and events.count("close") == 1
    assert events[-1] == "close"  # one bounded close, at the very end
    saves = [i for i, e in enumerate(events) if e.startswith("save ")]
    assert len(saves) == 6 and max(saves) < events.index("close")  # every case saved before it


def test_wrong_credentials_and_empty_submit_share_the_browser_and_login_runs_last(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    _wire(monkeypatch, events)
    login, wrong = _case(0), _case(1, klass=CaseClass.AUTH_WRONG_CREDS)
    empty = _case(2, klass=CaseClass.INPUT_EMPTY, keys=())
    _run_entry([login, wrong, empty], events, tmp_path)
    assert [e for e in events if e.startswith("run ")] == [
        f"run {wrong.id}", f"run {empty.id}", f"run {login.id}"]
    assert len(FakeSession.launched) == 1 and events.count("wipe") == 1
    assert events.count("reset") == 2  # logged out before the 2nd and 3rd; none before the 1st


def test_a_case_that_crashes_before_a_result_is_errored_and_the_next_case_still_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    _wire(monkeypatch, events)

    def boom(case, session, judge, run_id, store):
        events.append(f"run {case.id}")
        if case.id == "case-0":
            raise RuntimeError("renderer crashed")
        return (RawResult(case_id=case.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(run_execution, "_run_and_grade_resilient", boom)
    monkeypatch.setattr(run_execution, "grade_errored_result",
                        lambda case, result, *a, **k: Verdict(
                            run_id="r1", case_id=case.id, result=Result.INCONCLUSIVE,
                            grader_provider="rule"))
    _run_entry([_case(0), _case(1)], events, tmp_path)
    assert events.count("save case-0") == 1 and events.count("save case-1") == 1
    assert len(FakeSession.launched) == 2  # the crashed browser was discarded, not reused
    assert FakeSession.launched[0].closed and FakeSession.launched[1].closed


def test_a_single_entry_case_still_launches_saves_then_closes_its_own_browser(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    _wire(monkeypatch, events)
    secrets = SimpleNamespace(redactor=lambda: Redactor({}))
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    run_execution._run_entry_case(_case(0), PROJECT, secrets, tmp_path, "demo",
                                  SimpleNamespace(trace=None), "r1", _Store(events),
                                  budget=budget)
    assert events == ["wipe", "run case-0", "save case-0", "close"]

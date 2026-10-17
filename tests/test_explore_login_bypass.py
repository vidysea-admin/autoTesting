"""AT-226: an already-authenticated session must not abort the crawl.

A persistent Chromium profile can hold a live session from a prior run, in
which case the login page itself redirects away before the login case's own
form-fill step ever finds a field to fill. `_bootstrap_login` must notice the
redirect and skip the case rather than let `run_case` block on a field that
will never appear. Contract: qa/contracts/explore.md (login bootstrap, X10).
"""

from __future__ import annotations

from pathlib import Path

from crawl_fake import BASE, grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, CrawlStatus
from autotester.schema.flowspec import Step
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

SIGNIN = "https://app.test/signin"
IDENTIFIER = "input[name='identifier']"


def _login_case(target: str = SIGNIN) -> Case:
    """A NAVIGATE then a FILL, exactly the shape that timed out in AT-226's
    real crawl (`Locator.evaluate: Timeout ... input[name="identifier"]`)."""
    return Case(
        project="demo", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="log in", steps=[
            Step(order=1, action=Action.NAVIGATE, target=target),
            Step(order=2, action=Action.FILL, target=IDENTIFIER, value="someone"),
        ],
    )


def test_a_redirect_away_from_the_login_page_is_treated_as_already_authenticated(
    tmp_path: Path,
) -> None:
    project = make_project()
    session, page = make_session(tmp_path, project)
    page.redirects[SIGNIN] = BASE
    # The field only "exists" at /signin -- the page it redirects to (BASE)
    # never renders it, exactly like the real Pathlynks dashboard did not.
    page.fillable[SIGNIN] = {IDENTIFIER}
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())
    assert crawl.status is CrawlStatus.COMPLETED
    assert crawl.stop_reason == "frontier empty"


def test_a_login_page_that_does_not_redirect_still_runs_the_case(tmp_path: Path) -> None:
    project = make_project()
    session, page = make_session(tmp_path, project)
    page.fillable[SIGNIN] = {IDENTIFIER}
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())
    # No redirect was staged, so the login page genuinely held and the FILL
    # step succeeds there -- the case runs to completion as normal.
    assert crawl.status is CrawlStatus.COMPLETED
    assert crawl.stop_reason == "frontier empty"
    # AT-274: crawl.status/stop_reason alone cannot tell "the case genuinely
    # ran" apart from "the case was skipped by an always-skip regression" --
    # a checker sabotage (_already_past_login -> unconditional True) left
    # this test green with the login case never touched. Assert the FILL
    # step's own side effect happened, on the exact selector/value the case
    # names, so an always-skip mutation fails here.
    assert (IDENTIFIER, "someone") in page.fills


def test_a_login_case_with_no_navigate_step_falls_back_to_running_it(
    tmp_path: Path,
) -> None:
    project = make_project()
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    case = Case(
        project="demo", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="log in", steps=[],
    )
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=case)
    assert crawl.status is CrawlStatus.COMPLETED


def test_a_transient_precheck_failure_is_named_not_swallowed(tmp_path: Path) -> None:
    """AT-273: `_already_past_login`'s own exception must not be indistinguishable
    from a genuine "not yet authenticated" `False` -- if the precheck's own
    `goto` raises AND the login case that runs next also fails, the crawl's
    stop_reason must say the precheck itself glitched, not just that login
    failed. Nothing was staged as fillable, so the case fails as it would have
    before AT-226 existed -- this test is about the CAUSE reaching the report,
    not about the fallback behaviour, which is unchanged and still correct."""
    project = make_project()
    session, page = make_session(tmp_path, project)

    real_goto = page.goto

    def flaky_goto(url: str, wait_until: str = "") -> None:
        if url == SIGNIN:
            raise RuntimeError("net::ERR_CONNECTION_RESET")
        real_goto(url, wait_until)

    page.goto = flaky_goto  # type: ignore[method-assign]
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())

    assert crawl.status is CrawlStatus.LOGIN_FAILED
    assert crawl.stop_reason is not None
    assert "precheck also failed" in crawl.stop_reason
    assert "ERR_CONNECTION_RESET" in crawl.stop_reason


# -- AT-528: a completed login case is not proof of authentication -------------

def test_a_login_api_401_during_the_bootstrap_is_login_failed(
    tmp_path: Path,
) -> None:
    """The live Pathlynks crawl (crawl_01M31V5GHN91TE38MMB4BKM6HF) completed its
    login case while the app rendered 'Invalid credentials' and the login API
    answered 401 — and the crawl proceeded signed-out, reading COMPLETED. The
    product's own verdict during the bootstrap (a first-party 401 on the login
    API) now ends the crawl LOGIN_FAILED even though every step ran."""
    import crawl_fake as cf

    project = make_project()
    session, page = make_session(tmp_path, project)
    page.fillable[SIGNIN] = {IDENTIFIER}

    class RejectedObserver(PageObserver):
        def drain(self):
            return [], [(f"{BASE}api/auth/login", "401")], [], ([], [])

    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=RejectedObserver(),
                      login_case=_login_case())

    assert crawl.status is CrawlStatus.LOGIN_FAILED
    assert crawl.stop_reason is not None
    assert "401" in crawl.stop_reason
    assert "AT-528" in crawl.stop_reason
    assert cf is not None  # keep the import meaningful if the test evolves


# -- AT-889: a redirect landing AFTER the one-shot precheck -------------------

def _stage_late_redirect(page) -> None:  # type: ignore[no-untyped-def]
    """/signin renders for the precheck's goto, then the app redirects to the
    dashboard by the time the login case's own NAVIGATE runs -- no sleeps: the
    redirect is bound to the second visit of /signin."""
    real_goto, visits = page.goto, []

    def goto(url: str, wait_until: str = "") -> None:
        if url == SIGNIN:
            visits.append(url)
            if len(visits) > 1:
                page.redirects[SIGNIN] = BASE
        real_goto(url, wait_until)

    page.goto = goto
    page.fillable[SIGNIN] = {IDENTIFIER}


def test_a_session_redirect_after_the_precheck_still_reaches_the_crawl(tmp_path: Path) -> None:
    """crawl_01M4KMYEX8YQ4M3DB8J0991Z1T: /signin rendered at the precheck, the app then
    redirected to the dashboard and the FILL waited on a field that was gone."""
    project = make_project()
    session, page = make_session(tmp_path, project)
    _stage_late_redirect(page)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())
    assert crawl.status is CrawlStatus.COMPLETED
    assert crawl.stop_reason == "frontier empty"


def test_a_login_failed_stop_reason_names_the_login_case_error(tmp_path: Path) -> None:
    """Still on /signin and the field genuinely absent: a real failure, and the
    crawl folder alone must say why (the case's own error, not a bare sentence)."""
    project = make_project()
    session, _page = make_session(tmp_path, project)  # nothing fillable at /signin
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())
    assert crawl.status is CrawlStatus.LOGIN_FAILED
    assert crawl.stop_reason is not None
    assert "locator not found" in crawl.stop_reason
    assert IDENTIFIER in crawl.stop_reason

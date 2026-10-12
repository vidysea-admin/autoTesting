"""EXPLORE login bootstrap: run the human-authored login case, or skip it when the
persistent profile already holds a live session (AT-226, AT-889).

Split from `explore.py` for the 300-line cap. One job: decide whether the crawl is
authenticated before the first node, and name the cause when it is not.
Contract: qa/contracts/explore.md X10, X18.
"""

from __future__ import annotations

from urllib.parse import urlparse

from autotester.browser.session import NavigationRefused
from autotester.schema.case import Case
from autotester.schema.enums import Action, Outcome
from autotester.stages import explore_node, explore_status
from autotester.stages.execute import run_case
from autotester.stages.explore_runtime import ExploreRuntime


def _left_login_page(rt: ExploreRuntime, login_url: str) -> bool:
    """Whether the browser is now on a real page of the login host other than the login
    page's path (a blank or foreign page after a failed navigation proves nothing)."""
    here, login = urlparse(rt.session.current_url()), urlparse(login_url)
    return (here.scheme in {"http", "https"} and here.netloc == login.netloc
            and here.path != login.path)


def already_past_login(rt: ExploreRuntime, login_url: str) -> bool:
    """Navigate to the case's login page; report whether the app redirected
    away (AT-226). Still there -> record the login signature for X18(a).
    AT-273: a nav failure must not read as "not yet authenticated" `False` —
    still the safe fallback, but its CAUSE is kept."""
    try:
        rt.session.goto(login_url)
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
    except NavigationRefused as exc:
        rt.login_precheck_error = f"refused by the domain guard: {exc}"
        return False
    except Exception as exc:
        rt.login_precheck_error = f"{type(exc).__name__}: {exc}"
        return False
    if _left_login_page(rt, login_url):
        return True
    rt.login_signature, rt.login_observe_error = explore_status.observed_signature(rt.session)
    explore_node.record_login_observe_failure(rt, rt.login_observe_error)
    return False


def bootstrap_login(rt: ExploreRuntime, case: Case) -> bool:
    """Run the human-authored login case through `run_case` — the ONLY place
    the explorer types anything, and the only pre-crawl form submit (X10).

    **AT-226.** A persistent browser profile can already hold a live session,
    in which case the login page itself redirects away before the case's own
    FILL step ever runs — the field it names is not on the page at all, and
    `run_case` blocks for the full step timeout before reporting ERRORED.
    Checked once, before the case runs, against the case's own NAVIGATE step:
    if the browser lands somewhere other than the login page itself, the
    session is already authenticated and the case is skipped rather than run
    to a guaranteed timeout — a login page that redirects away from itself
    has already done its job, no app-specific marker needed."""
    login_step = next(
        (s for s in sorted(case.steps, key=lambda s: s.order) if s.action is Action.NAVIGATE),
        None,
    )
    if login_step is not None and already_past_login(rt, login_step.target):
        return True
    result = run_case(case, rt.session)
    rt.store.save_result(rt.crawl.id, result)
    if result.outcome is not Outcome.COMPLETED:
        # AT-889: the precheck samples the URL once and can lose a race with a client-side
        # redirect. The case's failure is the later, authoritative moment: if the page is now
        # off the login path the session was live all along. Otherwise name the cause.
        if (login_step is not None and rt.login_precheck_error is None
                and _left_login_page(rt, login_step.target)):
            return True  # the login page did load (precheck ok), then the app moved on
        rt.stop_reason = (f"login case did not complete ({result.outcome.value}"
                          f"{': ' + result.error if result.error else ''})")
        return False
    # AT-528: a COMPLETED step sequence is NOT proof of authentication — run_case
    # observes, it never judges (E1); the live Pathlynks crawl
    # crawl_01M31V5GHN91TE38MMB4BKM6HF completed while the app rendered "Invalid
    # credentials" (expected.visible_text is best-effort settle, never a gate).
    # The product's own verdict during the bootstrap is a first-party 401 on the
    # login API — precise, app-reported, fixture-neutral. A signed-out crawl may
    # never read COMPLETED: end LOGIN_FAILED naming the evidence.
    _console, failed, _dialogs, _popups = rt.observer.drain()
    auth_401 = [(u, why) for u, why in failed if why.rstrip().endswith("401")]
    if auth_401:
        url, why = auth_401[0]
        rt.stop_reason = (f"login case 'completed' but the server rejected it "
                          f"({url} -> {why} — invalid credentials?) — AT-528 guard")
        return False
    return True


def login_failed_reason(rt: ExploreRuntime) -> str:
    """AT-273: name the login-precheck's own swallowed cause when the case
    then genuinely failed too, so an operator sees the precheck itself
    glitched rather than only that login did. AT-528: a failure that already
    named a SPECIFIC cause (the 401 guard sets its own stop_reason) keeps it
    verbatim — the vaguer sentence would overwrite the server's verdict."""
    if rt.stop_reason and "AT-528" in rt.stop_reason:
        return rt.stop_reason
    if rt.stop_reason and rt.stop_reason.startswith("login case did not complete"):
        reason = rt.stop_reason  # AT-889: keeps the case's own outcome and error text
    else:
        reason = "login case did not complete"
    if rt.login_precheck_error:
        reason += f" (precheck also failed: {rt.login_precheck_error})"
    return reason

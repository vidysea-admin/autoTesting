"""AT-113 / AT-889: an unreachable screen never ends a crawl clean, and the
already-authenticated precheck cannot lose a race with a late redirect.
Contract: qa/contracts/explore.md X10, X11, X18."""

from __future__ import annotations

from pathlib import Path

import pytest
from crawl_fake import BASE, crawl_it, grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, CrawlStatus
from autotester.schema.flowspec import Step
from autotester.stages import explore_login, explore_return, explore_status, explore_traversal
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

SIGNIN = "https://app.test/signin"
IDENTIFIER = "input[name='identifier']"


def test_a_screen_lost_during_the_destructive_drain_is_filed_and_not_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-113: the deferred pass recorded an edge but filed no issue and left the node
    EXPLORED, so the crawl ended completed / frontier empty / 0 issues."""
    original = explore_traversal.drain_deferred

    def inject_then_drain(rt):  # type: ignore[no-untyped-def]
        node = next(iter(rt.nodes.values()))
        rt.deferred.append((node.id, node.elements[0]))
        original(rt)

    monkeypatch.setattr(explore_traversal, "drain_deferred", inject_then_drain)
    monkeypatch.setattr(explore_return, "return_to", lambda rt, node, **kw: False)
    crawl, store, _page = crawl_it(tmp_path)

    assert any(n.status.value == "aborted_error" for n in store.list_nodes(crawl.id))
    assert any("lost this screen" in i.detail for i in store.list_crawl_issues(crawl.id))
    assert crawl.issues >= 1
    assert crawl.status is CrawlStatus.ABORTED
    assert not explore_status.is_success(crawl)


def _login_case() -> Case:
    return Case(
        project="demo", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="log in", steps=[
            Step(order=1, action=Action.NAVIGATE, target=SIGNIN),
            Step(order=2, action=Action.FILL, target=IDENTIFIER, value="someone"),
        ],
    )


def test_a_redirect_landing_after_the_precheck_still_counts_as_authenticated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-889: /signin rendered at precheck time, the app redirected afterwards, and the
    case's FILL died on the vanished field -- the crawl ended login_failed."""
    project = make_project()
    session, _page = make_session(tmp_path, project)
    real = explore_login.run_case

    def case_then_late_redirect(case, sess):  # type: ignore[no-untyped-def]
        result = real(case, sess)  # fails: the field is not on the page
        sess.goto(BASE)  # the late client-side redirect
        return result

    monkeypatch.setattr(explore_login, "run_case", case_then_late_redirect)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())
    assert crawl.status is CrawlStatus.COMPLETED


def test_login_failed_names_the_login_cases_own_error(tmp_path: Path) -> None:
    """AT-889: the stop_reason used to carry no cause; the crawl folder alone must explain it."""
    project = make_project()
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(), login_case=_login_case())
    assert crawl.status is CrawlStatus.LOGIN_FAILED
    assert crawl.stop_reason is not None
    assert crawl.stop_reason.startswith("login case did not complete (")
    assert ": " in crawl.stop_reason  # outcome AND error text

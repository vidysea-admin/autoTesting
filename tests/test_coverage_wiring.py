"""The self-extension loop, wired to a real entry point — AT-240.

`diff_coverage`, `request_for` and `ProjectStore.add_request` were all tested
and all correct, and between them they had **zero** production callers: a
`VideoRequest` had never been created in this product's life, so "when it meets
a screen it does not know, it asks the human for a video instead of guessing"
— the north star's own sentence — never happened.

These tests are deliberately driven through the two routes an operator actually
presses (`POST /projects/{slug}/run`, `POST /projects/{slug}/explore`) rather
than by calling `queue_requests` directly. A test that called the helper would
pass just as well with both call sites deleted, which is precisely the vacuous
shape this repo keeps finding in its own guards (AT-218). The browser and the
crawler are faked; the routes' own control flow is real.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.case import Case
from autotester.schema.crawl import Crawl
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    CrawlStatus,
    EvidenceKind,
    Outcome,
    Result,
    ReviewStatus,
)
from autotester.schema.flowspec import FlowSpec, Review, Screen, Step
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult
from autotester.schema.screen_graph import ScreenNode
from autotester.schema.verdict import Verdict
from autotester.stages.coverage import diff_crawl, queue_requests
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _project(root: Path, *, screens: list[Screen]) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.save_flowspec(FlowSpec(project="demo", review=Review(status=ReviewStatus.APPROVED),
                                 screens=screens))
    return store


def _a_case(store: ProjectStore) -> Case:
    return store.add_case(Case(
        project="demo", flow_id="flow-home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Homepage loads",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")],
    ))


def _run_with_urls(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, urls: list[str]
) -> None:
    """Press ▶ Run tests for real, with the browser faked out and the run's
    evidence saying it reached `urls`."""
    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module
    from autotester.browser.session import BrowserSession

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    def fake_run_and_grade_case_resilient(case_, session, judge, run_id, store_):
        result = RawResult(
            case_id=case_.id, outcome=Outcome.COMPLETED,
            evidence=[Evidence(kind=EvidenceKind.URL, path=u) for u in urls],
        )
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                          grader_provider="mock")
        return result, verdict

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)
    # AT-567: _run_and_grade_resilient (and its call to run_and_grade_case_
    # resilient) now lives in ui/run_execution.py -- patch it there, where the
    # name is actually looked up at call time, not on routes_runs_module.
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303, response.text


def test_a_run_that_reaches_an_unknown_route_asks_for_a_video(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole loop, end to end, through the button an operator presses."""
    store = _project(scratch_root, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    _a_case(store)

    _run_with_urls(monkeypatch, client, ["https://demo.test/reports/new"])

    requests = ProjectStore("demo", scratch_root).list_requests()
    assert len(requests) == 1, requests
    assert "/reports/new" in requests[0].prompt


def test_a_run_that_stays_on_known_routes_asks_for_nothing(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """coverage.md V1: a known route is not a gap. A wire that asked for a video
    after every run would be worse than no wire at all."""
    store = _project(scratch_root, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    _a_case(store)

    _run_with_urls(monkeypatch, client, ["https://demo.test/"])

    assert ProjectStore("demo", scratch_root).list_requests() == []


def test_two_runs_over_the_same_unknown_route_ask_once(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """coverage.md V3 surviving the wire: `add_request` is idempotent on a
    content-addressed id, and re-running the suite must not re-ask."""
    store = _project(scratch_root, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    _a_case(store)

    _run_with_urls(monkeypatch, client, ["https://demo.test/reports/new"])
    _run_with_urls(monkeypatch, client, ["https://demo.test/reports/new"])

    assert len(ProjectStore("demo", scratch_root).list_requests()) == 1


def test_a_run_on_a_project_with_no_flowspec_asks_for_nothing(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No FlowSpec means no understanding at all, not "every screen is unknown".
    Asking for a video per URL there is noise, and it is what a naive wire does."""
    store = ProjectStore("demo", scratch_root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    _a_case(store)

    _run_with_urls(monkeypatch, client, ["https://demo.test/reports/new"])

    assert ProjectStore("demo", scratch_root).list_requests() == []


# -- the crawl half ----------------------------------------------------------

def _crawl_reaching(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, root: Path, urls: list[str]
) -> None:
    """Press Explore now for real, with consent and the browser faked out and
    the crawler recording nodes at `urls`."""
    from autotester.browser.session import BrowserSession
    from autotester.stages import explore as explore_stage

    crawl = Crawl(project="demo", id="crawl_demo", status=CrawlStatus.COMPLETED,
                  stop_reason="frontier empty", screens=len(urls))

    def fake_run_crawl(project, session, store, observer=None, bounds=None, login_case=None,
                       crawl_id=None):  # mirrors stages.explore.run_crawl, which the UI now
        # hands the declared login case (X17)
        crawl_ = crawl.model_copy(update={"id": crawl_id or crawl.id})
        for index, url in enumerate(urls):
            store.add_node(ScreenNode(
                crawl_id=crawl_.id, project="demo", url_template=url.split("//", 1)[-1],
                url_example=url, signature=f"sig_{index}", name=f"Screen {index}",
            ))
        store.save_crawl(crawl_)
        return crawl_

    monkeypatch.setattr("autotester.stages.explore_consent.require_consent",
                        lambda *a, **k: None)
    monkeypatch.setattr(explore_stage, "run_crawl", fake_run_crawl)
    monkeypatch.setattr(BrowserSession, "__enter__", lambda self: self)
    monkeypatch.setattr(BrowserSession, "__exit__", lambda self, *exc: None)
    response = client.post("/projects/demo/explore", follow_redirects=False)
    assert response.status_code == 303, response.text


def test_a_crawl_that_finds_an_unknown_screen_asks_for_a_video(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _project(scratch_root, screens=[Screen(id="s1", name="Home", url_pattern="/")])

    _crawl_reaching(monkeypatch, client, scratch_root,
                    ["https://demo.test/", "https://demo.test/settings"])

    requests = ProjectStore("demo", scratch_root).list_requests()
    assert len(requests) == 1, requests
    assert "/settings" in requests[0].prompt


def test_a_screen_the_crawl_never_reached_is_never_a_video_request(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """coverage.md V5, the direction that must NOT be wired: a bounded crawl
    seeing less than the FlowSpec describes is expected, and turning
    `unreached_screens` into requests would ask the human to re-record screens
    the system already understands."""
    _project(scratch_root, screens=[
        Screen(id="s1", name="Home", url_pattern="/"),
        Screen(id="s2", name="Billing", url_pattern="/billing"),
    ])

    _crawl_reaching(monkeypatch, client, scratch_root, ["https://demo.test/"])

    assert ProjectStore("demo", scratch_root).list_requests() == []


# -- AT-289: the loop's CLOSING half, through the same two seams --------------
#
# `queue_requests` is called from both the run route and the crawl route (V6).
# `resolve_requests` shipped wired to the CLI only, so the product's own
# "Merge these screens into the FlowSpec" button covered the gap and left the
# ask OPEN forever. Against T-100's no-CLI goal that is the only door an
# operator has. Driven through the button for the same reason as above: a test
# that called `resolve_requests` directly would pass with the call site deleted.


def _a_crawl_that_found(store: ProjectStore, url: str) -> str:
    crawl = Crawl(project="demo", status=CrawlStatus.COMPLETED)
    store.save_crawl(crawl)
    store.add_node(ScreenNode(
        crawl_id=crawl.id, project="demo", url_example=url, url_template=url,
        signature=f"sig-{url}", title="New report", name="New report"))
    return crawl.id


def test_the_merge_button_closes_the_request_the_crawl_answers(
    client: TestClient, scratch_root: Path
) -> None:
    """Gap -> ask -> the crawl finds that very screen -> the operator merges it.
    The ask must close, not linger. Checker A found it lingering (AT-289)."""
    store = _project(scratch_root, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    crawl_id = _a_crawl_that_found(store, "https://demo.test/reports/new")
    # Precondition, not the thing under test: the ask exists. (The route that
    # queues it, POST /explore, runs a real browser crawl.)
    queue_requests(store, diff_crawl(store.load_flowspec(), store.list_nodes(crawl_id)))
    assert len(ProjectStore("demo", scratch_root).list_requests()) == 1, "precondition: one ask"

    response = client.post(f"/projects/demo/crawls/{crawl_id}/merge", follow_redirects=False)

    assert response.status_code == 303, response.text
    requests = ProjectStore("demo", scratch_root).list_requests()
    assert [r.status.value for r in requests] == ["fulfilled"], requests


def test_the_merge_button_leaves_an_unrelated_ask_open(
    client: TestClient, scratch_root: Path
) -> None:
    """The mirror: merging screens that answer nothing must not close anything.
    A closing wire that fired on every merge would lose real asks."""
    store = _project(scratch_root, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    asked = _a_crawl_that_found(store, "https://demo.test/reports/new")
    queue_requests(store, diff_crawl(store.load_flowspec(), store.list_nodes(asked)))
    other = _a_crawl_that_found(store, "https://demo.test/settings")

    client.post(f"/projects/demo/crawls/{other}/merge", follow_redirects=False)

    statuses = [r.status.value for r in ProjectStore("demo", scratch_root).list_requests()]
    assert "open" in statuses, statuses

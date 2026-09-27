"""The explorer against a REAL headless Chromium and a real local site.

This is where the fake-page tests cannot reach: genuine navigation, a real
`beforeunload`, real `confirm()` dialogs, real failed requests, real console
errors. Skipped when Chromium is unavailable, exactly like
`test_browser.py`'s real-browser test.

Contract: qa/contracts/explore.md X3, X5, X7, X8, X9.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.enums import ApprovalKind, EdgeOutcome, IssueKind
from autotester.schema.project import Project
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

SITE_DIR = Path(__file__).resolve().parent / "fixtures" / "crawl_site"
SENTINELS = ("deleted.html", "saved.html", "logged-out.html")


@pytest.fixture(scope="module")
def crawl_result(
    tmp_path_factory: pytest.TempPathFactory, serve_dir: Callable[[Path], str]
) -> tuple[Crawl, ProjectStore]:
    """Module-scoped on purpose: ONE real crawl, many assertions about it.
    Function scope re-crawled for every test (8 full browser crawls) and made
    the file take minutes."""
    pytest.importorskip("playwright")
    tmp_path = tmp_path_factory.mktemp("crawl-live")
    base_url = serve_dir(SITE_DIR)
    project = Project(slug="crawl-demo", name="Crawl demo", base_url=base_url + "/",
                      allowed_domains=["127.0.0.1"], headed=False)
    paths = ProjectPaths("crawl-demo", tmp_path)
    paths.ensure()
    (tmp_path / ".env").write_text("", encoding="utf-8")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    store = ProjectStore("crawl-demo", tmp_path)
    store.add_approval(RunApproval(
        project="crawl-demo", run_kind=ApprovalKind.CRAWL, target=project.base_url,
        scope="local fixture crawl in the live test suite", max_actions=200,
        wall_clock_s=600.0, granted_by="test", granted_at="2026-09-08",
        expires_at="2099-01-01",
    ).sign())
    observer = PageObserver()
    session = BrowserSession(project, secrets, tmp_path / "shots", paths, observer=observer)
    try:
        session.start()
    except Exception as exc:  # browser binary missing on this machine
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    try:
        crawl = run_crawl(project, session, store, observer=observer,
                          bounds=CrawlBounds(max_screens=12, max_actions=60,
                                             wall_clock_s=120.0, dialog_repeat_limit=2))
    finally:
        session.close()
    return crawl, store


def test_crawl_finds_the_real_sites_screens(crawl_result: tuple[Crawl, ProjectStore]) -> None:
    crawl, store = crawl_result
    templates = {n.url_template for n in store.list_nodes(crawl.id)}
    assert "/" in templates
    assert "/students" in templates
    assert "/settings.html" in templates
    assert crawl.screens >= 4


def test_the_two_student_pages_collapse_to_one_templated_screen(
    crawl_result: tuple[Crawl, ProjectStore],
) -> None:
    """X3 against a real DOM: /students/1/ and /students/2/ differ only in row
    text, so they are ONE screen."""
    crawl, store = crawl_result
    templates = [n.url_template for n in store.list_nodes(crawl.id)]
    assert templates.count("/students/{id}") == 1


def test_no_sentinel_page_is_ever_reached(crawl_result: tuple[Crawl, ProjectStore]) -> None:
    """X5/X6: Delete/Deactivate/Remove/Save/Log out all lead to sentinel pages.
    Reaching any of them means a guard failed against a real browser."""
    crawl, store = crawl_result
    examples = " ".join(n.url_example for n in store.list_nodes(crawl.id))
    for sentinel in SENTINELS:
        assert sentinel not in examples, sentinel


def test_destructive_controls_are_recorded_as_denied(
    crawl_result: tuple[Crawl, ProjectStore],
) -> None:
    crawl, store = crawl_result
    denied = {e.name for e in store.list_edges(crawl.id)
              if e.outcome is EdgeOutcome.DENIED_POLICY}
    assert {"Delete account", "Deactivate", "Remove user", "Save", "Log out"} <= denied


def test_the_external_link_is_refused(crawl_result: tuple[Crawl, ProjectStore]) -> None:
    crawl, store = crawl_result
    refused = [e for e in store.list_edges(crawl.id)
               if e.outcome is EdgeOutcome.OFF_DOMAIN_REFUSED]
    assert any(e.name == "External site" for e in refused)
    assert not any("example.com" in n.url_example for n in store.list_nodes(crawl.id))


def test_first_party_404_and_console_error_become_issues_but_analytics_does_not(
    crawl_result: tuple[Crawl, ProjectStore],
) -> None:
    """X9: /api/missing (first-party 404) and the console error are real
    issues; the Google Analytics request never is."""
    crawl, store = crawl_result
    issues = store.list_crawl_issues(crawl.id)
    details = " ".join(i.detail for i in issues)
    assert "/api/missing" in details
    assert any(i.kind is IssueKind.CONSOLE for i in issues)
    assert "google-analytics" not in details


def test_the_dialog_page_does_not_trap_the_crawl(
    crawl_result: tuple[Crawl, ProjectStore],
) -> None:
    """X8: five confirm() dialogs with dialog_repeat_limit=2 must abort that
    node and let the crawl finish, not hang."""
    crawl, store = crawl_result
    assert crawl.finished_at is not None
    nodes = {n.url_template: n for n in store.list_nodes(crawl.id)}
    dialog_node = nodes.get("/dialog.html")
    if dialog_node is not None:
        assert dialog_node.status.value in ("aborted_dialog", "explored")


def test_the_filter_toggle_is_a_distinct_same_url_screen(
    crawl_result: tuple[Crawl, ProjectStore],
) -> None:
    """X3 the other direction: clicking "Open filters" reveals a checkbox at
    the SAME url, which must register as a different screen."""
    crawl, store = crawl_result
    root_nodes = [n for n in store.list_nodes(crawl.id) if n.url_template == "/"]
    assert len(root_nodes) >= 2, [n.signature for n in root_nodes]

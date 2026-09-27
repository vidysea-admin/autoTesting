"""X18(a) in a REAL browser on a single-page app: login and dashboard share one url (AT-462).

The cycle-2 checker reproduced it live: a correct login on a single-page app whose
dashboard is one structural state ended LOGIN_FAILED, because the judgement counted
signatures at the login url instead of comparing against the login screen itself. The
explorer now observes the login screen's signature before the case types, and calls a
login failed only when every screen reached IS that screen. Both directions are pinned
here with a real headless Chromium against `tests/fixtures/spa_login_site`.
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
from autotester.schema.case import Case
from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind, CrawlStatus
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

SITE = Path(__file__).resolve().parent / "fixtures" / "spa_login_site"


def _crawl(tmp_path: Path, base: str, password: str, *, sticky: bool = False) -> Crawl:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:  # decide "no browser" before the crawl, so a real failure never reads as a skip
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    url = f"{base}/index.html" + ("?sticky=1" if sticky else "")
    project = Project(slug="spa", name="SPA", base_url=url, allowed_domains=["127.0.0.1"],
                      headed=False)
    paths = ProjectPaths("spa", tmp_path)
    paths.ensure()
    (tmp_path / ".env").write_text("", encoding="utf-8")
    store = ProjectStore("spa", tmp_path)
    store.add_approval(RunApproval(
        project="spa", run_kind=ApprovalKind.CRAWL, target=url, scope="local SPA fixture",
        max_actions=30, wall_clock_s=90.0, granted_by="test", granted_at="2026-09-17",
        expires_at="2099-01-01",
    ).sign())
    case = Case(project="spa", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="sign in", steps=[
                    Step(order=1, action=Action.NAVIGATE, target=url),
                    Step(order=2, action=Action.FILL, target="#username", value="tester"),
                    Step(order=3, action=Action.FILL, target="#password", value=password),
                    Step(order=4, action=Action.CLICK, target="#sign-in"),
                ])
    session = BrowserSession(project, SecretStore.load(project, tmp_path / ".env", strict=False),
                             tmp_path / "shots", paths, observer=PageObserver())
    session.start()
    try:
        return run_crawl(project, session, store, observer=PageObserver(), login_case=case,
                         bounds=CrawlBounds(max_screens=6, max_actions=30, wall_clock_s=90.0))
    finally:
        session.close()


def test_a_correct_login_on_a_single_page_app_is_not_login_failed(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    crawl = _crawl(tmp_path, serve_dir(SITE), password="fixture-pass")

    assert crawl.status is not CrawlStatus.LOGIN_FAILED, crawl.stop_reason
    assert crawl.status is CrawlStatus.COMPLETED, crawl.stop_reason


def test_a_wrong_password_on_a_single_page_app_is_login_failed(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    """The guard must still say no: the product never left its login screen."""
    crawl = _crawl(tmp_path, serve_dir(SITE), password="nope")

    assert crawl.status is CrawlStatus.LOGIN_FAILED, crawl.stop_reason
    assert crawl.stop_reason is not None and "login page" in crawl.stop_reason


def test_a_wrong_password_with_a_sticky_error_banner_is_still_login_failed(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    """AT-467, live: a wrong password that leaves a persistent Dismiss control visible
    changes the page's structural signature against a REAL DOM (the fake-site unit test
    proves the logic; this proves the same fixture family under a real browser). The
    fill-target fallback must still call it LOGIN_FAILED."""
    crawl = _crawl(tmp_path, serve_dir(SITE), password="nope", sticky=True)

    assert crawl.status is CrawlStatus.LOGIN_FAILED, crawl.stop_reason

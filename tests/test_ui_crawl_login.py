"""A crawl started from the UI logs in first, with the project's declared login case (X17).

Found by Umesh, 2026-09-16 22:25 (qa/feedback-inbox.md): "abhi tho hmara testing flow
login k baad hi ruk jata hi". Measured the same hour: every crawl on disk stopped at or
before the login page. The UI Explore route called `run_crawl` with no `login_case`, and
`Project` had nowhere to name one, so no crawl started from the UI could reach a single
post-login screen.

The last test is X17's load-bearing verify: a REAL browser, a local fixture product whose
every page sits behind a login form, and a crawl POSTed through the UI route that must map
screens behind the login.

Split from `test_ui_crawls.py` (at doctor's 300-line cap) along a real seam: that file
proves a crawl is bounded and consented; this one proves it can get in.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.cli_crawl import _resolve_crawl_target
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

LOGIN_SITE = Path(__file__).resolve().parent / "fixtures" / "login_site"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _project(root: Path, base: str = "https://demo.test", **extra: object) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url=f"{base}/app/dashboard.html",
                               allowed_domains=["127.0.0.1", "demo.test"], headed=False, **extra))
    return store


def _login_case(store: ProjectStore, base: str = "https://demo.test",
                title: str = "Sign in as the test user") -> Case:
    case = Case(project="demo", flow_id="flow_login", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title=title, steps=[
                    Step(order=1, action=Action.NAVIGATE, target=f"{base}/login.html"),
                    Step(order=2, action=Action.FILL, target="#username", value="tester"),
                    Step(order=3, action=Action.FILL, target="#password", value="fixture-pass"),
                    Step(order=4, action=Action.CLICK, target="#sign-in"),
                ])
    store.add_case(case)
    return case


@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """Stand-ins for the browser and the crawl: record what `run_crawl` was given."""
    calls: list[dict[str, object]] = []

    class Session:
        def __init__(self, *_a: object, **_k: object) -> None:
            calls.append({"browser": True})

        def __enter__(self) -> Session:
            return self

        def __exit__(self, *_a: object) -> None:
            pass

    def run(_project: object, _session: object, _store: object, **kwargs: object) -> Crawl:
        calls.append(kwargs)
        return Crawl(project="demo", id=str(kwargs["crawl_id"]))

    monkeypatch.setattr("autotester.browser.session.BrowserSession", Session)
    monkeypatch.setattr("autotester.stages.explore_consent.require_consent",
                        lambda *_a, **_k: None)
    monkeypatch.setattr("autotester.stages.explore.run_crawl", run)
    return calls


def _run_kwargs(calls: list[dict[str, object]]) -> dict[str, object]:
    return next(c for c in calls if "crawl_id" in c)


# -- (a) one declared source ---------------------------------------------------

def test_declaring_a_login_case_saves_it_on_the_project(root: Path) -> None:
    store = _project(root)
    case = _login_case(store)

    response = TestClient(app).post("/projects/demo/login-case", data={"case_id": case.id},
                                    follow_redirects=False)

    assert response.status_code == 303
    assert store.load_project().login_case_id == case.id


def test_an_empty_choice_clears_the_declaration(root: Path) -> None:
    store = _project(root)
    case = _login_case(store)
    store.save_project(store.load_project().model_copy(update={"login_case_id": case.id}))

    TestClient(app).post("/projects/demo/login-case", data={"case_id": ""})

    assert store.load_project().login_case_id is None


def test_an_unknown_case_is_not_declared_and_not_echoed(root: Path) -> None:
    store = _project(root)
    canary = "case_<script>hunter2"

    response = TestClient(app).post("/projects/demo/login-case", data={"case_id": canary})

    assert response.status_code == 400
    assert canary not in response.text and "hunter2" not in response.text
    assert store.load_project().login_case_id is None


def test_the_cli_uses_the_declared_case_and_the_flag_overrides_it(root: Path) -> None:
    store = _project(root)
    declared = _login_case(store)
    other = _login_case(store, base="https://other.demo.test", title="Sign in another way")
    store.save_project(store.load_project().model_copy(update={"login_case_id": declared.id}))

    _s, _p, by_default = _resolve_crawl_target("demo", None)
    _s, _p, overridden = _resolve_crawl_target("demo", other.id)

    assert by_default is not None and by_default.id == declared.id
    assert overridden is not None and overridden.id == other.id, "the flag wins for one run"
    assert store.load_project().login_case_id == declared.id, "and does not re-declare"


# -- (b) the UI uses it, and says so when there is none ---------------------------

def test_with_nothing_declared_the_crawl_page_says_so_before_a_crawl(root: Path) -> None:
    _project(root)

    text = TestClient(app).get("/projects/demo/crawls").text

    assert "No login case declared" in text


def test_the_declared_case_is_named_on_the_crawl_page_escaped(root: Path) -> None:
    store = _project(root)
    case = _login_case(store, title="<img src=x onerror=alert(1)>")
    store.save_project(store.load_project().model_copy(update={"login_case_id": case.id}))

    text = TestClient(app).get("/projects/demo/crawls").text

    assert "Logs in first" in text
    assert "<img src=x onerror=alert(1)>" not in text
    assert "&lt;img src=x onerror=alert(1)&gt;" in text


def test_the_declared_case_reaches_the_crawl(
    root: Path, launched: list[dict[str, object]],
) -> None:
    store = _project(root)
    case = _login_case(store)
    store.save_project(store.load_project().model_copy(update={"login_case_id": case.id}))

    response = TestClient(app).post("/projects/demo/explore", data={}, follow_redirects=False)

    assert response.status_code == 303
    given = _run_kwargs(launched)["login_case"]
    assert isinstance(given, Case) and given.id == case.id


def test_nothing_declared_crawls_signed_out(root: Path, launched: list[dict[str, object]]) -> None:
    _project(root)

    TestClient(app).post("/projects/demo/explore", data={}, follow_redirects=False)

    assert _run_kwargs(launched)["login_case"] is None


def test_a_declared_case_that_no_longer_exists_is_refused_before_a_browser_opens(
    root: Path, launched: list[dict[str, object]],
) -> None:
    """Silently crawling signed out instead is exactly the run this unit exists to stop."""
    _project(root, login_case_id="case_deleted000")

    response = TestClient(app).post("/projects/demo/explore", data={})

    assert response.status_code == 400
    assert "Login case not found" in response.text
    assert launched == [], "no browser, no crawl"


# -- X17 verify: a real browser maps screens behind a real login -----------------

def test_a_ui_started_crawl_maps_screens_behind_the_login_in_a_real_browser(
    root: Path, serve_dir: Callable[[Path], str],
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:  # decide "no browser" BEFORE the crawl, so a real crash can never read as a skip
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    base = serve_dir(LOGIN_SITE)
    store = _project(root, base=base)
    case = _login_case(store, base=base)
    store.save_project(store.load_project().model_copy(update={"login_case_id": case.id}))
    store.add_approval(RunApproval(
        project="demo", run_kind=ApprovalKind.CRAWL, target=f"{base}/app/dashboard.html",
        scope="local login fixture in the test suite", max_actions=60, wall_clock_s=120.0,
        granted_by="test", granted_at="2026-09-16", expires_at="2099-01-01",
    ).sign())

    response = TestClient(app).post("/projects/demo/explore", data={
        "max_screens": "10", "max_actions": "60", "wall_clock_s": "120", "max_depth": "4",
    }, follow_redirects=False)

    assert response.status_code == 303, response.text[:500]
    crawl_id = store.list_crawl_ids()[0]
    crawl = store.load_crawl(crawl_id)
    assert crawl.login_case_id == case.id
    templates = {n.url_template for n in store.list_nodes(crawl_id)}
    behind = templates - {"/login.html"}
    assert "/app/dashboard.html" in templates, f"never got past the login: {templates}"
    assert {"/app/orders.html", "/app/profile.html"} <= templates, templates
    assert behind, templates
    assert "/logout.html" not in templates, "a crawl must never sign itself out (X6)"

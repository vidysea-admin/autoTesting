"""The crawl-consent UI surfaces (D-018 gate 2's granting + pre-flight).

Split from `test_ui_crawls.py` (AT-536: the file had crossed doctor's 300-line
cap). Covers: the credentials page's crawl-approval card (server-scoped,
server-bound), a secret in free text refused, a run without approval refused
leaving no trace, invalid bounds themed without a browser launch, and the
one-bounds-object pre-flight/run seam (AT-535's policy threading).

Contract: qa/contracts/ui.md + explore.md (D-018).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.crawl import Crawl
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def make_project(root: Path) -> ProjectStore:
    store = ProjectStore("demo", root)
    secret = SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"], secrets=[secret]))
    return store


def test_explore_without_an_approval_is_refused_and_leaves_no_trace(
    client: TestClient, scratch_root: Path
) -> None:
    make_project(scratch_root)
    response = client.post("/projects/demo/explore", follow_redirects=False)
    assert response.status_code == 403
    assert "AutoTester" in response.text
    assert "/projects/demo/env#crawl-approval" in response.text
    assert "uv run autotester" not in response.text
    assert not (scratch_root / "projects" / "demo" / "crawl").exists()
    assert not (scratch_root / "profiles" / "demo").exists()


def test_credentials_page_grants_a_server_scoped_crawl_approval(
    client: TestClient, scratch_root: Path,
) -> None:
    store = make_project(scratch_root)
    page = client.get("/projects/demo/env")
    assert "id='crawl-approval'" in page.text
    assert "applies only to <code>https://demo.test</code>" in page.text
    assert "new Date(expiry.value)" in page.text
    assert "name='target'" not in page.text and "name='project'" not in page.text
    expiry = "2099-09-11T12:00"
    response = client.post("/projects/demo/crawl-approval", data={
        "granted_by": "Umesh", "scope": "read and click safe controls",
        "expires_at": expiry, "timezone_offset_minutes": "330",
        "max_actions": "17", "wall_clock_s": "45",
        "target": "https://evil.test", "project": "other",
    }, follow_redirects=False)
    assert response.status_code == 303
    approval = store.list_approvals()[0]
    assert (approval.project, approval.target, approval.max_actions) == (
        "demo", "https://demo.test", 17)
    assert approval.wall_clock_s == 45 and approval.granted_by == "Umesh"
    assert approval.expires_at == "2099-09-11T06:30:00+00:00"


def test_crawl_approval_refuses_a_secret_in_free_text(
    client: TestClient, scratch_root: Path,
) -> None:
    store = make_project(scratch_root)
    (scratch_root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    response = client.post("/projects/demo/crawl-approval", data={
        "granted_by": "Umesh", "scope": "hunter2", "note": "safe",
        "expires_at": (datetime.now() + timedelta(days=1)).isoformat(),
        "max_actions": "10", "wall_clock_s": "20",
    })
    assert response.status_code == 400 and "hunter2" not in response.text
    assert all(text in response.text for text in (
        "Crawl approval not saved", "Return to crawl approval"))
    assert store.list_approvals() == []


def test_invalid_bounds_are_themed_and_never_launch(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_project(scratch_root)
    monkeypatch.setattr("autotester.browser.session.BrowserSession",
                        lambda *_a, **_k: pytest.fail("browser launched"))
    response = client.post("/projects/demo/explore", data={"max_screens": "0"})
    assert response.status_code == 400
    assert "AutoTester" in response.text and "Invalid crawl bounds" in response.text
    assert not (scratch_root / "projects" / "demo" / "crawl").exists()


def test_one_bounds_object_reaches_preflight_and_run(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_project(scratch_root)
    seen: list[object] = []

    class Session:
        def __init__(self, *_a: object, **_k: object) -> None: pass
        def __enter__(self) -> Session: return self
        def __exit__(self, *_a: object) -> None: pass

    def preflight(_project: object, _store: object, bounds: object,
                  **_kwargs: object) -> None:
        seen.append(bounds)

    def run(_project: object, _session: object, _store: object, **kwargs: object) -> Crawl:
        seen.append(kwargs["bounds"])
        return Crawl(project="demo", id=str(kwargs["crawl_id"]))

    monkeypatch.setattr("autotester.browser.session.BrowserSession", Session)
    monkeypatch.setattr("autotester.stages.explore_consent.require_consent", preflight)
    monkeypatch.setattr("autotester.stages.explore.run_crawl", run)
    response = client.post("/projects/demo/explore", data={
        "max_screens": "7", "max_actions": "11", "wall_clock_s": "13", "max_depth": "3",
    }, follow_redirects=False)
    assert response.status_code == 303 and seen[0] is seen[1]
    bounds = seen[0]
    assert (bounds.max_screens, bounds.max_actions, bounds.wall_clock_s, bounds.max_depth) == (  # type: ignore[attr-defined]
        7, 11, 13.0, 3)


def test_explore_survives_an_invalid_flowspec_after_the_crawl_finished(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-477: routes_crawls.py:251 called store.load_flowspec() unguarded
    after the crawl already finished and saved -- a broken flowspec.json
    turned a completed crawl into a 500 that hid its own result. The route
    must redirect to the crawl page (which itself must not 500 either --
    covered by test_ui_crawls.py's crawl-page test)."""
    store = make_project(scratch_root)
    store.paths.flowspec.write_text("{ this is not a flowspec", encoding="utf-8")

    class Session:
        def __init__(self, *_a: object, **_k: object) -> None: pass
        def __enter__(self) -> Session: return self
        def __exit__(self, *_a: object) -> None: pass

    def run(_project: object, _session: object, _store: object, **kwargs: object) -> Crawl:
        crawl = Crawl(project="demo", id=str(kwargs["crawl_id"]))
        _store.save_crawl(crawl)
        return crawl

    monkeypatch.setattr("autotester.browser.session.BrowserSession", Session)
    monkeypatch.setattr("autotester.stages.explore_consent.require_consent",
                        lambda *_a, **_k: None)
    monkeypatch.setattr("autotester.stages.explore.run_crawl", run)
    response = client.post("/projects/demo/explore", data={
        "max_screens": "7", "max_actions": "11", "wall_clock_s": "13", "max_depth": "3",
    }, follow_redirects=False)
    assert response.status_code == 303
    crawl_id = response.headers["location"].rsplit("/", 1)[-1]
    assert store.load_crawl(crawl_id) is not None
    page = client.get(response.headers["location"])
    assert page.status_code == 200


def test_explore_logs_a_redacted_flowspec_read_failure(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AT-593: `_queue_coverage_gap` used to discard the read failure with no
    server-side trace at all. A broken flowspec.json can echo an
    operator-pasted secret via pydantic's own `input_value=...`, so the
    logged line must both exist and be scrubbed -- and the route's AT-477
    behaviour (redirect, crawl kept) must not change."""
    store = make_project(scratch_root)
    (scratch_root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    store.paths.flowspec.write_text('{"project": "demo", "screens": "hunter2"}',
                                    encoding="utf-8")

    class Session:
        def __init__(self, *_a: object, **_k: object) -> None: pass
        def __enter__(self) -> Session: return self
        def __exit__(self, *_a: object) -> None: pass

    def run(_project: object, _session: object, _store: object, **kwargs: object) -> Crawl:
        crawl = Crawl(project="demo", id=str(kwargs["crawl_id"]))
        _store.save_crawl(crawl)
        return crawl

    monkeypatch.setattr("autotester.browser.session.BrowserSession", Session)
    monkeypatch.setattr("autotester.stages.explore_consent.require_consent",
                        lambda *_a, **_k: None)
    monkeypatch.setattr("autotester.stages.explore.run_crawl", run)
    with caplog.at_level(logging.WARNING, logger="autotester.ui.routes_crawls"):
        response = client.post("/projects/demo/explore", data={
            "max_screens": "7", "max_actions": "11", "wall_clock_s": "13", "max_depth": "3",
        }, follow_redirects=False)
    assert response.status_code == 303
    crawl_id = response.headers["location"].rsplit("/", 1)[-1]
    assert store.load_crawl(crawl_id) is not None
    assert "coverage gap not queued" in caplog.text
    assert "hunter2" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_crawl_page_scrubs_a_secret_from_a_broken_flowspecs_read_error(
    client: TestClient, scratch_root: Path,
) -> None:
    """AT-608: `_coverage_card` renders `_load_flowspec_safe`'s read-failure
    text straight into the crawl page with `escape()` only -- pydantic's own
    error text echoes `input_value=...`, so a declared secret pasted into a
    broken flowspec.json reached the browser raw. The card must render the
    same stated read failure (AT-477's contract is unchanged) but scrubbed."""
    store = make_project(scratch_root)
    (scratch_root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    store.paths.flowspec.write_text('{"project": "demo", "screens": "hunter2"}',
                                    encoding="utf-8")
    store.save_crawl(Crawl(project="demo", id="crawl_demo"))

    response = client.get("/projects/demo/crawls/crawl_demo")

    assert response.status_code == 200
    assert "hunter2" not in response.text
    assert "[REDACTED]" in response.text
    assert "the FlowSpec could not be read" in response.text
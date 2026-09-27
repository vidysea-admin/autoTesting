"""AT-596: every `HTTPException` -- app.py's routers' own, Starlette's bare
one for an unmatched route, and any route's uncaught 404/400/409 -- gets a
themed HTML page for a browser and the exact JSON body FastAPI's default
handler already produced for everyone else. Contract: qa/contracts/ui.md
(U5's escaping discipline extended to the app-wide handler in
`ui/error_pages.py`).

Real routes exercise the negotiation + status-code-unchanged claims (400, 404,
409, the T-184/AT-585 pinned-case route this bug was found against), the
unmatched-route coverage a checker pre-check demanded, and one AT-259 path
(`approve_flowspec`'s unknown-slug 404); a standalone throwaway app exercises
the escaping and secret-redaction claims, which need control over the detail
text and the `.env` `_repo_redactor()` reads that the shared `app` fixture in
other files must not have (it would leak into every other UI test's
redaction).

AT-605 (a 405's `Allow` header surviving the HTML branch) is a separate
concern with its own fixtures -- split into `test_ui_error_page_headers.py`
once this file passed doctor's 300-line cap.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from autotester.core.env import ENV_FILE
from autotester.schema.enums import Action, CaseClass
from autotester.store.project_store import ProjectStore
from autotester.ui import error_pages
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _onboard(client: TestClient) -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })


def _add_case(client: TestClient, title: str, target: str = "https://demo.test/signin"):
    return client.post("/projects/demo/cases", data={
        "title": title, "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.NAVIGATE.value], "step_target": [target],
        "step_value": [""], "step_expected": [""],
    }, follow_redirects=False)


# -- 400 (onboard: blank name) ------------------------------------------------

def test_400_with_html_accept_renders_a_themed_page(
    client: TestClient, scratch_root: Path,
) -> None:
    response = client.post(
        "/onboard",
        data={"slug": "ghost", "name": "  ", "base_url": "https://demo.test/signin",
              "allowed_domains": "demo.test"},
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "a project needs a name" in response.text
    assert "AutoTester" in response.text, "wrapped in the app's shared page(), not a bare fragment"
    assert "href='/'" in response.text, "carries a way back"


def test_400_with_json_accept_is_unchanged(client: TestClient, scratch_root: Path) -> None:
    response = client.post(
        "/onboard",
        data={"slug": "ghost", "name": "  ", "base_url": "https://demo.test/signin",
              "allowed_domains": "demo.test"},
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "a project needs a name"


def test_400_with_no_accept_header_stays_json(client: TestClient, scratch_root: Path) -> None:
    """httpx's own default (`Accept: */*`) — every pre-existing test in this
    suite that never sets the header must keep seeing exactly what it saw
    before this handler existed."""
    response = client.post("/onboard", data={
        "slug": "ghost", "name": "  ", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "a project needs a name"


# -- 404 (unknown case) -------------------------------------------------------

def test_404_with_html_accept_renders_a_themed_page(
    client: TestClient, scratch_root: Path,
) -> None:
    _onboard(client)

    response = client.post(
        "/projects/demo/cases/case_nope/delete", headers={"Accept": "text/html"},
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "no case" in response.text


def test_404_with_json_accept_is_unchanged(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)

    response = client.post(
        "/projects/demo/cases/case_nope/delete", headers={"Accept": "application/json"},
    )

    assert response.status_code == 404
    assert "no case" in response.json()["detail"]


# -- 409 (AT-585 pinned case, the case this bug was filed against) -----------

def _pin_a_case(client: TestClient, scratch_root: Path) -> str:
    _onboard(client)
    _add_case(client, "Known bug — pinned regression")
    store = ProjectStore("demo", scratch_root)
    case = store.list_cases()[0]
    store.update_case(case.model_copy(update={"pinned": True, "pinned_issue_id": "iss_1"}))
    return case.id


def test_409_with_html_accept_renders_a_themed_page(
    client: TestClient, scratch_root: Path,
) -> None:
    case_id = _pin_a_case(client, scratch_root)

    response = client.post(
        f"/projects/demo/cases/{case_id}/delete", headers={"Accept": "text/html"},
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("text/html")
    assert "pinned" in response.text
    assert [c.id for c in ProjectStore("demo", scratch_root).list_cases()] == [case_id]


def test_409_with_json_accept_is_unchanged(client: TestClient, scratch_root: Path) -> None:
    case_id = _pin_a_case(client, scratch_root)

    response = client.post(
        f"/projects/demo/cases/{case_id}/delete", headers={"Accept": "application/json"},
    )

    assert response.status_code == 409
    assert "pinned" in response.json()["detail"]


# -- escaping (U5) and redaction, isolated from the shared `app` fixture -----

@pytest.fixture
def throwaway_app(scratch_root: Path) -> FastAPI:
    """A standalone app carrying only `error_pages`' handler, so these two
    tests can control the `.env` `_repo_redactor()` reads (via the same
    `AUTOTESTER_ROOT` isolation `scratch_root` gives every other test in this
    suite) without ever touching the shared production `app` fixture or the
    real repo-root `.env`."""
    scratch = FastAPI()
    error_pages.register_exception_handler(scratch)

    @scratch.get("/boom")
    def boom(detail: str = "boom") -> None:
        raise HTTPException(400, detail)

    return scratch


def test_html_error_page_escapes_the_detail(
    throwaway_app: FastAPI, scratch_root: Path,
) -> None:
    client = TestClient(throwaway_app)

    response = client.get(
        "/boom", params={"detail": "<script>alert(1)</script>"},
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 400
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_html_error_page_redacts_a_known_secret_from_the_repo_env(
    throwaway_app: FastAPI, scratch_root: Path,
) -> None:
    (scratch_root / ENV_FILE).write_text(
        "DEMO_API_KEY=sk-supersecretvalue123\n", encoding="utf-8")
    client = TestClient(throwaway_app)

    response = client.get(
        "/boom", params={"detail": "call failed: sk-supersecretvalue123"},
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 400
    assert "sk-supersecretvalue123" not in response.text
    assert "REDACTED" in response.text


# -- unmatched route: Starlette's own 404, no route's HTTPException involved -

def test_unmatched_route_with_html_accept_renders_a_themed_page(client: TestClient) -> None:
    """AT-596 pre-check finding: the first version of this handler registered
    on `fastapi.HTTPException` only, so a URL matching no route at all --
    Starlette raises its own bare `starlette.exceptions.HTTPException` for
    that, never a `fastapi.HTTPException` -- fell through uncovered."""
    response = client.get("/this-route-does-not-exist", headers={"Accept": "text/html"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "AutoTester" in response.text


def test_unmatched_route_with_json_accept_is_unchanged(client: TestClient) -> None:
    response = client.get("/this-route-does-not-exist", headers={"Accept": "application/json"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


# -- AT-259: approve/request-edit's own HTTPException (unknown slug) --------

def test_approve_flowspec_unknown_slug_renders_a_themed_page(client: TestClient) -> None:
    """`routes_learn.py::_signed` calls `_load_project_or_404` before any of
    its own themed refusals -- an unknown slug raises a plain
    `fastapi.HTTPException(404, ...)` that nothing in that route catches, so
    it reaches this handler like any other route's 404. (The route's OTHER
    refusals -- unsigned, credential-guard, nothing-to-approve -- already
    return a hand-built `HTMLResponse` via `_refusal()` and never reach this
    handler at all; see the manifest for what AT-259 covers vs. does not.)"""
    response = client.post(
        "/projects/does-not-exist/flowspec/approve", data={"by": "reviewer"},
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")

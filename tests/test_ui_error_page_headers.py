"""AT-605: a header-carrying `HTTPException` must keep that header on the HTML
branch of `ui/error_pages.py`'s handler, not just the JSON one. Contract:
qa/contracts/ui.md U5. Split from test_ui_error_pages.py once that file
passed doctor's 300-line cap.

Checker cycle-1 finding (verdict 7b9727d): `_error_page` rebuilt the response
without `exc.headers`, so a browser-negotiated 405 silently lost the `Allow`
header RFC 9110 SS15.5.6 requires ("a 405 response MUST generate an Allow
header field"), while a JSON caller on the exact same route kept it (FastAPI's
own default handler already forwards `exc.headers`). A real route
(`/projects/{slug}/flowspec/approve`, `@router.post`-only) exercises the
`Allow` claim for both `Accept` values; a standalone throwaway app exercises
a second header (401 `WWW-Authenticate`) that no real route in this app
happens to raise, so the fix is pinned to "any header," not just this one
route's.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from autotester.ui import error_pages
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def throwaway_app(scratch_root: Path) -> FastAPI:
    """A standalone app carrying only `error_pages`' handler, isolated from
    the shared production `app` fixture, so a route can be added here that
    the real app has no reason to carry."""
    scratch = FastAPI()
    error_pages.register_exception_handler(scratch)
    return scratch


# -- AT-605: a 405's Allow header must survive the HTML branch too -----------

def test_405_with_html_accept_keeps_the_allow_header(client: TestClient) -> None:
    """`/projects/{slug}/flowspec/approve` (routes_learn.py:176) is
    `@router.post`-only, so a GET on it never reaches route code -- Starlette's
    own routing raises a bare `HTTPException(405, headers={"Allow": "POST"})`
    before any view runs."""
    response = client.get(
        "/projects/demo/flowspec/approve", headers={"Accept": "text/html"},
    )

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["allow"] == "POST"


def test_405_with_json_accept_keeps_the_allow_header(client: TestClient) -> None:
    """Same route, JSON caller -- must be exactly what it was before this unit
    existed (FastAPI's own default handler already forwards `exc.headers`)."""
    response = client.get(
        "/projects/demo/flowspec/approve", headers={"Accept": "application/json"},
    )

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


def test_other_exception_headers_survive_the_html_branch_too(
    throwaway_app: FastAPI,
) -> None:
    """Not just `Allow` -- any header a route's `HTTPException` carries (a
    401's `WWW-Authenticate`, or a made-up one here) must reach the HTML
    response the same way it always reached the JSON one."""

    @throwaway_app.get("/locked")
    def locked() -> None:
        raise HTTPException(401, "nope", headers={"WWW-Authenticate": "Bearer"})

    client = TestClient(throwaway_app)
    response = client.get("/locked", headers={"Accept": "text/html"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

"""D-066: an Origin/CSRF check on every state-changing UI route.

The local UI has no auth, so any page the operator's browser can reach could POST
to it: edit a project's credential domains, then trigger a run that types a
credential. A browser always sends `Origin` on a cross-site POST, so a request
whose Origin is not the UI's own is refused before any handler runs.

The allowed set is loopback (the UI's default home) plus `AUTOTESTER_ALLOWED_ORIGINS`
(the server URL after go-live). It is deliberately NOT "whatever Host the request
named": a DNS-rebinding page has Origin == Host == attacker.example.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ui_runs import _onboard_demo

from autotester.ui.app import app

EVIL = "https://evil.example"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def _state_changing_routes() -> list[tuple[str, str]]:
    """Walk the OpenAPI schema: FastAPI wraps included routers, so `app.routes` is not flat."""
    found = []
    for path, operations in app.openapi()["paths"].items():
        for method in sorted(UNSAFE & {m.upper() for m in operations}):
            found.append((method, re.sub(r"\{[^}]+\}", "x", path)))
    return found


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.delenv("AUTOTESTER_ALLOWED_ORIGINS", raising=False)
    return TestClient(app)


def test_the_route_walk_finds_the_state_changing_routes_it_is_meant_to_guard() -> None:
    paths = {path for _, path in _state_changing_routes()}
    assert len(paths) >= 20
    for needle in ("/projects/x/run", "/projects/x/env", "/projects/x/secrets",
                   "/projects/x/crawl-approval", "/projects/x/explore", "/onboard"):
        assert needle in paths


@pytest.mark.parametrize(("method", "path"), _state_changing_routes())
def test_every_state_changing_route_refuses_a_cross_site_origin(
    client: TestClient, method: str, path: str,
) -> None:
    response = client.request(method, path, headers={"Origin": EVIL})
    assert response.status_code == 403
    assert "origin" in response.text.lower()


@pytest.mark.parametrize("headers", [
    {"Origin": "null"},
    {"Origin": "http://localhost.evil.example"},
    {"Origin": "http://localhost@evil.example"},
    {"Origin": "http://evil.example:8000"},
    {"Origin": "ftp://localhost"},
    {"Referer": "https://evil.example/page"},
    {"Sec-Fetch-Site": "cross-site"},
    {"Origin": "http://testserver", "Host": "testserver"},  # Origin == Host is not enough
])
def test_other_cross_site_shapes_are_refused(client: TestClient, headers: dict) -> None:
    assert client.post("/projects/nope/run", headers=headers).status_code == 403


@pytest.mark.parametrize("origin", [
    "http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000", "http://localhost",
])
def test_a_same_origin_post_reaches_the_handler(client: TestClient, origin: str) -> None:
    response = client.post("/projects/nope/run", headers={"Origin": origin})
    assert response.status_code == 404  # the handler ran and looked the project up


def test_a_same_origin_referer_is_accepted_when_there_is_no_origin(client: TestClient) -> None:
    headers = {"Referer": "http://localhost:8000/projects/nope"}
    assert client.post("/projects/nope/run", headers=headers).status_code == 404


def test_a_non_browser_client_with_no_origin_still_reaches_the_handler(
    client: TestClient,
) -> None:
    assert client.post("/projects/nope/run").status_code == 404


def test_reads_are_never_blocked_by_origin(client: TestClient) -> None:
    assert client.get("/", headers={"Origin": EVIL}).status_code == 200


def test_the_allowed_origin_is_configurable_for_the_server_url(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = "https://autotester.example.org"
    assert client.post("/projects/nope/run", headers={"Origin": server}).status_code == 403
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", f"{server}/, https://other.example.org")
    assert client.post("/projects/nope/run", headers={"Origin": server}).status_code == 404
    other = {"Origin": "https://other.example.org"}
    assert client.post("/projects/nope/run", headers=other).status_code == 404
    assert client.post("/projects/nope/run", headers={"Origin": EVIL}).status_code == 403
    # configuring a server does not retire the loopback default
    local = {"Origin": "http://localhost:8000"}
    assert client.post("/projects/nope/run", headers=local).status_code == 404
    # a wildcard is not a thing: it must not open the guard
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "*")
    assert client.post("/projects/nope/run", headers={"Origin": EVIL}).status_code == 403


def test_a_refused_cross_site_credential_edit_changes_nothing(
    client: TestClient, tmp_path: Path,
) -> None:
    _onboard_demo(client)
    before = (tmp_path / "projects" / "demo" / "project.json").read_text(encoding="utf-8")
    refused = client.post("/projects/demo/edit", headers={"Origin": EVIL}, data={
        "name": "Demo", "base_url": "https://demo.test", "allowed_domains": "evil.example"})
    assert refused.status_code == 403
    after = (tmp_path / "projects" / "demo" / "project.json").read_text(encoding="utf-8")
    assert after == before and "evil.example" not in after
    assert not (tmp_path / ".env").exists()


@pytest.mark.parametrize("headers", [{"Origin": "http://[bad"}, {"Referer": "http://[bad"}])
def test_an_unparsable_origin_or_referer_is_refused_not_a_server_error(
    client: TestClient, headers: dict,
) -> None:
    assert client.post("/projects/nope/run", headers=headers).status_code == 403

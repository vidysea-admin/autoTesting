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

from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app
from autotester.ui.env_editor import set_env_value

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
    # D-110: `*` is an opt-in allow-all -- it now opens the guard to any origin
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "*")
    assert client.post("/projects/nope/run", headers={"Origin": EVIL}).status_code == 404


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


# -- AT-758 / AT-760 / AT-761 ----------------------------------------------------------------

BAD_HOSTS = ["evil.example", "evil.example:8000", "localhost.evil.example", "127.0.0.1.evil.com",
             "localhost:8000.evil.com", "localhost@evil.example", "localhost/x", "localhost.", "",
             "evil.example@localhost", "x@127.0.0.1:8000"]


def _save_credential(tmp_path: Path) -> None:
    ProjectStore("demo", tmp_path).save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]))
    set_env_value(tmp_path / ".env", "DEMO_PASSWORD", "s3cr3t-real-value")


@pytest.mark.parametrize("host", BAD_HOSTS)
@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/projects/demo/env"), ("GET", "/"), ("POST", "/projects/nope/run")])
def test_a_host_outside_the_allow_list_gets_an_empty_403_on_every_method(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    host: str, method: str, path: str,
) -> None:
    monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS", raising=False)
    _save_credential(tmp_path)
    response = client.request(method, path, headers={"Host": host})
    assert response.status_code == 403 and response.content == b""


def test_the_rebinding_repro_cannot_read_a_saved_credential_but_loopback_can(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS", raising=False)
    _save_credential(tmp_path)
    rebound = client.get("/projects/demo/env", headers={"Host": "evil.example:8000"})
    assert rebound.status_code == 403 and "s3cr3t-real-value" not in rebound.text
    for host in ("localhost:8000", "127.0.0.1:8000", "[::1]:8000", "localhost"):
        local = client.get("/projects/demo/env", headers={"Host": host})
        assert local.status_code == 200 and "s3cr3t-real-value" in local.text


def test_hosts_of_the_allowed_origins_and_the_hosts_variable_are_added_exactly(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS", raising=False)
    get = lambda host: client.get("/", headers={"Host": host}).status_code  # noqa: E731
    assert get("testserver") == 403 and get("autotester.example.org") == 403
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "https://autotester.example.org/")
    assert get("autotester.example.org") == 200 and get("Autotester.Example.org") == 200
    assert get("autotester.example.org:9999") == 403 and get("evil.example") == 403
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "ui.internal, other.internal:8443")
    assert get("ui.internal") == 200 and get("other.internal:8443") == 200
    assert get("ui.internal:80") == 403 and get("other.internal") == 403
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "*")
    assert get("evil.example") == 200  # D-110: `*` is an opt-in allow-all


@pytest.mark.parametrize("origin", ["http://localhost:8000.evil.com", "http://localhost:80a",
                                    "http://127.0.0.1:x", "http://[::1]:8000.evil.com"])
def test_an_origin_with_an_unparsable_port_is_refused(client: TestClient, origin: str) -> None:
    assert client.post("/projects/nope/run", headers={"Origin": origin}).status_code == 403


@pytest.mark.parametrize(("name", "pairs"), [
    ("origin", [("Host", "localhost:8000"), ("Origin", "http://localhost:8000"), ("Origin", EVIL)]),
    ("origin", [("Host", "localhost:8000"), ("Origin", EVIL), ("Origin", "http://localhost:8000")]),
    ("host", [("Host", "localhost:8000"), ("Host", "evil.example")]),
    ("host", [("Host", "evil.example"), ("Host", "localhost:8000")]),
])
def test_more_than_one_origin_or_host_header_is_refused(
    client: TestClient, name: str, pairs: list[tuple[str, str]],
) -> None:
    response = client.post("/projects/nope/run", headers=pairs)  # httpx keeps repeated names
    assert response.status_code == 403, name


def test_a_request_with_no_host_header_is_refused() -> None:
    """Fail closed: a scope with no Host at all (HTTP/1.0) never reaches the app."""
    import asyncio

    from autotester.ui.helpers import _OriginGuard

    sent: list[dict] = []
    reached: list[bool] = []

    async def inner(scope, receive, send) -> None:
        reached.append(True)

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    asyncio.run(_OriginGuard(inner)(scope, None, send))
    assert not reached and sent[0]["status"] == 403


# -- D-110: `*` is an opt-in allow-all (D-066 guard off; CSRF + host-spoofing accepted) ------

def test_star_in_allowed_origins_opens_both_the_origin_and_the_host_guard(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-110: `AUTOTESTER_ALLOWED_ORIGINS=*` is the single switch that turns the whole guard
    off -- any cross-site POST is accepted and any Host is answered."""
    monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "*")
    assert client.post("/projects/nope/run", headers={"Origin": EVIL}).status_code == 404
    assert client.get("/", headers={"Host": "anything.evil.example"}).status_code == 200


def test_star_in_allowed_hosts_opens_only_the_host_guard_not_the_origin_guard(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-110: `AUTOTESTER_ALLOWED_HOSTS=*` answers any Host, but a cross-site POST is still
    refused (its Origin is not vouched for) -- so the login POST needs ALLOWED_ORIGINS=*."""
    monkeypatch.delenv("AUTOTESTER_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "*")
    assert client.get("/", headers={"Host": "anything.evil.example"}).status_code == 200
    assert client.post("/projects/nope/run", headers={"Origin": EVIL}).status_code == 403

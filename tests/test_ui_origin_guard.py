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


def _guard_reply(method: str, headers: list[tuple[str, str]]) -> tuple[list, list]:
    import asyncio

    from autotester.ui.helpers import _OriginGuard

    reached, sent = [], []

    async def handler(scope, receive, send):
        reached.append("handler")
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"saved-fixture-secret"})

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        sent.append(message)

    asyncio.run(_OriginGuard(handler)(
        {"type": "http", "method": method,
         "headers": [(k.encode(), v.encode()) for k, v in headers]}, receive, send))
    return reached, sent


@pytest.mark.parametrize("origin", ["http://localhost:8000.evil.com", "http://localhost:x",
                                    "http://localhost:65536", "http://localhost:",
                                    "http://[::1]evil", "http://[::1]:x",
                                    "http://@localhost", "http://:@localhost"])
def test_malformed_loopback_origin_refuses_even_when_explicitly_listed(
    monkeypatch: pytest.MonkeyPatch, origin: str,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", origin)
    reached, sent = _guard_reply("POST", [("Host", "localhost"), ("Origin", origin)])
    assert reached == [] and sent[0]["status"] == 403
    assert origin.encode() not in sent[-1]["body"]


@pytest.mark.parametrize("origins", [(EVIL, "http://localhost"), ("http://localhost", EVIL)])
def test_duplicate_origins_refuse_in_either_order_before_routing(origins: tuple) -> None:
    reached, sent = _guard_reply("POST", [("Host", "localhost"),
                                          *(('Origin', origin) for origin in origins)])
    assert reached == [] and sent[0]["status"] == 403
    assert b"saved-fixture-secret" not in sent[-1]["body"]


@pytest.mark.parametrize("method", ["GET", "HEAD", "POST", "DELETE"])
@pytest.mark.parametrize("host", ["evil.example", "localhost.evil.example",
                                  "127.0.0.1.evil.io", "localhost:x", "localhost:",
                                  "[::1]evil", "[::1]:x", "localhost:65536"])
def test_host_guard_refuses_every_http_method_before_auth_or_handler(
    monkeypatch: pytest.MonkeyPatch, method: str, host: str,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "*")
    monkeypatch.delenv("AUTOTESTER_ALLOWED_ORIGINS", raising=False)
    reached, sent = _guard_reply(method, [("Host", host)])
    assert reached == [] and sent[0]["status"] == 403
    assert host.encode() not in sent[-1]["body"]
    assert b"saved-fixture-secret" not in sent[-1]["body"]


@pytest.mark.parametrize("host", ["localhost", "LOCALHOST:8000", "127.0.0.1:12",
                                  "[::1]", "[::1]:8000", "listed.example:443",
                                  "origin.example:8000"])
def test_loopback_and_explicitly_allowed_hosts_reach_handler(
    monkeypatch: pytest.MonkeyPatch, host: str,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "LISTED.example:443")
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "https://origin.example")
    reached, sent = _guard_reply("GET", [("Host", host)])
    assert reached == ["handler"] and sent[0]["status"] == 200


@pytest.mark.parametrize("headers", [[("Host", "listed.example:80")],
                                     [("Host", "localhost"), ("Host", "localhost")], []])
def test_host_explicit_port_and_unambiguous_single_header_are_required(
    monkeypatch: pytest.MonkeyPatch, headers: list,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "listed.example:443")
    monkeypatch.delenv("AUTOTESTER_ALLOWED_ORIGINS", raising=False)
    reached, sent = _guard_reply("GET", headers)
    assert reached == [] and sent[0]["status"] == 403


@pytest.mark.parametrize("style", ["omitted", "positional", "keyword", "explicit-default"])
def test_fixture_localhost_default_preserves_explicit_urls_and_host(style: str) -> None:
    expected = "http://localhost" if style == "omitted" else "https://explicit.example"
    if style == "positional":
        client = TestClient(app, expected, headers={"Host": "evil.example"})
    else:
        if style == "explicit-default":
            expected = "http://testserver"
        kwargs = {} if style == "omitted" else {"base_url": expected}
        client = TestClient(app, **kwargs, headers={"Host": "evil.example"})
    assert str(client.base_url).rstrip("/") == expected
    assert client.headers["Host"] == "evil.example"
    assert client.build_request("GET", "/", headers={"Host": "other.example"}).headers[
        "Host"] == "other.example"


@pytest.mark.parametrize(("method", "headers"), [
    ("GET", [("Host", "evil.example")]),
    ("POST", [("Host", "localhost.evil.example")]),
    ("POST", [("Host", "localhost"), ("Origin", "http://localhost:x")]),
    ("POST", [("Host", "localhost"), ("Origin", EVIL), ("Origin", "http://localhost")]),
    ("POST", [("Host", "localhost"), ("Origin", "http://localhost"), ("Origin", EVIL)]),
])
def test_bad_headers_precede_auth_and_leave_seeded_files_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, headers: list,
) -> None:
    from auth_harness import ADMIN, account, gate_on, login, project

    from autotester.ui import auth_middleware

    root = gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    signed = login(ADMIN)
    project(root, "demo")
    (root / ".env").write_bytes(b"DEMO_PASSWORD=saved-fixture-secret\n")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setattr(auth_middleware, "_principal", lambda _: pytest.fail("auth reached"))
    reply = signed.request(method, "/projects/demo/env", headers=headers,
                           data={"key": "DEMO_PASSWORD", "value": "attacker-canary"})
    assert reply.status_code == 403
    assert "saved-fixture-secret" not in reply.text and "attacker-canary" not in reply.text
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before

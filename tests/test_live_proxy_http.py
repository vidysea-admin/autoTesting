"""E6.1, E6.3 (HTTP half), E6.5, E6.7 (HTTP): the in-app noVNC relay (AT-1419)."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_harness import ADMIN, account, client, gate_on, login
from live_stub import Stub

from autotester.ui import routes_live


@pytest.fixture
def stubs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Stub]]:
    gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    account("dev@team.test", "developer")       # live.view only
    account("tester@team.test", "tester")       # no live.view
    control, view = Stub("control"), Stub("view")
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc", ("127.0.0.1", control.port))
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc-view", ("127.0.0.1", view.port))
    yield {"control": control, "view": view}
    control.stop()
    view.stop()


def _contacts(stubs: dict[str, Stub]) -> int:
    return sum(s.contacts for s in stubs.values())


def test_relay_strips_prefix_and_drops_cookie_and_authorization(stubs) -> None:
    admin = login(ADMIN)
    resp = admin.get("/novnc/vnc.html", headers={"authorization": "Bearer secret-canary"})
    assert resp.status_code == 200 and resp.text == "stub:control:/vnc.html"
    path, seen = stubs["control"].http[-1]
    assert path == "/vnc.html" and "cookie" not in seen and "authorization" not in seen
    assert stubs["view"].contacts == 0


def test_view_endpoint_reaches_only_the_view_upstream(stubs) -> None:
    resp = login("dev@team.test").get("/novnc-view/core/rfb.js?x=1")
    assert resp.status_code == 200 and resp.text == "stub:view:/core/rfb.js?x=1"
    assert stubs["control"].contacts == 0


@pytest.mark.parametrize("path", [
    "/novnc//evil.example/x", "/novnc/%2e%2e/%2e%2e/etc", "/novnc/..%2f..%2fetc",
    "/novnc/a%5cb", "/novnc/a%00b", "/novnc/http://evil.example/x", "/novnc/a%2f..%2fb",
])
def test_hostile_paths_are_refused_before_any_connection(stubs, path: str) -> None:
    assert login(ADMIN).get(path).status_code == 400
    assert _contacts(stubs) == 0


def test_request_host_never_picks_the_upstream(stubs, monkeypatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "testserver,evil.example")
    resp = login(ADMIN).get("/novnc/vnc.html", headers={"host": "evil.example"})
    assert resp.status_code == 200 and resp.text == "stub:control:/vnc.html"


@pytest.mark.parametrize("prefix", ["/novnc", "/novnc-view"])
@pytest.mark.parametrize("who,allowed", [
    (None, set()), ("tester@team.test", set()),
    ("dev@team.test", {"/novnc-view"}), (ADMIN, {"/novnc", "/novnc-view"})])
def test_auth_matrix_http(stubs, prefix: str, who: str | None, allowed: set[str]) -> None:
    c = client() if who is None else login(who)
    resp = c.get(prefix + "/vnc.html", headers={"accept": "application/json"})
    if prefix in allowed:
        assert resp.status_code == 200
    else:
        assert resp.status_code == (401 if who is None else 403), resp.status_code
        assert _contacts(stubs) == 0


@pytest.mark.parametrize("path", ["/novnc", "/novnc-view", "/novnc/", "/websockify",
                                  "/websockify/x", "/vnc.html", "/vnc_lite.html"])
def test_look_alike_vnc_paths_are_403_and_never_relay(stubs, path: str) -> None:
    assert login(ADMIN).get(path).status_code == 403
    assert client().get(path, headers={"accept": "application/json"}).status_code in (401, 403)
    assert _contacts(stubs) == 0


def test_closed_upstream_is_502_without_the_address(stubs, monkeypatch) -> None:
    with socket.socket() as s:                       # grab a port, then free it
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc", ("127.0.0.1", port))
    started = time.monotonic()
    resp = login(ADMIN).get("/novnc/vnc.html")
    assert resp.status_code == 502 and time.monotonic() - started < 4
    assert "127.0.0.1" not in resp.text and str(port) not in resp.text


def test_a_hung_upstream_does_not_block_other_routes(stubs, monkeypatch) -> None:
    monkeypatch.setattr(routes_live, "_READ_TIMEOUT_S", 2.0)
    hang = socket.socket()
    hang.bind(("127.0.0.1", 0))
    hang.listen(5)                                   # accepts in the kernel, never answers
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc",
                        ("127.0.0.1", hang.getsockname()[1]))
    try:
        with login(ADMIN) as c:
            result: list[int] = []
            worker = threading.Thread(
                target=lambda: result.append(c.get("/novnc/vnc.html").status_code))
            worker.start()
            time.sleep(0.5)
            started = time.monotonic()
            assert c.get("/healthz").status_code == 200
            assert time.monotonic() - started < 1.0
            worker.join(6)
        assert result == [502]
    finally:
        hang.close()

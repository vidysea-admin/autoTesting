"""E6.2, E6.3 (websocket half), E6.4, E6.7 (websocket): the in-app noVNC websocket relay."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_harness import ADMIN, account, client, gate_on, login
from live_stub import Stub
from starlette.websockets import WebSocketDisconnect

from autotester.ui import routes_live


@pytest.fixture
def handled(monkeypatch: pytest.MonkeyPatch) -> threading.Event:
    """Set when the relay's websocket handler has fully returned. Starlette's test session cancels
    the app the moment its `with` exits, so a test that wants a clean end waits on this first."""
    done = threading.Event()
    real = routes_live._relay_ws

    async def watched(ws, prefix):
        try:
            await real(ws, prefix)
        finally:
            done.set()

    monkeypatch.setattr(routes_live, "_relay_ws", watched)
    return done


@pytest.fixture
def stubs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
          handled: threading.Event) -> Iterator[dict[str, Stub]]:
    gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    account("dev@team.test", "developer")
    account("tester@team.test", "tester")
    control, view = Stub("control"), Stub("view")
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc", ("127.0.0.1", control.port))
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc-view", ("127.0.0.1", view.port))
    yield {"control": control, "view": view}
    control.stop()
    view.stop()


def _ws(c, prefix: str, **kw):
    return c.websocket_connect(prefix + "/websockify", subprotocols=["binary"], **kw)


def _close_and_settle(ws, handled: threading.Event) -> None:
    """Close INSIDE the `with`, then wait for the handler to finish: the `with` exit would
    otherwise cancel it mid-cleanup (the race that made these tests flaky)."""
    ws.close(1000)
    assert handled.wait(10), "the relay handler never finished after the client closed"


def test_frames_relay_both_ways_and_close_propagates(stubs, handled) -> None:
    with _ws(login(ADMIN), "/novnc") as ws:
        assert ws.accepted_subprotocol == "binary"
        ws.send_bytes(b"\x00\x01rfb")
        assert ws.receive_bytes() == b"\x00\x01rfb"
        ws.send_text("hello")
        assert ws.receive_text() == "hello"
        _close_and_settle(ws, handled)
    assert stubs["control"].closed.wait(5), "upstream never saw the client close"
    assert stubs["control"].subprotocols == ["binary"] and stubs["view"].contacts == 0


@pytest.mark.parametrize("prefix", ["/novnc", "/novnc-view"])
@pytest.mark.parametrize("who,allowed", [
    (None, set()), ("tester@team.test", set()),
    ("dev@team.test", {"/novnc-view"}), (ADMIN, {"/novnc", "/novnc-view"})])
def test_auth_matrix_websocket(stubs, handled, prefix: str, who: str | None,
                               allowed: set[str]) -> None:
    c = client() if who is None else login(who)
    if prefix in allowed:
        with _ws(c, prefix) as ws:
            ws.send_bytes(b"ok")
            assert ws.receive_bytes() == b"ok"
            _close_and_settle(ws, handled)
        return
    with pytest.raises(WebSocketDisconnect), _ws(c, prefix):
        pass
    assert sum(s.contacts for s in stubs.values()) == 0


def test_foreign_origin_is_refused_even_with_a_valid_session(stubs) -> None:
    with pytest.raises(WebSocketDisconnect), _ws(
            login(ADMIN), "/novnc", headers={"origin": "https://evil.example"}):
        pass
    assert stubs["control"].contacts == 0


def test_own_origin_and_no_origin_are_accepted(stubs, handled) -> None:
    for headers in ({"origin": "http://testserver"}, {}):
        with _ws(login(ADMIN), "/novnc", headers=headers) as ws:
            ws.send_bytes(b"a")
            assert ws.receive_bytes() == b"a"
            _close_and_settle(ws, handled)
        handled.clear()


def test_absent_upstream_closes_1011_quickly(stubs, handled, monkeypatch) -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setitem(routes_live.VNC_UPSTREAMS, "/novnc", ("127.0.0.1", port))
    started = time.monotonic()
    with _ws(login(ADMIN), "/novnc") as ws, pytest.raises(WebSocketDisconnect) as gone:
        ws.receive_bytes()
        assert handled.wait(10)
    assert gone.value.code == 1011 and time.monotonic() - started < 4


def test_oversize_frame_closes_1009(stubs, handled, monkeypatch) -> None:
    monkeypatch.setattr(routes_live, "_MAX_FRAME", 1024)
    with _ws(login(ADMIN), "/novnc") as ws:
        ws.send_bytes(b"x" * 4096)
        with pytest.raises(WebSocketDisconnect) as gone:
            ws.receive_bytes()
        assert handled.wait(10)
    assert gone.value.code == 1009
    assert stubs["control"].received == []     # the relay refused it; it never went upstream

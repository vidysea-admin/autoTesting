"""T-177 slice 0 fix cycle 2 (F1a): the DevTools identity probe against a HOSTILE loopback listener.

`launch._answers_as` decides whether the listener on the port file's port is the browser we just
launched, while that browser (holding the run's credentials) is already exposed. So the probe
itself must be bounded and must never be steered: one monotonic deadline for connect + headers +
body (`PROBE_DEADLINE_S`), a hard cap on bytes read (`PROBE_MAX_BYTES`), any error from parsing
means "not this browser", and no redirect is ever followed. No real browser is launched here: the
hostile listener is a raw socket server, the port file is written by the test.
"""

from __future__ import annotations

import contextlib
import json
import socket
import threading
import time
from pathlib import Path

import pytest
from test_browser_session_cdp import GUID, FakeDevTools, install, refuses_connections, session

from autotester.browser import launch
from autotester.browser.launch import CdpEndpointError

GOOD = json.dumps({"webSocketDebuggerUrl": f"ws://127.0.0.1:1{GUID}"}).encode()


def _read_request(conn: socket.socket) -> None:
    conn.settimeout(2)
    seen = b""
    while b"\r\n\r\n" not in seen:
        seen += conn.recv(4096)


class Hostile:
    """A loopback listener whose reply to `GET /json/version` is whatever `mode` says."""

    def __init__(self, mode: str, location: str = "") -> None:
        self.mode, self.location = mode, location
        self.connections = 0
        self.sent = 0
        self.stopping = threading.Event()
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        while not self.stopping.is_set():
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            self.connections += 1
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _send(self, conn: socket.socket, data: bytes) -> None:
        conn.sendall(data)
        self.sent += len(data)

    def _serve(self, conn: socket.socket) -> None:
        with contextlib.suppress(OSError), conn:
            _read_request(conn)
            head = b"HTTP/1.1 200 OK\r\n"
            if self.mode == "drip_body":
                self._send(conn, head + b"Content-Length: 100000\r\n\r\n")
                while not self.stopping.is_set():
                    self._send(conn, b" ")
                    time.sleep(0.1)
            elif self.mode == "drip_headers":
                self._send(conn, head)
                while not self.stopping.is_set():
                    self._send(conn, b"X-A: b\r\n")
                    time.sleep(0.1)
            elif self.mode == "huge_declared":
                self._send(conn, head + b"Content-Length: 314572800\r\n\r\n")
                while not self.stopping.is_set():
                    self._send(conn, GOOD + b" " * 65536)
            elif self.mode == "padded_declared":  # a correct answer, padded past the cap
                body = GOOD + b" " * 100_000
                self._send(conn, head + f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
            elif self.mode == "padded_undeclared":
                self._send(conn, head + b"Connection: close\r\n\r\n" + GOOD + b" " * 100_000)
            elif self.mode == "deep":
                body = b"[" * 50_000
                self._send(conn, head + f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
            elif self.mode == "redirect":
                self._send(conn, f"HTTP/1.1 302 Found\r\nLocation: {self.location}\r\n"
                                 "Content-Length: 0\r\n\r\n".encode())

    def stop(self) -> None:
        self.stopping.set()
        self.sock.close()


def _profile(tmp_path: Path, port: int) -> Path:
    (tmp_path / "DevToolsActivePort").write_text(f"{port}\n{GUID}", encoding="utf-8")
    return tmp_path


def _refused(tmp_path: Path, mode: str, *, deadline: float = 0.6, location: str = "",
             monkeypatch: pytest.MonkeyPatch) -> tuple[Hostile, float]:
    monkeypatch.setattr(launch, "PROBE_DEADLINE_S", deadline)
    bad = Hostile(mode, location)
    started = time.monotonic()
    with pytest.raises(CdpEndpointError, match="not this browser"):
        launch.verified_cdp_url(_profile(tmp_path, bad.port))
    elapsed = time.monotonic() - started
    bad.stop()
    return bad, elapsed


@pytest.mark.parametrize("mode", ["drip_body", "drip_headers"])
def test_a_trickling_listener_is_cut_off_at_the_overall_deadline(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """One byte every 0.1 s never trips a per-recv timeout; only a total deadline ends it."""
    _bad, elapsed = _refused(tmp_path, mode, deadline=0.6, monkeypatch=monkeypatch)
    assert elapsed < 2.0, f"the probe held start() for {elapsed:.1f}s against a 0.6s deadline"


@pytest.mark.parametrize("mode", ["padded_declared", "padded_undeclared"])
def test_a_correct_answer_padded_past_the_byte_cap_is_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """The padded reply IS this browser's answer, so only the cap can be what refuses it."""
    assert launch.PROBE_MAX_BYTES == 64 * 1024
    _refused(tmp_path, mode, deadline=5, monkeypatch=monkeypatch)


def test_a_huge_reply_is_not_buffered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad, elapsed = _refused(tmp_path, "huge_declared", deadline=5, monkeypatch=monkeypatch)
    assert elapsed < 4.0 and bad.sent < 16 * 1024 * 1024, f"{bad.sent} bytes sent to the probe"


def test_a_deeply_nested_reply_is_not_this_browser_not_a_recursion_error(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _refused(tmp_path, "deep", deadline=5, monkeypatch=monkeypatch)


@pytest.mark.parametrize("target", ["loopback_port", "other_host"])
def test_a_redirect_is_never_followed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    """A 3xx is "not this browser", and nothing but 127.0.0.1:<port file port> is ever contacted."""
    lure = Hostile("padded_declared")  # records connections
    answering = FakeDevTools()  # a valid `/json/version` for the right guid, on its own port
    host, port = ("127.0.0.1", answering.port)
    if target == "other_host":
        host, port = "localhost", lure.port
    dest = f"http://{host}:{port}/json/version"
    _refused(tmp_path, "redirect", deadline=5, location=dest, monkeypatch=monkeypatch)
    assert lure.connections == 0 and answering.hits == 0
    lure.stop()
    answering.stop()


@pytest.mark.parametrize("mode", ["deep", "drip_body", "redirect"])
def test_a_hostile_reply_closes_the_exposed_browser(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """Through `BrowserSession.start()`: the right error type, and the browser is closed."""
    monkeypatch.setattr(launch, "PROBE_DEADLINE_S", 0.6)
    bad = Hostile(mode, location="http://127.0.0.1:9/json/version")
    install(monkeypatch, devtools=bad)
    s = session(tmp_path, expose_cdp=True)
    started = time.monotonic()
    with pytest.raises(CdpEndpointError, match="not this browser"):
        s.start()
    assert time.monotonic() - started < 3.0
    assert s.cdp_url is None and refuses_connections(bad.port)

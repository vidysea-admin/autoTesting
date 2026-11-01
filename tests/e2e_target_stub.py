"""Local stubs for the target-reachability preflight tests (E4.2, AT-1421). Not a test module.

Everything binds 127.0.0.1 on an ephemeral port: no test here ever touches the real internet.
`Silent` accepts TCP connections at the kernel level but never answers (a blackholed target),
`Responder` is a tiny HTTP server that answers with a chosen status and records every request.
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Silent:
    """A listening socket nobody `accept()`s: connect succeeds, a request is never answered."""

    def __init__(self) -> None:
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}/"

    def saw_connect(self) -> bool:
        """True when a client connected (it sits in the accept queue until we look)."""
        self.sock.settimeout(0.3)
        try:
            self.sock.accept()
        except OSError:
            return False
        return True

    def close(self) -> None:
        self.sock.close()


@contextmanager
def silent() -> Iterator[Silent]:
    stub = Silent()
    try:
        yield stub
    finally:
        stub.close()


class Responder:
    """Answers every GET with `status` (and `location` for a 3xx); records path + headers."""

    def __init__(self, status: int = 200, location: str | None = None,
                 cookie: bool = False) -> None:
        self.requests: list[tuple[str, dict[str, str]]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                outer.requests.append((self.path, {k.lower(): v for k, v in self.headers.items()}))
                self.send_response(outer.status if self.path == "/" else 200)
                if outer.location and self.path == "/":
                    self.send_header("Location", outer.location)
                if outer.cookie:
                    self.send_header("Set-Cookie", "sid=abc; Path=/")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args: object) -> None:
                return None

        self.status, self.location, self.cookie = status, location, cookie
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@contextmanager
def responder(status: int = 200, location: str | None = None,
              cookie: bool = False) -> Iterator[Responder]:
    stub = Responder(status, location, cookie)
    try:
        yield stub
    finally:
        stub.close()

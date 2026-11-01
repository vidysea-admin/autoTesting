"""A stand-in for one websockify upstream (E6 tests): HTTP static side and websocket echo
side on ONE loopback port, recording every contact so a test can assert "zero connections"."""

from __future__ import annotations

import threading

from websockets.sync.server import serve


class Stub:
    def __init__(self, name: str) -> None:
        self.name = name
        self.http: list[tuple[str, dict[str, str]]] = []   # every request the stub received
        self.subprotocols: list[str | None] = []
        self.received: list[str | bytes] = []   # every websocket frame the stub got
        self.closed = threading.Event()
        self.server = serve(self._handler, "127.0.0.1", 0, process_request=self._process,
                            subprotocols=["binary"], compression=None)
        self.port = self.server.socket.getsockname()[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def contacts(self) -> int:
        return len(self.http)

    def _process(self, connection, request):
        self.http.append((request.path, {k.lower(): v for k, v in request.headers.items()}))
        if request.path.startswith("/websockify"):
            return None                      # a websocket upgrade: go on to the handler
        return connection.respond(200, f"stub:{self.name}:{request.path}")

    def _handler(self, ws) -> None:
        self.subprotocols.append(ws.subprotocol)
        try:
            for message in ws:
                self.received.append(message)
                ws.send(message)
        finally:
            self.closed.set()

    def stop(self) -> None:
        self.server.shutdown()

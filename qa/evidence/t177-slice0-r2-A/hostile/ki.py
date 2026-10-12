"""KeyboardInterrupt / SystemExit propagation out of _answers_as; finally-block + watchdog hygiene."""
from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl  # noqa: E402
from hl import PATH, Listener, good_json, http_head  # noqa: E402

launch = hl.launch


def good(c):
    c.request(); j = good_json(c.port); c.send(http_head(len(j)) + j); c.wait(0.5)


def slow(c):  # holds the socket so the exception happens mid-read
    c.request(); c.send(http_head(60000)); c.wait(3)


class RecTimer(threading.Timer):
    made: list = []

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.cancel_called = False
        RecTimer.made.append(self)

    def cancel(self):
        self.cancel_called = True
        super().cancel()


closes = []
orig_close = http.client.HTTPConnection.close


def rec_close(self):
    closes.append(1)
    return orig_close(self)


http.client.HTTPConnection.close = rec_close
orig_Timer = threading.Timer
orig_read1 = http.client.HTTPResponse.read1
orig_readinto = socket.SocketIO.readinto
orig_request = http.client.HTTPConnection.request
orig_getresponse = http.client.HTTPConnection.getresponse


def raiser(exc):
    def f(*a, **k):
        raise exc()
    return f


PATCHES = {
    "read1 -> KeyboardInterrupt": (http.client.HTTPResponse, "read1", raiser(KeyboardInterrupt), good),
    "read1 -> SystemExit": (http.client.HTTPResponse, "read1", raiser(SystemExit), good),
    "SocketIO.readinto (header read) -> KeyboardInterrupt": (socket.SocketIO, "readinto", raiser(KeyboardInterrupt), slow),
    "SocketIO.readinto (header read) -> SystemExit": (socket.SocketIO, "readinto", raiser(SystemExit), slow),
    "HTTPConnection.request -> KeyboardInterrupt": (http.client.HTTPConnection, "request", raiser(KeyboardInterrupt), good),
    "HTTPConnection.getresponse -> SystemExit": (http.client.HTTPConnection, "getresponse", raiser(SystemExit), good),
}
rows = []
for name, (obj, attr, repl, beh) in PATCHES.items():
    lst = Listener(beh)
    base = set(threading.enumerate())
    RecTimer.made.clear(); closes.clear(); hl.reset_client()
    threading.Timer = RecTimer
    orig = getattr(obj, attr)
    setattr(obj, attr, repl)
    t0 = time.monotonic()
    outcome = "returned (no propagation!)"
    try:
        launch._answers_as(lst.port, PATH)
    except BaseException as e:  # noqa
        outcome = "propagated " + type(e).__name__
    dt = time.monotonic() - t0
    setattr(obj, attr, orig)
    threading.Timer = orig_Timer
    time.sleep(0.1)
    row = dict(case=name, outcome=outcome, wall=round(dt, 3),
               timers_created=len(RecTimer.made), cancel_called=all(t.cancel_called for t in RecTimer.made),
               conn_close_calls=len(closes), client_sock_closed=all(s.fileno() == -1 for s in hl.SOCKS),
               timer_threads_alive=[t.name for t in RecTimer.made if t.is_alive()],
               foreign_threads=hl.foreign_threads(base))
    rows.append(row)
    print(row, flush=True)
    lst.stop()
json.dump(rows, open(sys.argv[1], "w"), indent=1)

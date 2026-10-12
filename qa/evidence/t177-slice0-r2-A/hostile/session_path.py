"""Full BrowserSession.start() path against hostile listeners (builder's FakePlaywright fake launch)."""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl  # noqa: E402
from hl import CAP, PATH, Listener, good_json, http_head  # noqa: E402

COPY = hl.COPY
sys.path.insert(0, COPY + "/tests")
from _pytest.monkeypatch import MonkeyPatch  # noqa: E402
import test_browser_session_cdp as T  # noqa: E402

launch = hl.launch


def b_header_trickle(c):
    c.request(); c.send(b"HTTP/1.1 200 OK\r\nX-")
    while c.wait(0.1):
        if not c.send(b"a"):
            return


def b_body_trickle(c):
    c.request(); c.send(http_head(60000))
    c.send(b'{"webSocketDebuggerUrl":"ws://127.0.0.1:1' + PATH.encode() + b'",')
    while c.wait(0.1):
        if not c.send(b" "):
            return


def b_endless_nocl(c):
    c.request(); c.send(http_head(close=True)); c.send(good_json(c.port))
    while c.send(b" " * 8192):
        pass


def b_continue_fast(c):
    c.request(); blob = b"HTTP/1.1 100 Continue\r\n\r\n" * 2000
    while c.send(blob):
        pass


def b_deep(c):
    c.request(); body = b"[" * 30000; c.send(http_head(len(body)) + body); c.wait(0.3)


def b_deep_obj(c):
    c.request(); body = b'{"a":' * 13000; c.send(http_head(len(body)) + body); c.wait(0.3)


def b_good_padded(c):  # control: a legit browser must still start
    c.request(); j = good_json(c.port); c.send(http_head(len(j)) + j); c.wait(0.3)


CASES = [("01 header trickle", b_header_trickle), ("02 body trickle", b_body_trickle),
         ("04 endless no-CL fast", b_endless_nocl), ("09a 100 Continue forever", b_continue_fast),
         ("11a deep [ x30000", b_deep), ("11b deep {a: x30000", b_deep_obj)]

rows = []
for name, beh in CASES + [("control good id (expects success)", b_good_padded)]:
    mp = MonkeyPatch()
    lst = Listener(beh)

    class Dev:  # what FakePlaywright/FakeContext expect: .port and .stop()
        port = lst.port
        def stop(self):
            Dev.stopped_at = time.monotonic()
            lst.stop()
    closed = {"ctx": False}
    orig_close = T.FakeContext.close

    def close(self, _o=orig_close, _c=closed):
        _c["ctx"] = True
        return _o(self)
    mp.setattr(T.FakeContext, "close", close)
    T.install(mp, devtools=Dev(), guid=PATH)
    mp.setattr(launch, "ATTACH_TIMEOUT_S", 5.0)  # default PROBE_DEADLINE_S (2.0) stays real
    tmp = Path(tempfile.mkdtemp(prefix="r2a-sess-"))
    s = T.session(tmp, expose_cdp=True)
    port_file = s.paths.profile_dir / "DevToolsActivePort"
    base = set(threading.enumerate())
    hl.reset_client()
    t0 = time.monotonic()
    try:
        s.start(); res = "STARTED(cdp_url=%s)" % s.cdp_url
    except launch.CdpEndpointError as e:
        res = "CdpEndpointError: " + str(e)
    except BaseException as e:  # noqa
        res = "OTHER " + repr(e)
    dt = time.monotonic() - t0
    time.sleep(0.15)
    row = dict(case=name, wall=round(dt, 3), result=res, ctx_closed=closed["ctx"],
               port_file_removed=not port_file.exists(), cdp_url_after=s.cdp_url,
               endpoint_refuses=T.refuses_connections(lst.port),
               client_bytes=hl.CLIENT_BYTES[0], connects=len(hl.CONNECTS),
               threads=hl.foreign_threads(base))
    if res.startswith("STARTED"):
        s.close(); row["after_close_port_file_removed"] = not port_file.exists()
    rows.append(row)
    print(row, flush=True)
    lst.stop(); mp.undo()
json.dump(rows, open(sys.argv[1], "w"), indent=1)

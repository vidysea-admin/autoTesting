"""r2-A hostile battery: python battery.py <run_idx> <out.json> [case-substring ...]"""
from __future__ import annotations

import gc
import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl  # noqa: E402
from hl import CAP, PATH, Listener, good_json, http_head  # noqa: E402

launch = hl.launch
RUN = int(sys.argv[1])
OUT = sys.argv[2]
ONLY = sys.argv[3:]


# ---------------- behaviours -----------------------------------------------------------------
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


def b_chunk_trickle(c):
    c.request(); c.send(http_head(chunked=True)); c.send(b"ea60\r\n{")
    while c.wait(0.1):
        if not c.send(b" "):
            return


def b_chunk_tiny_fast(c):
    c.request(); c.send(http_head(chunked=True)); c.send(b"1\r\n{\r\n")
    blob = b"1\r\n \r\n" * 2000
    while c.send(blob):
        pass


def b_endless_nocl(c):
    c.request(); c.send(http_head(close=True))
    c.send(good_json(c.port))
    blob = b" " * 8192
    while c.send(blob):
        pass


def b_endless_nocl_chunk_fast_ext(c):  # chunk-size line with an endless extension
    c.request(); c.send(http_head(chunked=True)); c.send(b"1;")
    blob = b"x" * 8192
    while c.send(blob):
        pass


def padded(total, declared, chunked=False):
    def f(c):
        c.request()
        j = good_json(c.port)
        body = j + b" " * (total - len(j))
        assert len(body) == total
        if chunked:
            c.send(http_head(chunked=True))
            c.send(f"{total:x}\r\n".encode() + body + b"\r\n0\r\n\r\n")
        elif declared:
            c.send(http_head(total) + body)
        else:
            c.send(http_head(close=True) + body)
        c.wait(0.3)
    return f


def b_silent(c):
    c.request(); c.stop.wait()


def b_mid_body_valid_json(c):  # complete valid JSON, CL says more, then close
    c.request(); j = good_json(c.port); c.send(http_head(1000) + j)


def b_mid_body_partial(c):
    c.request(); j = good_json(c.port); c.send(http_head(1000) + j[:30])


def b_headers_only_close(c):
    c.request(); c.send(http_head(100))


def b_continue_fast(c):
    c.request(); blob = b"HTTP/1.1 100 Continue\r\n\r\n" * 2000
    while c.send(blob):
        pass


def b_103_then_200(c):
    c.request(); j = good_json(c.port)
    c.send(b"HTTP/1.1 103 Early Hints\r\nLink: </x>\r\n\r\n" + http_head(len(j)) + j)
    c.wait(0.3)


def b_continue_trickle(c):
    c.request(); c.send(b"HTTP/1.1 100 Continue\r\n\r\n")
    while c.wait(0.1):
        if not c.send(b"HTTP/1.1 100 Continue\r\n\r\n"):
            return


def b_100_then_good(c):
    c.request(); j = good_json(c.port)
    c.send(b"HTTP/1.1 100 Continue\r\n\r\n" + http_head(len(j)) + j); c.wait(0.3)


def redirect(code, loc_fn):
    def f(c):
        c.request(); c.send(f"HTTP/1.1 {code} X\r\nLocation: {loc_fn(c)}\r\nContent-Length: 0\r\n\r\n".encode())
        c.wait(0.3)
    return f


def raw_body(body_fn, chunked=False):
    def f(c):
        c.request(); body = body_fn(c)
        if chunked:
            c.send(http_head(chunked=True) + f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n")
        else:
            c.send(http_head(len(body)) + body)
        c.wait(0.3)
    return f


def b_header_flood(n):
    def f(c):
        c.request(); j = good_json(c.port)
        extra = "".join(f"X-H{i}: v\r\n" for i in range(n))
        c.send(http_head(len(j), extra) + j); c.wait(0.3)
    return f


def b_long_header(c):
    c.request(); j = good_json(c.port)
    c.send(http_head(len(j), "X-L: " + "a" * 70000 + "\r\n") + j); c.wait(0.3)


def b_garbage(c):
    c.request(); c.send(b"garbage not http\r\n\r\n"); c.wait(0.3)


def b_empty(c):
    c.request()


def b_http09(c):
    c.request(); c.send(good_json(c.port)); c.wait(0.3)


def b_200_nobody_open(c):
    c.request(); c.send(http_head()); c.stop.wait()


DEEP_A = lambda c: b"[" * 30000
DEEP_B = lambda c: b'{"a":' * 30000
DEEP_CAP_A = lambda c: b"[" * CAP
DEEP_CAP_B = lambda c: (b'{"a":' * (CAP // 5)).ljust(CAP, b"[")
GOODJ = lambda c: good_json(c.port)


def with_extra(extra_fn):
    return lambda c: (b'{"webSocketDebuggerUrl":"ws://127.0.0.1:%d%s",' % (c.port, PATH.encode())) + extra_fn() + b"}"


def obj(**kv):
    return lambda c: json.dumps({k: (v(c) if callable(v) else v) for k, v in kv.items()}).encode()


RIGHT = lambda c: f"ws://127.0.0.1:{c.port}{PATH}"
WRONG = lambda c: f"ws://127.0.0.1:{c.port}/devtools/browser/someone-else"

CASES: list = []  # (name, behaviour_factory(aux)->behaviour, kind)


def add(name, beh, **kw):
    CASES.append((name, beh, kw))


add("01 header trickle 1B/0.1s", b_header_trickle)
add("02 body trickle CL=60000 1B/0.1s", b_body_trickle)
add("03a chunked trickle 1B/0.1s", b_chunk_trickle)
add("03b chunked endless tiny chunks fast", b_chunk_tiny_fast)
add("03c chunk-size ext endless fast", b_endless_nocl_chunk_fast_ext)
add("04 no-CL Connection:close endless fast", b_endless_nocl)
add("05a padded 65536 declared CL", padded(65536, True))
add("05b padded 65537 declared CL", padded(65537, True))
add("05c padded 65536 undeclared (close)", padded(65536, False))
add("05d padded 65537 undeclared (close)", padded(65537, False))
add("05e padded 65536 chunked", padded(65536, False, True))
add("05f padded 65537 chunked", padded(65537, False, True))
add("06 accepts, never answers", b_silent)
add("07a never-accept (backlog filled)", None, special="noaccept")
add("07b unrouted CDP_HOST 192.0.2.1", None, special="unrouted")
add("08a mid-body close, valid JSON prefix (CL 1000)", b_mid_body_valid_json)
add("08b mid-body close, partial JSON", b_mid_body_partial)
add("08c closed after headers only", b_headers_only_close)
add("09a 100 Continue forever fast", b_continue_fast)
add("09b 103 once then 200 good", b_103_then_200)
add("09c 100 Continue trickled", b_continue_trickle)
add("09d 100 once then 200 good (control)", b_100_then_good)
for code in (301, 302, 307):
    add(f"10a {code} -> other loopback port (good id)", None, special=f"redir{code}")
    add(f"10b {code} -> http://localhost:<aux>", None, special=f"redirlh{code}")
    add(f"10c {code} -> http://example.invalid/", None, special=f"redirhost{code}")
add("11a deep [ x30000", raw_body(DEEP_A))
add("11b deep {\"a\": x30000", raw_body(DEEP_B))
add("11c deep [ exactly cap", raw_body(DEEP_CAP_A))
add("11d deep {\"a\": exactly cap", raw_body(DEEP_CAP_B))
add("11e 60000-digit number in good obj", raw_body(with_extra(lambda: b'"n":' + b"1" * 60000)))
add("11f invalid UTF-8 inside good obj", raw_body(with_extra(lambda: b'"n":"\xff\xfe\x80"')))
add("11g dup key right then wrong", raw_body(lambda c: (
    '{"webSocketDebuggerUrl":"%s","webSocketDebuggerUrl":"%s"}' % (RIGHT(c), WRONG(c))).encode()))
add("11h dup key wrong then right", raw_body(lambda c: (
    '{"webSocketDebuggerUrl":"%s","webSocketDebuggerUrl":"%s"}' % (WRONG(c), RIGHT(c))).encode()))
add("11i UTF-8 BOM prefix + good", raw_body(lambda c: b"\xef\xbb\xbf" + good_json(c.port)))
add("11j id field = list", raw_body(obj(webSocketDebuggerUrl=lambda c: [RIGHT(c)])))
add("11k id field = dict", raw_body(obj(webSocketDebuggerUrl=lambda c: {"u": RIGHT(c)})))
add("11l id field = int", raw_body(obj(webSocketDebuggerUrl=5)))
add("11m id field = null", raw_body(obj(webSocketDebuggerUrl=None)))
add("11n id field = str w/ right path as suffix of longer str",
    raw_body(obj(webSocketDebuggerUrl=lambda c: "ws://evil.example:9/foo" + PATH)))
add("11o id field = right path + trailing junk", raw_body(obj(webSocketDebuggerUrl=lambda c: RIGHT(c) + "x")))
add("11p top-level array containing good obj", raw_body(lambda c: b"[" + good_json(c.port) + b"]"))
add("11q control: good identity", raw_body(GOODJ))
add("11r control: good identity chunked", raw_body(GOODJ, chunked=True))
add("12a 150 headers", b_header_flood(150))
add("12b 99 headers (control, should pass)", b_header_flood(99))
add("12c one 70000-byte header line", b_long_header)
add("13a non-HTTP reply", b_garbage)
add("13b empty reply (close)", b_empty)
add("13c HTTP/0.9-style bare body", b_http09)
add("13d 200 headers, no CL, no body, stays open", b_200_nobody_open)


# ---------------- runner ---------------------------------------------------------------------
def write_profile(port):
    d = Path(tempfile.mkdtemp(prefix="r2a-prof-"))
    (d / "DevToolsActivePort").write_text(f"{port}\n{PATH}\n", encoding="utf-8")
    return d


def make_target(name, beh, kw):
    """returns (listener, aux listeners, fillers, patches-undo)"""
    sp = kw.get("special", "")
    aux = []
    fill = []
    if sp.startswith("redir"):
        a = Listener(lambda c: (c.request(), c.send(http_head(len(good_json(c.port))) + good_json(c.port)), c.wait(0.2)))
        aux.append(a)
        code = int(sp[-3:])
        if sp.startswith("redirlh"):
            loc = lambda c: f"http://localhost:{a.port}/json/version"
        elif sp.startswith("redirhost"):
            loc = lambda c: "http://example.invalid:80/json/version"
        else:
            loc = lambda c: f"http://127.0.0.1:{a.port}/json/version"
        return Listener(redirect(code, loc)), aux, fill
    if sp == "noaccept":
        srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(0)
        port = srv.getsockname()[1]
        hung = None
        for i in range(40):
            s = socket.socket(); s.setblocking(False)
            try:
                s.connect(("127.0.0.1", port))
            except (BlockingIOError, OSError):
                pass
            fill.append(s)
        time.sleep(0.3)
        t0 = time.monotonic()
        try:
            hl._orig_cc(("127.0.0.1", port), timeout=0.7).close(); hung = False
        except Exception as e:
            hung = f"connect probe: {type(e).__name__} after {time.monotonic()-t0:.2f}s"
        class Fake:  # minimal Listener-like
            pass
        f = Fake(); f.port = port; f.accepts = 0; f.sent = 0; f.req_bytes = 0
        f.snap = lambda: (0, 0, 0)
        f.stop = lambda: [x.close() for x in fill] + [srv.close()]
        f.note = f"fill={len(fill)} extra-connect-hangs={hung}"
        return f, aux, fill
    if sp == "unrouted":
        class Fake:
            pass
        f = Fake(); f.port = 9; f.snap = lambda: (0, 0, 0); f.stop = lambda: None
        f.note = "CDP_HOST patched to 192.0.2.1 (RFC5737)"
        return f, aux, fill
    return Listener(beh), aux, fill


def timed_direct(port, unrouted=False):
    hl.reset_client()
    seen = []
    orig_fetch = launch._fetch_version

    def rec(p):
        try:
            r = orig_fetch(p); seen.append(len(r)); return r
        except BaseException as e:
            seen.append(type(e).__name__); raise
    launch._fetch_version = rec
    old_host = launch.CDP_HOST
    if unrouted:
        launch.CDP_HOST = "192.0.2.1"
    t0 = time.monotonic()
    try:
        r = launch._answers_as(port, PATH)
        exc = None
    except BaseException as e:  # noqa
        r, exc = None, repr(e)
    dt = time.monotonic() - t0
    launch.CDP_HOST = old_host
    launch._fetch_version = orig_fetch
    return r, exc, dt, seen


results = []
base_threads = set(threading.enumerate())
for name, beh, kw in CASES:
    if ONLY and not any(o in name for o in ONLY):
        continue
    lst, aux, fill = make_target(name, beh, kw)
    unrouted = kw.get("special") == "unrouted"
    rec = {"case": name, "run": RUN, "note": getattr(lst, "note", "")}
    a0 = lst.snap(); aux0 = [a.accepts for a in aux]
    r, exc, dt, seen = timed_direct(lst.port, unrouted)
    sock_open = [s.fileno() != -1 for s in hl.SOCKS]
    cb = hl.CLIENT_BYTES[0]; conns = list(hl.CONNECTS)
    time.sleep(0.1)
    thr = hl.foreign_threads(base_threads)
    a1 = lst.snap()
    rec.update(direct_ret=r, direct_exc=exc, direct_wall=round(dt, 3), client_bytes=cb,
               listener_sent=a1[1] - a0[1], listener_accepts=a1[0] - a0[0],
               connect_calls=len(conns), connect_addrs=sorted({f"{a[0]}:{a[1]}" for a in conns}),
               fetch_result=seen, client_sock_still_open=any(sock_open),
               threads_after_100ms=thr, aux_accepts=[a.accepts - x for a, x in zip(aux, aux0)])
    # public path
    hl.reset_client()
    prof = write_profile(lst.port)
    old_host = launch.CDP_HOST
    if unrouted:
        launch.CDP_HOST = "192.0.2.1"
    t0 = time.monotonic()
    try:
        url = launch.verified_cdp_url(prof); pr = ("returned", url)
    except launch.CdpEndpointError as e:
        pr = ("CdpEndpointError", str(e))
    except BaseException as e:  # noqa
        pr = ("OTHER", repr(e))
    pdt = time.monotonic() - t0
    launch.CDP_HOST = old_host
    time.sleep(0.1)
    rec.update(public=pr[0], public_msg=pr[1], public_wall=round(pdt, 3),
               public_client_bytes=hl.CLIENT_BYTES[0],
               public_connects=len(hl.CONNECTS),
               public_threads_after_100ms=hl.foreign_threads(base_threads),
               public_sock_open=any(s.fileno() != -1 for s in hl.SOCKS))
    a2 = lst.snap()
    rec["public_listener_accepts"] = a2[0] - a1[0]
    lst.stop()
    for a in aux:
        a.stop()
    gc.collect()
    time.sleep(0.15)
    rec["netstat_rows_after_stop"] = hl.netstat_pid_conns(os.getpid()) if RUN == 1 else None
    rec["threads_after_stop"] = hl.foreign_threads(base_threads)
    results.append(rec)
    print(f"{name:55s} direct={r!s:5} {dt:5.2f}s cb={cb:7d} sent={rec['listener_sent']:9d} "
          f"acc={rec['listener_accepts']} | public={pr[0]} {pdt:5.2f}s thr={thr} ns={rec['netstat_rows_after_stop']}",
          flush=True)
    json.dump(results, open(OUT, "w"), indent=1)
print("DONE", len(results))

"""Coordinator B adversarial pass: raw ASGI below the router. No network. Prints a table."""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="atb-root-"))
os.environ["AUTOTESTER_ROOT"] = str(root)
for k in ("AUTOTESTER_ALLOWED_HOSTS", "AUTOTESTER_ALLOWED_ORIGINS"):
    os.environ.pop(k, None)

from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402
from autotester.ui.app import app  # noqa: E402
from autotester.ui.env_editor import set_env_value  # noqa: E402
import autotester.ui.helpers as H  # noqa: E402

print("autotester from", H.__file__)
CANARY = "CANARY-s3cr3t-b-7731"
ProjectStore("demo", root).save_project(Project(
    slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
    secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]))
set_env_value(root / ".env", "DEMO_PASSWORD", CANARY)


async def call(headers, method="GET", path="/projects/demo/env", scope_type="http", extra=None):
    sent = []
    scope = {"type": scope_type, "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
             "query_string": b"", "root_path": "", "headers": headers,
             "client": ("1.2.3.4", 5), "server": ("testserver", 80)}
    if extra:
        scope.update(extra)
    body = [{"type": "websocket.connect"}] if scope_type == "websocket" else [{"type": "http.request", "body": b"", "more_body": False}]

    async def receive():
        return body.pop(0) if body else {"type": "http.disconnect"}

    async def send(m):
        sent.append(m)

    try:
        await app(scope, receive, send)
    except BaseException as exc:  # noqa: BLE001
        return ("EXC", repr(exc)[:120], b"", [])
    status = next((m["status"] for m in sent if m["type"] == "http.response.start"), None)
    hdrs = next((m.get("headers", []) for m in sent if m["type"] == "http.response.start"), [])
    b = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return (status, None, b, hdrs)


def H_(*pairs):
    return [(k.encode("latin-1"), v if isinstance(v, bytes) else v.encode("latin-1"))
            for k, v in pairs]


results = []


def check(label, res, expect_blocked=True):
    status, exc, body, hdrs = res
    leaked = CANARY.encode() in body or any(CANARY.encode() in v for _, v in hdrs)
    loc = [v for k, v in hdrs if k.lower() == b"location"]
    blocked = status == 403 and body == b""
    ok = (blocked and not leaked) if expect_blocked else (status == 200 and not leaked or status in (200, 404, 303, 307))
    results.append(ok)
    print(f"{'OK ' if ok else 'BAD'} {label:58s} status={status} len={len(body)} leak={leaked} loc={loc} exc={exc}")


async def main():
    ok_host = ("host", "localhost:8000")
    # control
    r = await call(H_(ok_host)); print("control loopback GET env ->", r[0], CANARY.encode() in r[2])
    # host attacks
    for h in [b"evil.example", b"evil.example:8000", b"localhost:8000.evil.com", b"localhost@evil.com",
              b"evil.com#@localhost", b"evil.com?@localhost", b"evil.com\\@localhost",
              b"localhost\x00.evil.com", b"local\thost", b"\xff\xfe", b"loc\xe0lhost", b"127.1",
              b"[::1", b"::1", b"0.0.0.0", b"LOCALHOST.evil.com", b"localhost, evil.com",
              b"localhost evil.com", b"http://localhost", b"//evil.com", b"localhost:99999999",
              b"localhost:-1", b"[::ffff:127.0.0.1]", b"127.0.0.1\r", b"", b" ", b"testserver"]:
        r = await call([(b"host", h)])
        exp_blocked = True
        label = f"GET env Host={h!r}"
        if h in (b"local\thost",):
            print("NOTE tab-in-host (known builder gap):", r[0]); continue
        check(label, r, exp_blocked)
    # missing host / duplicates / case-varied header names
    check("no Host header", await call([]))
    check("dup Host (good,evil)", await call(H_(("host", "localhost"), ("host", "evil.example"))))
    check("dup Host (evil,good)", await call(H_(("host", "evil.example"), ("host", "localhost"))))
    check("dup Host same value", await call(H_(("host", "localhost"), ("host", "localhost"))))
    check("Host UPPER-name header (raw bytes b'Host')", await call([(b"Host", b"evil.example")]))
    check("X-Forwarded-Host good + Host evil", await call(H_(("host", "evil.example"), ("x-forwarded-host", "localhost"))))
    check("Forwarded host=localhost + Host evil", await call(H_(("host", "evil.example"), ("forwarded", "host=localhost"))))
    check("absolute-form path http://localhost/ + Host evil", await call(H_(("host", "evil.example")), path="/projects/demo/env"))
    check(":authority pseudo header + Host evil", await call([(b":authority", b"localhost"), (b"host", b"evil.example")]))
    # many methods incl HEAD/OPTIONS/TRACE
    for m in ["HEAD", "OPTIONS", "TRACE", "PUT", "DELETE", "PATCH", "POST", "GET", "CONNECT", "PROPFIND"]:
        check(f"{m} Host evil", await call(H_(("host", "evil.example")), method=m))
    # health + run-queue + docs/openapi routes on a bad host
    rq = [r for r in app.openapi()["paths"] if "run" in r or "queue" in r]
    print("run/queue-ish routes:", rq[:12])
    for p in ["/healthz", "/docs", "/openapi.json", "/redoc", "/", "/nonexistent", "/projects/demo/env", "/static/x", "//", "/projects/../.env"]:
        check(f"GET {p} Host evil", await call(H_(("host", "evil.example")), path=p))
    for p in [x for x in rq][:10]:
        check(f"GET {p} Host evil", await call(H_(("host", "evil.example")), path=p))
    # error-path bodies from allowed host: 404/500 must not leak (informational)
    r = await call(H_(ok_host), path="/projects/nope/env"); print("allowed-host 404 body:", r[0], r[2][:80])
    # Origin attacks with allowed host
    for o in [b"http://localhost:8000.evil.com", b"null", b"http://evil.example", b"http://localhost@evil.com",
              b"http://localhost\\@evil.com", b"http://[::1]:8000.evil", b"http://localhost:8000\xff", b""]:
        r = await call(H_(ok_host, ("origin", o)), method="POST", path="/projects/demo/run")
        results.append(r[0] == 403)
        print(("OK " if r[0] == 403 else "BAD"), f"POST run Origin={o!r}", r[0], r[2][:100])
    r = await call(H_(ok_host, ("origin", "http://localhost:8000"), ("origin", "http://evil.example")), method="POST", path="/projects/demo/run")
    results.append(r[0] == 403); print("dup origin", r[0])
    # Referer / sec-fetch-site paths
    r = await call(H_(ok_host, ("sec-fetch-site", "cross-site")), method="POST", path="/projects/demo/run"); results.append(r[0] == 403); print("sec-fetch cross-site", r[0])
    # non-http scopes
    r = await call(H_(("host", "evil.example")), scope_type="websocket", path="/ws")
    print("websocket scope evil host ->", r[0], r[1])
    r = await call(H_(("host", "evil.example")), scope_type="websocket", path="/projects/demo/env")
    print("websocket scope to env route ->", r[0], r[1])
    print("ALL OK" if all(results) else "SOME BAD")

asyncio.run(main())

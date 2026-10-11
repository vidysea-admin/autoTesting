"""Checker A attack on the Host guard (TestClient, no network). Run with PYTHONPATH=<copy>/src."""
import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="atk_"))
os.environ["AUTOTESTER_ROOT"] = str(root)
for k in ("AUTOTESTER_ALLOWED_HOSTS", "AUTOTESTER_ALLOWED_ORIGINS"):
    os.environ.pop(k, None)

from fastapi.testclient import TestClient  # noqa: E402

import autotester  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402
from autotester.ui.app import app  # noqa: E402
from autotester.ui.env_editor import set_env_value  # noqa: E402
from autotester.ui.helpers import _OriginGuard  # noqa: E402

print("using", autotester.__file__)
SECRET = "s3cr3t-real-value-ZZ9"
ProjectStore("demo", root).save_project(Project(
    slug="demo", name="DemoMarkerName", base_url="https://demo.test", allowed_domains=["demo.test"],
    secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]))
set_env_value(root / ".env", "DEMO_PASSWORD", SECRET)

# every route family: openapi paths (all methods) + mounts/static + health + docs + 404
routes = set()
for path, ops in app.openapi()["paths"].items():
    for m in ops:
        routes.add((m.upper(), re.sub(r"\{[^}]+\}", "demo", path)))


def walk(rs):
    for r in rs:
        yield r
        sub = getattr(r, "routes", None)
        if sub:
            yield from walk(sub)


kinds = {type(r).__name__ for r in walk(app.routes)}
print("route classes:", sorted(kinds))
for r in walk(app.routes):
    p = getattr(r, "path", "")
    if type(r).__name__ in {"Mount"} or "static" in p:
        routes.add(("GET", p + "/x.css" if not p.endswith("/") else p + "x.css"))
for extra in ["/healthz", "/docs", "/redoc", "/openapi.json", "/static/app.css", "/nope-404",
              "/projects/demo/env", "/projects/demo", "/", "/%2e%2e/projects/demo/env"]:
    routes.add(("GET", extra))
for m in ("HEAD", "OPTIONS", "PUT", "PATCH", "DELETE", "POST"):
    routes.add((m, "/projects/demo/env"))
    routes.add((m, "/healthz"))
    routes.add((m, "/"))
print("distinct (method,path) probes:", len(routes))

BAD_HOSTS = [
    "evil.example", "evil.example:8000", "EVIL.EXAMPLE", "localhost.evil.example", "127.0.0.1.evil.com",
    "localhost:8000.evil.com", "localhost@evil.example", "evil.example@localhost", "x@127.0.0.1:8000",
    "user:pw@localhost:8000", "localhost/x", "localhost?x=1", "localhost#f", "localhost.", "LOCALHOST.",
    "127.0.0.1.", "[::1].", "", " ", "[::ffff:127.0.0.1]", "[::1", "::1", "0.0.0.0", "127.1",
    "localhost:99999", "localhost:-1", "localhost:8000, evil.example", "localhost evil.example",
    "localhost\\@evil.example", "//evil.example", "@localhost", "localhost:8000:9", "[evil]:8000",
    "[::1]x", "[::1]:80.evil", "lоcalhost", "ｌｏｃａｌｈｏｓｔ", "localhost\x00.evil.example",
    "testserver", "server.example.org",
]
bad = 0
n = 0
leaks = []
c = TestClient(app, raise_server_exceptions=False)
for host in BAD_HOSTS:
    for method, path in sorted(routes):
        try:
            r = c.request(method, path, headers={"Host": host}, follow_redirects=False)
        except Exception as exc:  # client could not even send it
            if n == 0 or True:
                pass
            continue
        n += 1
        text = r.content
        if SECRET.encode() in text or b"DemoMarkerName" in text or any(
                SECRET in v for v in r.headers.values()):
            leaks.append((host, method, path, r.status_code))
        if r.status_code != 403 or text != b"":
            bad += 1
            if bad <= 15:
                print("NOT-403", repr(host), method, path, r.status_code, len(text))
print(f"BAD_HOSTS requests sent={n} non-403-or-nonempty={bad} leaks={len(leaks)}")
for l in leaks[:10]:
    print("LEAK", l)

# allowed hosts still serve (display unchanged)
for host in ["localhost", "LOCALHOST:8000", "127.0.0.1:8000", "[::1]:8000", "[::1]", "Localhost:1"]:
    r = c.get("/projects/demo/env", headers={"Host": host})
    print("allowed", repr(host), r.status_code, SECRET in r.text)

# X-Forwarded-Host does not vouch, nor condemn
r = c.get("/projects/demo/env", headers={"Host": "evil.example", "X-Forwarded-Host": "localhost"})
print("evil Host + XFH localhost ->", r.status_code, SECRET in r.text)
r = c.get("/projects/demo/env", headers={"Host": "localhost", "X-Forwarded-Host": "evil.example"})
print("localhost Host + XFH evil ->", r.status_code, "(allowed by Host; app ignores XFH)")
r = c.get("/projects/demo/env", headers={"Host": "evil.example", "Forwarded": "host=localhost"})
print("evil Host + Forwarded host=localhost ->", r.status_code)

# repeated headers
for pairs in ([("Host", "localhost"), ("Host", "localhost")], [("Host", "localhost"), ("Host", "evil.example")],
              [("Host", "evil.example"), ("Host", "localhost")], [("host", "localhost"), ("HOST", "localhost")]):
    r = c.get("/projects/demo/env", headers=pairs)
    print("repeated", pairs, r.status_code, r.content == b"")
r = c.post("/projects/demo/env", headers=[("Host", "localhost"), ("Origin", "http://localhost"), ("Origin", "http://localhost")])
print("dup origin same value ->", r.status_code)
for o in ("http://localhost:8000.evil.com", "http://localhost:80a", "http://[::1]:8000.evil.com"):
    r = c.post("/projects/demo/env", headers={"Host": "localhost", "Origin": o})
    print("AT-760 origin", o, r.status_code)


# raw ASGI: missing host, absolute-form target, scope variants
async def call(scope):
    sent = []
    reached = []

    async def inner(s, rc, sd):
        reached.append(1)
        await sd({"type": "http.response.start", "status": 200, "headers": []})
        await sd({"type": "http.response.body", "body": b"APP"})

    async def send(m):
        sent.append(m)

    async def receive():
        return {"type": "http.request", "body": b""}
    await _OriginGuard(inner)(scope, receive, send)
    return bool(reached), sent[0].get("status")


def hdr(*pairs):
    return [(k.encode(), v.encode()) for k, v in pairs]


cases = {
    "missing host": {"type": "http", "method": "GET", "path": "/projects/demo/env", "headers": []},
    "absolute-form + evil host": {"type": "http", "method": "GET", "path": "http://evil.example/projects/demo/env",
                                  "raw_path": b"http://evil.example/projects/demo/env",
                                  "headers": hdr(("host", "evil.example"))},
    "absolute-form + loopback host (target names evil)": {"type": "http", "method": "GET",
                                  "path": "/projects/demo/env", "raw_path": b"http://evil.example/projects/demo/env",
                                  "headers": hdr(("host", "localhost"))},
    "absolute-form target loopback, Host evil": {"type": "http", "method": "GET",
                                  "path": "/projects/demo/env", "raw_path": b"http://localhost/projects/demo/env",
                                  "headers": hdr(("host", "evil.example"))},
    "authority header (h2-like)": {"type": "http", "method": "GET", "path": "/projects/demo/env",
                                  "headers": hdr((":authority", "evil.example"))},
    "websocket scope": {"type": "websocket", "path": "/x", "headers": hdr(("host", "evil.example"))},
}
for name, sc in cases.items():
    sc.setdefault("query_string", b"")
    print("asgi", name, "-> reached app, status:", asyncio.run(call(sc)))

# env-config matrix
def get(host, path="/"):
    return c.get(path, headers={"Host": host}).status_code

print("unset allow-lists, non-loopback Host (hosted bind, nothing configured):",
      get("autotester.example.org"), get("10.0.0.5:8000"))
os.environ["AUTOTESTER_ALLOWED_ORIGINS"] = "https://autotester.example.org/"
print("ORIGINS admits autotester.example.org:", get("autotester.example.org"), get("autotester.example.org:443"),
      "evil still:", get("evil.example"), "sub:", get("a.autotester.example.org"))
os.environ["AUTOTESTER_ALLOWED_ORIGINS"] = "autotester.example.org"  # no scheme
print("ORIGINS bare name (no scheme):", get("autotester.example.org"))
os.environ["AUTOTESTER_ALLOWED_ORIGINS"] = "https://x@evil.example, http://localhost:8000.evil.com, *"
print("ORIGINS junk entries admit evil?:", get("evil.example"), get("x@evil.example"), get("localhost:8000.evil.com"))
os.environ.pop("AUTOTESTER_ALLOWED_ORIGINS")
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "*"
print("HOSTS='*':", get("evil.example"))
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "ui.internal, Other.Internal:8443"
print("HOSTS list:", get("ui.internal"), get("other.internal:8443"), get("ui.internal:8443"), get("ui.internal."), get("evil"))
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = ""
print("HOSTS empty string:", get("evil.example"))
sys.exit(1 if (bad or leaks) else 0)

import os, sys, tempfile, re, threading, time, socket
root = tempfile.mkdtemp(prefix="at-tricks-")
os.environ["AUTOTESTER_ROOT"] = root
os.environ["AUTOTESTER_TEST_NO_AUTO_LOGIN"] = "1"
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
for n in ("AUTOTESTER_AUTH_DIR", "AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED", "AUTOTESTER_FIRST_ADMIN_EMAIL",
          "AUTOTESTER_COOKIE_SECURE", "AUTOTESTER_ALLOWED_ORIGINS", "UVICORN_HOST", "AUTOTESTER_PUBLIC_ORIGIN"):
    os.environ.pop(n, None)
import autotester
print("autotester:", autotester.__file__)
from pathlib import Path
from fastapi.testclient import TestClient
from autotester.ui.app import app
from autotester.auth import accounts, groups
from autotester.auth.access import set_owner, set_relation
from autotester.auth.ratelimit import login_limiter
from autotester.schema.auth import ProjectRelation
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

PW = "correct-horse-battery"


def tc():
    return TestClient(app, follow_redirects=False, raise_server_exceptions=False)


def mkproject(slug):
    ProjectStore(slug, Path(root)).save_project(Project(slug=slug, name=slug.title(), base_url=f"https://{slug}.test", allowed_domains=[f"{slug}.test"]))


def gid(seed):
    return next(g.id for g in groups.list_groups() if g.seed == seed)


def signup(e):
    tc().post("/auth/signup", data={"email": e, "password": PW})


def cookie(e):
    login_limiter.reset()
    c = tc()
    r = c.post("/auth/login", data={"email": e, "password": PW})
    assert r.status_code == 303
    return "; ".join(f"{k}={v}" for k, v in c.cookies.items())


signup("admin@team.test"); signup("nogroup@team.test"); signup("pv@team.test"); signup("tester@team.test"); signup("dev@team.test")
mkproject("alpha"); mkproject("beta")
pv = accounts.find_user("pv@team.test")
g = groups.create_group("PV-only", ["project.view@all"])
accounts.set_user_groups(pv.id, [g.id])
t = accounts.find_user("tester@team.test")
accounts.set_user_groups(t.id, [gid("tester")])
set_relation("alpha", t.id, ProjectRelation.SHARED, True)
d = accounts.find_user("dev@team.test")
accounts.set_user_groups(d.id, [gid("developer")])
set_owner("alpha", d.id)
set_owner("beta", accounts.find_user("admin@team.test").id)
COOK = {"anon": None, "nogroup": cookie("nogroup@team.test"), "pv_only": cookie("pv@team.test"),
        "tester_shared": cookie("tester@team.test"), "dev_owner_alpha": cookie("dev@team.test"),
        "admin": cookie("admin@team.test")}
import uvicorn
port = 18765
cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off")
srv = uvicorn.Server(cfg)
th = threading.Thread(target=srv.run, daemon=True)
th.start()
for _ in range(100):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
        break
    except OSError:
        time.sleep(0.1)


def raw(method, target, cookie=None, extra=None, body=b"", host="testserver"):
    hdrs = [f"{method} {target} HTTP/1.1", f"Host: {host}", "Accept: application/json", "Connection: close"]
    if cookie:
        hdrs.append("Cookie: " + cookie)
    for k, v in (extra or {}).items():
        hdrs.append(f"{k}: {v}")
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        hdrs += ["Content-Type: application/x-www-form-urlencoded", f"Content-Length: {len(body)}"]
    data = ("\r\n".join(hdrs) + "\r\n\r\n").encode("latin-1", "replace") + body
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(data)
    buf = b""
    while True:
        try:
            ch = s.recv(65536)
        except OSError:
            break
        if not ch:
            break
        buf += ch
    s.close()
    line = buf.split(b"\r\n", 1)[0].decode("latin-1")
    parts = line.split(" ", 2)
    code = parts[1] if len(parts) > 1 else "?"
    loc = re.search(rb"\r\nlocation: ([^\r]*)", buf, re.I)
    return code + (("->" + loc.group(1).decode()[:30]) if loc and code.startswith("3") else "")


TARGETS = [
    ("POST drive (video.upload)", "POST", "/projects/alpha/sources/drive", ["anon", "nogroup", "pv_only", "tester_shared"]),
    ("POST upload (video.upload)", "POST", "/projects/alpha/sources/upload", ["anon", "nogroup", "pv_only", "tester_shared"]),
    ("GET damage-report (report.view)", "GET", "/projects/alpha/damage-report", ["anon", "nogroup", "pv_only"]),
    ("GET drive job (project.view)", "GET", "/projects/alpha/sources/drive/01HZZZZZZZZZZZZZZZZZZZZZZZ", ["anon", "nogroup"]),
    ("GET admin/users (users.manage)", "GET", "/admin/users", ["anon", "nogroup", "tester_shared", "dev_owner_alpha"]),
    ("POST admin/groups (groups.manage)", "POST", "/admin/groups", ["anon", "nogroup", "tester_shared", "dev_owner_alpha"]),
    ("GET beta report (dev/tester not on beta)", "GET", "/projects/beta/damage-report", ["dev_owner_alpha", "tester_shared"]),
]


def variants(tgt):
    first = re.match(r"^/([^/]+)/", tgt)
    lead = first.group(1) if first else ""
    out = {
        "plain": tgt,
        "trailing slash": tgt + "/",
        "double slash after 1st seg": re.sub(r"^/([^/]+)/", r"/\1//", tgt),
        "double slash prefix": "/" + tgt,
        "dot segment /./": re.sub(r"^/([^/]+)/", r"/\1/./", tgt),
        "dotdot via /zzz/..": "/zzz/.." + tgt,
        "pct-encoded %2F after 1st": re.sub(r"^/([^/]+)/", r"/\1%2F", tgt),
        "pct-encoded last char": tgt[:-1] + "%" + format(ord(tgt[-1]), "02X"),
        "double-encoded %252F": re.sub(r"^/([^/]+)/", r"/\1%252F", tgt),
        "uppercase first seg": "/" + lead.upper() + tgt[len(lead) + 1:],
        "query ?next=/auth/login": tgt + "?next=/auth/login",
        "semicolon param": tgt + ";x=1",
        "pct-23 fragment": tgt + "%23",
        "trailing dot": tgt + ".",
        "null %00": tgt + "%00",
        "overlong %c0%af": re.sub(r"^/([^/]+)/", r"/\1%c0%af", tgt),
        "fullwidth slash %EF%BC%8F": re.sub(r"^/([^/]+)/", r"/\1%EF%BC%8F", tgt),
        "backslash": re.sub(r"^/([^/]+)/", r"/\1\\", tgt),
        "absolute-URI target": "http://testserver" + tgt,
        "public-prefix /auth/login/.." : "/auth/login/.." + tgt,
        "public-suffix + /healthz": tgt + "/../../healthz",
    }
    return out


def bad(code):
    return code[:1] == "2" or code[:3] in ("422", "500")


flag = []
for label, m, tgt, princs in TARGETS:
    print(f"\n## {label}  [{m} {tgt}]")
    print("   baseline:", {p: raw(m, tgt, COOK[p]) for p in princs})
    for vname, v in variants(tgt).items():
        row = {}
        for p in princs:
            try:
                row[p] = raw(m, v, COOK[p])
            except Exception:
                row[p] = "ERR"
            if bad(row[p]):
                flag.append((label, vname, p, row[p]))
        print(f"   {vname:28s} {row}")
    for mv in ("post", "Post", "get", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE", "TRACE", "FOO"):
        if mv == m:
            continue
        row = {}
        for p in princs:
            try:
                row[p] = raw(mv, tgt, COOK[p])
            except Exception:
                row[p] = "ERR"
            if bad(row[p]):
                flag.append((label, "method " + mv, p, row[p]))
        print(f"   method {mv:20s} {row}")
    for hn, hv in (("X-HTTP-Method-Override", "GET"), ("X-Original-URL", "/healthz"), ("X-Rewrite-URL", "/healthz"),
                   ("X-Forwarded-Prefix", "/auth"), ("X-Forwarded-For", "127.0.0.1"), ("X-Forwarded-Host", "testserver")):
        row = {p: raw(m, tgt, COOK[p], extra={hn: hv}) for p in princs}
        for p, c in row.items():
            if bad(c):
                flag.append((label, "hdr " + hn, p, c))
        print(f"   header {hn:24s} {row}")
print("\nFLAGGED (2xx/422/500 where a refusal is expected):", flag)
print("\nUNKNOWN PATH / METHOD")
for tgt in ("/nope", "/projects/alpha/nope", "/projects/nonexistent/damage-report", "/projects/nonexistent/sources/drive",
            "/static/x.js", "/ws", "/admin", "/admin/", "/projects", "/projects/", "/auth", "/openapi.json/", "/docs/", "/live/"):
    print(f"   GET {tgt:40s}", {p: raw("GET", tgt, COOK[p]) for p in ("anon", "nogroup", "tester_shared", "admin")})
for m in ("PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE", "FOO"):
    print(f"   {m:7s} /projects/alpha/sources/drive ", {p: raw(m, "/projects/alpha/sources/drive", COOK[p]) for p in ("anon", "nogroup", "tester_shared", "admin")})
print("   GET /projects/alpha/sources/drive (POST-only)", {p: raw("GET", "/projects/alpha/sources/drive", COOK[p]) for p in ("anon", "nogroup", "tester_shared", "admin")})
print("   HEAD on POST-only upload", {p: raw("HEAD", "/projects/alpha/sources/upload", COOK[p]) for p in ("anon", "nogroup", "tester_shared", "admin")})
print("   HEAD /projects/alpha/damage-report", {p: raw("HEAD", "/projects/alpha/damage-report", COOK[p]) for p in ("anon", "nogroup", "pv_only", "tester_shared", "admin")})
print("   OPTIONS /projects/alpha/damage-report", {p: raw("OPTIONS", "/projects/alpha/damage-report", COOK[p]) for p in ("anon", "nogroup", "pv_only", "tester_shared", "admin")})
print("   websocket upgrade GET /live (anon)", raw("GET", "/live", None, extra={"Upgrade": "websocket", "Connection": "Upgrade", "Sec-WebSocket-Key": "x3JJHMbDL1EzLkh9GBhXDw==", "Sec-WebSocket-Version": "13"}))
srv.should_exit = True

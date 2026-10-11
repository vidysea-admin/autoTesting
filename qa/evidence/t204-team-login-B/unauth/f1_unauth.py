"""Family 1: unauthenticated reach. Usage: python f1_unauth.py <loopback|hosted> <scratch>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C

mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402

PUBLIC_GET = {"/auth/login", "/auth/signup", "/healthz"}
PUBLIC_POST = {"/auth/login", "/auth/signup"}
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]
HTML = [("accept", "text/html,application/xhtml+xml")]
JSON = [("accept", "application/json")]
findings, rows = [], []
MARK = "ZZMARK<script>1</script>"


def check(label, method, path, resp, accept_html, public_ok=False, mark=None):
    row = {"label": label, "m": method, "p": path, "html": accept_html, "status": resp.status,
           "loc": resp.location, "exc": resp.exc}
    rows.append(row)
    bad = []
    if resp.exc:
        bad.append("exception " + resp.exc)
    lk = C.leaks(resp)
    if lk:
        bad.append(f"sentinel leaked {lk}")
    if mark and (mark in resp.text or "<script>" in (resp.location or "")):
        bad.append("input echoed")
    if not public_ok:
        if accept_html:
            ok = resp.status == 302 and (resp.location or "").startswith("/auth/login?next=")
        else:
            ok = resp.status == 401 and resp.text.strip() == '{"detail":"authentication required"}'
        if not ok:
            bad.append(f"not refused: status {resp.status} loc {resp.location} body[:80]={resp.text[:80]!r}")
        loc = resp.location or ""
        if "evil" in loc or "ZZQ" in loc:
            bad.append("query leaked into Location")
    if bad:
        findings.append({"label": label, "m": method, "p": path, "html": accept_html, "bad": bad})


def is_public(method, path):
    verb = "GET" if method == "HEAD" else method
    return (verb == "GET" and path in PUBLIC_GET) or (verb == "POST" and path in PUBLIC_POST)


# ---- window A: every non-public request must change nothing
snap0 = C.snapshot(scratch)
n0 = C.STATE["n"]
rt = C.routes()
paths = set()
for ms, tpl, cls in rt:
    for real in (True, False):
        paths.add(C.fill(tpl, ids, real))
paths |= {"/", "/static/x.css", "/video/x", "/report/x", "/download/x", "/upload", "/health", "/live",
          "/novnc/", "/vnc.html", "/websockify", "/auth/check", "/openapi.json", "/docs", "/redoc",
          "/favicon.ico", "/docs/oauth2-redirect", "/projects", "/projects/", "/admin", "/admin/"}
table = []
for p in sorted(paths):
    for m in METHODS:
        for html in (True, False):
            if is_public(m, p):
                continue
            r = C.call(m, p, HTML if html else JSON, query="q=ZZQ&next=http://evil.example")
            check("enum", m, p, r, html)
paths_ct = len(paths)

# variants of a protected target and public targets
variants = ["/Auth/login", "/AUTH/LOGIN/", "/auth/login/", "/auth/login//", "/projects/", "/projects",
            "/Projects/alpha/env", "//projects/alpha/env", "///projects/alpha/env", "/projects//alpha/env",
            "/projects/alpha//env", "/projects/./alpha/env", "/projects/alpha/../alpha/env",
            "/auth/login/../projects/alpha/env", "/auth/login%2f..%2fprojects/alpha/env",
            "/auth/login%2F..%2Fprojects%2Falpha%2Fenv", "/projects%2falpha%2fenv", "/projects%2Falpha/env",
            "/projects/alpha%2fenv", "/projects/%2e%2e/projects/alpha/env", "/%2e%2e/projects/alpha/env",
            "/projects/alpha/env%00", "/projects/alpha/env%00.png", "/auth/login%00", "/auth/login%00/../projects",
            "/projects/alpha\\env", "/projects\\alpha\\env", "\\projects\\alpha\\env", "/auth\\login",
            "/auth/login%0a", "/auth/login%0d%0a", "/projects/alpha/env%0a", "/healthz%0a", "/healthz/", "/healthz%2f",
            "/healthz;x", "/healthz%00", "/healthz.json", "/auth/login.", "/auth/login%20", "/auth/login%09",
            "/auth/signup/", "/auth/signup%0a", "/auth/logout", "/auth/waiting", "/auth/login;/../admin/users",
            "/projects/alpha/env;.css", "/projects/alpha/env/", "/projects/alpha/env.json",
            "/projects/alpha/runs/" + ids["run"] + "/videos/video.webm",
            "/projects/alpha/runs/" + ids["run"] + "/videos/..%2f..%2f..%2f.env",
            "/projects/alpha/runs/" + ids["run"] + "/videos/%2e%2e/%2e%2e/.env",
            "/projects/alpha/frames/s1/..%2f..%2f.env", "/.env", "/%2e%2eenv", "/.auth/auth.sqlite3",
            "/projects/alpha/project.json", "/projects/alpha/%2e%2e/%2e%2e/.env",
            "/" + MARK, "/projects/" + MARK + "/env", "/admin/users/1/delete", "/admin/users/1%2fdelete",
            "/auth/login?next=//evil.example", "/openapi.json/", "/docs/", "/redoc/", "/OPENAPI.JSON"]
for p in variants:
    for m in ("GET", "POST", "HEAD", "OPTIONS", "DELETE"):
        for html in (True, False):
            if is_public(m, p):
                continue
            r = C.call(m, p, HTML if html else JSON, query="")
            check("variant", m, p, r, html, mark="ZZMARK")

bypass = [[("x-original-url", "/auth/login")], [("x-rewrite-url", "/auth/login")],
          [("x-forwarded-prefix", "/auth/login")], [("x-forwarded-path", "/auth/login")],
          [("x-forwarded-for", "127.0.0.1")], [("x-real-ip", "127.0.0.1")],
          [("x-forwarded-proto", "https")], [("x-forwarded-host", "localhost")],
          [("x-http-method-override", "GET")], [("x-method-override", "GET")],
          [("authorization", "Bearer abc"), ("x-auth-request-user", "admin")],
          [("x-forwarded-user", "admin-b@scratch.test"), ("remote-user", "admin")],
          [("cookie", "at_session=garbage")], [("cookie", "__Host-at_session=garbage")],
          [("cookie", "at_session=")], [("cookie", "at_session=" + "A" * 5000)],
          [("cookie", "at_session=1; at_session=2")], [("cookie", "session=admin; user=admin; admin=1")],
          [("referer", good := C.good_origin() + "/auth/login")], [("origin", C.good_origin())],
          [("sec-fetch-site", "same-origin")], [("x-original-url", "/healthz"), ("x-rewrite-url", "/healthz")]]
for hs in bypass:
    for target in ("/projects/alpha/env", "/admin/users", "/", "/projects/alpha/report.html"):
        for m in ("GET", "POST"):
            for html in (True, False):
                r = C.call(m, target, hs + (HTML if html else JSON))
                check("bypass-header " + ",".join(k for k, _ in hs), m, target, r, html)

# Host header variants unauthenticated on protected path
for hv in ("evil.example", "localhost.evil.com", "127.0.0.1.evil.io", "localhost:8000.evil.com", "testserver.evil.com",
           "TESTSERVER", "localhost@evil.example", "evil.example#@localhost", "[::1]:8000", "", "localhost\t"):
    r = C.call("GET", "/projects/alpha/env", HTML, host_override=hv)
    rows.append({"label": "host", "host": hv, "status": r.status, "loc": r.location, "leak": C.leaks(r)})
    if C.leaks(r):
        findings.append({"label": "host", "bad": ["sentinel leaked"], "host": hv})
r = C.call("GET", "/projects/alpha/env", HTML, with_host=False)
rows.append({"label": "host-absent", "status": r.status})
r = C.call("GET", "/projects/alpha/env", HTML + [("host", "testserver"), ("host", "evil.example")])
rows.append({"label": "host-dup", "status": r.status, "text": r.text[:60]})

snap1 = C.snapshot(scratch)
df = C.diff(snap0, snap1)
_a = scratch / ".work" / "audit.jsonl"
winA = {"requests": C.STATE["n"] - n0, "data_root_diff": df,
        "audit_lines_after_windowA": _a.read_text().strip().splitlines() if _a.exists() else []}

# ---- AU16 positive checks on public set
healthz = []
for html in (True, False):
    r = C.call("GET", "/healthz", HTML if html else JSON)
    healthz.append({"accept_html": html, "status": r.status, "body": r.text, "ctype": r.h("content-type")})
for hv in ("evil.example", "localhost:8000"):
    r = C.call("GET", "/healthz", JSON, host_override=hv)
    healthz.append({"host": hv, "status": r.status, "body": r.text})
pub = []
for p in ("/auth/login", "/auth/signup"):
    for m in ("GET", "HEAD", "OPTIONS"):
        r = C.call(m, p, HTML)
        pub.append({"m": m, "p": p, "status": r.status, "loc": r.location, "len": len(r.body),
                    "leak": C.leaks(r), "allow": r.h("allow")})

# ---- window B: public POSTs (bad login / bad signup) -> only an audit line may be written
login_limiter.reset(); signup_limiter.reset()
snapB0 = C.snapshot(scratch)
b = []
for p in ("/auth/login", "/auth/signup"):
    for body in (b"", b"email=nobody%40nowhere.test&password=wrong-wrong-wrong", b"email=%3Cb%3E&password=x"):
        r = C.call("POST", p, [("content-type", "application/x-www-form-urlencoded"),
                               ("origin", C.good_origin())] + HTML, body=body)
        b.append({"p": p, "body": body[:40].decode(), "status": r.status, "leak": C.leaks(r),
                  "echo_email": "nobody@nowhere" in r.text})
snapB1 = C.snapshot(scratch)
winB = {"diff": C.diff(snapB0, snapB1), "responses": b}
audit = scratch / ".work" / "audit.jsonl"
winB["audit_tail"] = audit.read_text().strip().splitlines()[-3:] if audit.exists() else []

C.dump("f1", {"mode": mode, "paths_enumerated": paths_ct, "routes": len(rt), "requests_total": C.STATE["n"],
              "findings": findings, "windowA": winA, "healthz": healthz, "public": pub, "windowB": winB,
              "rows_sample": [r for r in rows if r["label"] in ("host", "host-absent", "host-dup")]})
print(mode, "requests", C.STATE["n"], "routes", len(rt), "paths", paths_ct, "findings", len(findings))
print("windowA diff", df, winA["audit_lines_after_windowA"][:6], len(winA["audit_lines_after_windowA"]))
for f in findings[:30]:
    print("FINDING", f)
print("healthz", healthz)
print("windowB", winB)

"""Family 2: signed-in user with NO group. Usage: python f2_nogroup.py <mode> <scratch>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import common as C
mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
ALLOWED = {("GET", "/auth/waiting"), ("GET", "/auth/login"), ("GET", "/auth/signup"), ("GET", "/healthz"),
           ("POST", "/auth/login"), ("POST", "/auth/signup")}
HTML = [("accept", "text/html")]; JSON = [("accept", "application/json")]
cookie = C.session_cookie(ids["nogroup"])
rt = C.routes()
app_pairs = {(m, p) for ms, p, _ in rt for m in ms}
n0 = C.STATE["n"]; snap0 = C.snapshot(scratch)
from collections import Counter
cnt = Counter(); odd = []; leaks = []
for ms, tpl, _ in rt:
    for real in (True, False):
        path = C.fill(tpl, ids, real)
        for m in METHODS:
            if (m, tpl) == ("POST", "/auth/logout"):
                continue
            for html in (True, False):
                login_limiter.reset(); signup_limiter.reset()
                hs = [("cookie", cookie)] + (HTML if html else JSON) + ([("origin", C.good_origin())] if m in UNSAFE else [])
                r = C.call(m, path, hs)
                cnt[(r.status)] += 1
                if C.leaks(r): leaks.append((m, path))
                key = (m if m != "HEAD" else "GET", tpl)
                if r.status != 403 and (m, tpl) not in ALLOWED and not (m == "HEAD" and ("GET", tpl) in ALLOWED):
                    has_route = key in app_pairs
                    odd.append({"m": m, "path": path, "status": r.status, "has_handler_for_method": has_route,
                                "html": html, "loc": r.location})
# logout with a separate throwaway session
c2 = C.session_cookie(ids["nogroup"])
lo = C.call("POST", "/auth/logout", [("cookie", c2), ("origin", C.good_origin())] + HTML)
after = C.call("GET", "/auth/waiting", [("cookie", c2)] + HTML)
snap1 = C.snapshot(scratch)
d = [x for x in C.diff(snap0, snap1) if x[1] != ".work/audit.jsonl"]
bad = [o for o in odd if o["has_handler_for_method"]]
print(mode, "requests", C.STATE["n"] - n0, "status counts", dict(cnt))
print("non-403 not in allowed set (all):", len(odd), "of which the method HAS a handler:", len(bad))
for o in bad[:20]: print("  ", o)
print("no-handler 404/405 examples:", Counter((o["status"]) for o in odd if not o["has_handler_for_method"]))
print("logout status", lo.status, lo.location, "waiting after logout ->", after.status, after.location)
print("leaks", leaks[:5]); print("data root diff excluding audit:", d)
C.dump("f2", {"requests": C.STATE["n"] - n0, "status_counts": {str(k): v for k, v in cnt.items()},
              "odd_with_handler": bad, "odd_no_handler_sample": [o for o in odd if not o["has_handler_for_method"]][:10],
              "leaks": leaks, "diff_excl_audit": d, "logout": [lo.status, lo.location, after.status]})

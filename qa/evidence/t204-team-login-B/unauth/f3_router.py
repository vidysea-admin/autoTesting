"""Family 3: router table vs policy table. Usage: python f3_router.py <mode> <scratch>"""
import sys, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import common as C
mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from starlette.routing import Match  # noqa: E402
from autotester.auth import policy  # noqa: E402
from autotester.ui.app import app  # noqa: E402
from urllib.parse import unquote

def flat(routes, out):
    for r in routes:
        inner = getattr(r, "original_router", None)
        if inner is not None:
            flat(inner.routes, out); continue
        out.append(r)
    return out
rs = flat(list(app.router.routes), [])
print("route classes:", sorted({type(r).__name__ for r in rs}), "count", len(rs))
app_pairs = set()
for r in rs:
    for m in (getattr(r, "methods", None) or ()):
        if m not in ("HEAD",):
            app_pairs.add((m, r.path))
pol = set(policy.ROUTE_POLICY)
print("routes not in policy:", sorted(app_pairs - pol))
print("policy rows with no route:", sorted(pol - app_pairs))
print("routes without .methods (mounts/static/ws):", [ (type(r).__name__, r.path) for r in rs if not getattr(r,'methods',None)])

def handler(method, path):
    scope = {"type": "http", "method": method, "path": path, "root_path": "", "headers": [], "query_string": b"", "app": app}
    partial = None
    for r in rs:
        m, _ = r.matches(scope)
        if m is Match.FULL:
            return r.path
        if m is Match.PARTIAL and partial is None:
            partial = r.path
    return None

FUZZ = ["alpha", "x", "a b", "a\n", "a\r", "a\x00", ".", "..", "%", "a;b", "a:b", "\u00fc", "A", "a.b", "-", "1", "a\b",
        "a?b", "a#b", "a/b", "a/../b", "../x", "", "a//b", "a%2fb", "a/", "/a", "a\t", "0", "-1", "True"]
mism, n = [], 0
for ms, tpl, cls in C.routes():
    for m in ms:
        if m in ("HEAD",):
            continue
        for fz in FUZZ:
            path = C.fill(tpl, ids, True, fuzz=fz)
            if not path.startswith("/"):
                continue
            h = handler(m, path)
            n += 1
            if h is None:
                continue
            p = policy.route_for(m, path)
            pt = p[0] if p else None
            if pt != h:
                mism.append({"m": m, "path": path, "starlette_handler": h, "policy_template": pt,
                             "policy_rule": str(p[1]) if p else None})
print("fuzz combos", n, "mismatches", len(mism))
seen = set()
for x in mism:
    k = (x["m"], x["starlette_handler"], x["policy_template"])
    if k in seen: continue
    seen.add(k)
    print(x)
C.dump("f3", {"app_not_in_policy": sorted(app_pairs - pol), "policy_no_route": sorted(pol - app_pairs),
              "fuzz_combos": n, "mismatches": mism})

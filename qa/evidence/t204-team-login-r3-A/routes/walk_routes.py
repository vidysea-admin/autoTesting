import os, sys, tempfile, json
root = tempfile.mkdtemp(prefix="at-enum-")
os.environ["AUTOTESTER_ROOT"] = root
os.environ["AUTOTESTER_TEST_NO_AUTO_LOGIN"] = "1"
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
for n in ("AUTOTESTER_AUTH_DIR","AUTOTESTER_AUTH_DISABLED","AUTOTESTER_HOSTED","AUTOTESTER_FIRST_ADMIN_EMAIL","AUTOTESTER_COOKIE_SECURE","AUTOTESTER_ALLOWED_ORIGINS","UVICORN_HOST","AUTOTESTER_PUBLIC_ORIGIN"):
    os.environ.pop(n, None)
import autotester; print("autotester file:", autotester.__file__)
from autotester.ui.app import app
from autotester.auth import policy
from starlette.routing import Mount, Route, WebSocketRoute, Host
out=[]
def walk(routes, prefix=""):
    for r in routes:
        inner = getattr(r, "original_router", None)
        if inner is not None:
            walk(inner.routes, prefix); continue
        if isinstance(r, Mount):
            print("MOUNT", prefix + r.path, type(r.app).__name__)
            out.append((prefix+r.path, "MOUNT", type(r).__name__)); continue
        if isinstance(r, WebSocketRoute):
            print("WEBSOCKET", prefix + r.path); out.append((prefix+r.path,"WS","WebSocketRoute")); continue
        meth = sorted(getattr(r,"methods",None) or [])
        out.append((prefix+r.path, ",".join(meth), type(r).__name__))
walk(app.routes)
print("TOTAL route objects:", len(out))
rows=[]
for path, meths, kind in sorted(out):
    for m in meths.split(","):
        if m in ("HEAD",): continue
        # concrete path for lookup
        concrete = path
        import re
        concrete = re.sub(r"\{([^}:]+):path\}", r"a/b", concrete)
        concrete = re.sub(r"\{[^}]+\}", "x", concrete)
        f = policy.route_for(m, concrete)
        if f is None: pol = "NO ROW (unexposed: default deny)"; key=None; scope=None
        else:
            t, rule, _ = f; pol = f"{rule.kind}:{rule.key.value if rule.key else '-'}"; 
        rows.append((m, path, kind, pol, f[0] if f else None))
for r in rows: print(" | ".join(str(x) for x in r))
print("policy rows:", len(policy.ROUTE_POLICY))
served = {(m, p) for m,p,_,_,_ in rows}
used = {(m, t) for m,_,_,_,t in rows if t}
pol = set(policy.ROUTE_POLICY)
print("POLICY ROWS WITH NO SERVED ROUTE:", sorted(pol - {(m,p) for m,p,_,_,t in rows if t}))

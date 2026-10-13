import os, sys, tempfile, re, json
root = tempfile.mkdtemp(prefix="ckb-root-")
os.environ["AUTOTESTER_ROOT"] = root
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
for k in ("AUTOTESTER_AUTH_DIR","AUTOTESTER_AUTH_DISABLED","AUTOTESTER_HOSTED","AUTOTESTER_FIRST_ADMIN_EMAIL","UVICORN_HOST","AUTOTESTER_PUBLIC_ORIGIN","AUTOTESTER_COOKIE_SECURE"):
    os.environ.pop(k, None)
from fastapi.testclient import TestClient
from autotester.ui.app import app
from autotester.auth import accounts, policy
from fastapi.routing import APIRoute
from starlette.routing import Route, Mount

routes = []
pending = list(app.routes)
while pending:
    r = pending.pop()
    inner = getattr(r, "original_router", None)
    if inner is not None:
        pending.extend(inner.routes); continue
    if isinstance(r, Mount):
        print("MOUNT", r.path); routes.append(("MOUNT", r.path)); continue
    for m in sorted(getattr(r, "methods", None) or ()):
        if m not in ("HEAD","OPTIONS"): routes.append((m, r.path))
routes = sorted(set(routes))
print("served pairs:", len(routes))
def fill(p):
    return re.sub(r"\{[^}]+\}", "x1", p)

# state: admin + zero-access user
admin = accounts.signup("admin@team.test", "correct-horse-battery")
zero = accounts.signup("zero@team.test", "correct-horse-battery")
def login(email):
    c = TestClient(app, follow_redirects=False)
    r = c.post("/auth/login", data={"email": email, "password": "correct-horse-battery"})
    assert r.status_code == 303, r.status_code
    return c
anon = TestClient(app, follow_redirects=False)
zc = login("zero@team.test")
public = set(); session=set(); bad=[]
unrouted=[]
for m, p in routes:
    if m == "MOUNT":
        print("MOUNT needs manual", p); continue
    hit = policy.route_for(m, p)
    if hit is None:
        unrouted.append((m,p)); 
    else:
        kind = hit[1].kind
        if kind=="public": public.add((m,p))
        if kind=="session": session.add((m,p))
    url = fill(p)
    kw = dict(data={}) if m in ("POST","PUT","PATCH","DELETE") else {}
    ra = anon.request(m, url, **kw)
    rz = zc.request(m, url, **kw)
    kind = hit[1].kind if hit else "NONE"
    # anon must be refused unless public
    if kind != "public" and ra.status_code not in (401,303,307,302):
        bad.append(("ANON-OPEN", m, p, kind, ra.status_code))
    if kind != "public" and ra.status_code in (303,307,302) and "/auth/login" not in ra.headers.get("location",""):
        bad.append(("ANON-REDIR-ODD", m, p, ra.headers.get("location")))
    # zero-access must be 403 (or redirect to waiting) unless public/session/member?
    if kind not in ("public","session"):
        if rz.status_code not in (403,303,401):
            bad.append(("ZERO-OPEN", m, p, kind, rz.status_code))
print("kinds:", sorted({policy.route_for(m,p)[1].kind for m,p in routes if m!='MOUNT' and policy.route_for(m,p)}))
print("public:", sorted(public)); print("session:", sorted(session))
print("UNROUTED:", unrouted)
from collections import Counter
print("ZERO status", Counter()) 
print("BAD:", json.dumps(bad, indent=1))
# unmatched path + weird methods
for m,u in [("GET","/nope"),("GET","/static/../.env"),("GET","/docs"),("GET","/openapi.json"),("GET","/redoc"),("TRACE","/healthz"),("GET","/healthz/"),("GET","//auth/login"),("GET","/projects"),("GET","/projects/")]:
    r = anon.request(m,u); print(m,u,r.status_code,r.headers.get("location",""))

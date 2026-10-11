"""Seat B own reproduction: (a) slug-prefixed server env key by a Developer; (b) users.manage resets a settings.manage account."""
import os, sys, tempfile, pathlib
root = pathlib.Path(tempfile.mkdtemp(prefix="t204b-own-", dir=os.environ["B_SCRATCH"]))
os.environ.update(AUTOTESTER_ROOT=str(root), AUTOTESTER_ALLOWED_HOSTS="testserver", AUTOTESTER_TEST_NO_AUTO_LOGIN="1")
for k in ("AUTOTESTER_HOSTED","AUTOTESTER_AUTH_DISABLED","AUTOTESTER_FIRST_ADMIN_EMAIL","UVICORN_HOST","ANTHROPIC_BASE_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, "D:/autoTesting/.worktrees/t204-team-login/tests")
from fastapi.testclient import TestClient
from autotester.auth import accounts, groups
from autotester.ui.app import app
import auth_harness as H
H.login_limiter.reset(); H.signup_limiter.reset()
H.account("admin@t.test")
H.account("dev@t.test", "developer")
dev = H.login("dev@t.test")
ORIGIN = {}
# (a)
for slug, key in (("anthropic", "ANTHROPIC_BASE_URL"), ("http", "HTTP_PROXY"), ("node", "NODE_OPTIONS"), ("ld", "LD_PRELOAD")):
    r = dev.post("/onboard", headers=ORIGIN, data={"slug": slug, "name": slug.title(), "base_url": f"https://{slug}.example.com",
        "allowed_domains": f"{slug}.example.com", "credential_key": key, "credential_value": "canary-value-1",
        "credential_domains": f"{slug}.example.com", "credential_description": ""})
    env = (root / ".env")
    print("(a)", slug, key, "->", r.status_code, "in .env:", env.exists() and (key + "=") in env.read_text())
# control: a key outside the namespace
r = dev.post("/onboard", headers=ORIGIN, data={"slug": "ctl", "name": "Ctl", "base_url": "https://ctl.example.com", "allowed_domains": "ctl.example.com",
    "credential_key": "ANTHROPIC_API_KEY", "credential_value": "x1", "credential_domains": "ctl.example.com", "credential_description": ""})
print("(a) control provider key ->", r.status_code)
# (b)
ops = groups.create_group("Ops", ["users.manage"]); setg = groups.create_group("SetMgr", ["settings.manage"])
H.account("ops@t.test"); accounts.set_user_groups(H.user_id("ops@t.test"), [ops.id])
H.account("sm@t.test");  accounts.set_user_groups(H.user_id("sm@t.test"), [setg.id])
opsc = H.login("ops@t.test")
print("(b) ops GET /settings/providers ->", opsc.get("/settings/providers").status_code)
r = opsc.post(f"/admin/users/{H.user_id('sm@t.test')}/password", headers=ORIGIN, data={"password": "NewPassw0rd-canary-b"})
print("(b) ops resets settings.manage account password ->", r.status_code)
c = TestClient(app, follow_redirects=False)
l = c.post("/auth/login", headers=ORIGIN, data={"email": "sm@t.test", "password": "NewPassw0rd-canary-b"})
print("(b) login as that account ->", l.status_code, "; GET /settings/providers ->", c.get("/settings/providers").status_code)

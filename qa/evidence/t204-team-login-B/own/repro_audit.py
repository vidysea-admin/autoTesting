"""Seat B own reproduction (c): AU27 refused attempts and the audit file."""
import os, sys, tempfile, pathlib, json
root = pathlib.Path(tempfile.mkdtemp(prefix="t204b-aud-", dir=os.environ["B_SCRATCH"]))
os.environ.update(AUTOTESTER_ROOT=str(root), AUTOTESTER_ALLOWED_HOSTS="testserver", AUTOTESTER_TEST_NO_AUTO_LOGIN="1")
for k in ("AUTOTESTER_HOSTED","AUTOTESTER_AUTH_DISABLED","AUTOTESTER_FIRST_ADMIN_EMAIL","UVICORN_HOST"): os.environ.pop(k, None)
sys.path.insert(0, "D:/autoTesting/.worktrees/t204-team-login/tests")
from autotester.auth import accounts, groups
import auth_harness as H
H.login_limiter.reset(); H.signup_limiter.reset()
H.account("admin@t.test")
ops = groups.create_group("Ops", ["users.manage", "groups.manage"])
H.account("ops@t.test"); accounts.set_user_groups(H.user_id("ops@t.test"), [ops.id])
c = H.login("ops@t.test")
aid = H.user_id("admin@t.test")
audit = root / ".work" / "audit.jsonl"
before = len(audit.read_text().splitlines()) if audit.exists() else 0
r1 = c.post(f"/admin/users/{aid}/password", data={"password": "Another-canary-pw-1"})
r2 = c.post(f"/admin/groups/{ops.id}", data={"name": "Ops", "permission": ["users.manage","groups.manage","settings.manage"]})
print("reset admin ->", r1.status_code, "| tick settings.manage ->", r2.status_code)
lines = audit.read_text().splitlines()[before:]
for l in lines:
    d = json.loads(l); d.pop("ts", None); print(d)
print("lines with actor/target/action keys:", sum(1 for l in lines if "action" in json.loads(l)))

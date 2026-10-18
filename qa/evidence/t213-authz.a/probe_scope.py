"""Checker-A counterexamples (run outside the worktree; imports the worktree's package + test fakes)."""
import sys, tempfile
from pathlib import Path
import pytest
sys.path.insert(0, "D:/autoTesting/.worktrees/t213-authz/tests")
sys.path.insert(0, "D:/autoTesting/.worktrees/t213-authz")
from authz_fakes import Scaffold, BASE, NOW, rows
from autotester.schema.authz_probe import AuthzPlan, PrivilegeProbe, TenantProbe, ProbeReply
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.stages import oracle_privilege, oracle_tenant

mp = pytest.MonkeyPatch()
root = Path(tempfile.mkdtemp(dir="D:/autoTesting/.work/tmp"))
sc = Scaffold(root, mp)
# project with TWO platforms; approval is only for the PRIMARY base URL
proj = Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.test", "other.test"],
               platforms=[Platform(id="primary", name="P", base_url=BASE, allowed_domains=["app.test"], include_subdomains=False),
                          Platform(id="second", name="S", base_url="https://other.test/", allowed_domains=["other.test"])])
sc.store.save_project(proj)
sc.grant(10)
plan = AuthzPlan(platform_id="primary", privilege_probes=[PrivilegeProbe(id="p1", higher_role_id="admin", lower_role_id="student", read_urls=["https://other.test/admin/users"])])
sc.plan(plan)
sc.app.serve("student", "/admin/users", 200)
_orig = sc.app.read
urls = []
def spy(role, url):
    urls.append(url); return _orig(role, url)
sc.app.read = spy
try:
    out = oracle_privilege.run_privilege_pass(sc.context(), clock=lambda: 0.0, sleep=lambda s: None, now=NOW)
    print("GATE PASSED; transport saw URLs:", urls, "findings:", len(out))
except Exception as e:
    print("REFUSED:", type(e).__name__, str(e)[:120])

# --- silent false negative: owner list 401 (session expired) -> clean, nothing named unprobed
root2 = Path(tempfile.mkdtemp(dir="D:/autoTesting/.work/tmp"))
sc2 = Scaffold(root2, mp)
sc2.grant(10)
sc2.plan(AuthzPlan(platform_id="primary", tenant_probes=[TenantProbe(id="t1", viewer_role_id="tenant-a", owner_role_id="tenant-b", list_url="/students")]))
sc2.app.serve("tenant-a", "/students", 200, rows("b", 3))   # A sees B's 3 rows
sc2.app.serve("tenant-b", "/students", 401, [])             # B's list read fails (expired session)
out = oracle_tenant.run_tenant_pass(sc2.context(), clock=lambda: 0.0, sleep=lambda s: None, now=NOW)
import json
log = json.loads((root2/"run"/"authz"/"tenant_log.json").read_text())
print("OWNER-401: findings =", len(out), "| unprobed named =", log["unprobed"], "| sent =", log["sent"])
# control: owner list 200 -> 3 rows found
sc2.app.serve("tenant-b", "/students", 200, rows("b", 3))
out = oracle_tenant.run_tenant_pass(sc2.context(), clock=lambda: 0.0, sleep=lambda s: None, now=NOW)
print("CONTROL owner-200: findings =", len(out), "count =", out[0].count if out else None)
tree = "\n".join(p.read_bytes().decode("utf-8","replace") for p in root2.rglob("*") if p.is_file())
print("MPI1 scan of control run tree: markers present =", [m for m in ("ZZNAME","zz.leak","ZZPHONE","sid-b-") if m in tree], "| files =", len([p for p in root2.rglob('*') if p.is_file()]))

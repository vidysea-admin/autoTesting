"""Checker-A cycle-1 counterexamples for the repaired scope gate (read-only toward the worktree)."""
import sys, tempfile
from pathlib import Path
import pytest
sys.path.insert(0, "D:/autoTesting/.worktrees/t213-authz/tests")
sys.path.insert(0, "D:/autoTesting/.worktrees/t213-authz")
from authz_fakes import Scaffold, BASE, NOW
from autotester.schema.authz_probe import AuthzPlan, PrivilegeProbe
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.stages import oracle_privilege
from autotester.stages.authz_probe import _in_scope, abs_url

mp = pytest.MonkeyPatch()

def attempt(label, url, primary_kw=None, second_base="https://other.test/", proj_domains=("app.test", "other.test")):
    root = Path(tempfile.mkdtemp(dir="D:/autoTesting/.work/tmp"))
    sc = Scaffold(root, mp)
    sc.store.save_project(Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=list(proj_domains),
        platforms=[Platform(id="primary", name="P", base_url=BASE, allowed_domains=["app.test"], **(primary_kw or {})),
                   Platform(id="second", name="S", base_url=second_base, allowed_domains=[__import__("urllib.parse").parse.urlsplit(second_base).hostname])]))
    sc.grant(10)
    try:
        sc.plan(AuthzPlan(platform_id="primary", privilege_probes=[PrivilegeProbe(id="p1", higher_role_id="admin", lower_role_id="student", read_urls=[url])]))
    except Exception as e:
        print(f"{label}: SCHEMA-REJECTED before the gate ({type(e).__name__})"); return
    sc.app.serve("student", "/admin/users", 200)
    seen = []
    orig = sc.app.read
    sc.app.read = lambda r, u: (seen.append(u), orig(r, u))[1]
    try:
        out = oracle_privilege.run_privilege_pass(sc.context(), clock=lambda: 0.0, sleep=lambda s: None, now=NOW)
        print(f"{label}: GATE PASSED, transport saw {seen}")
    except Exception as e:
        print(f"{label}: REFUSED {type(e).__name__} transport_urls={seen}")

attempt("sibling-platform host (cycle-0 escape)", "https://other.test/admin/users")
attempt("sibling, include_subdomains=False", "https://other.test/admin/users", {"include_subdomains": False})
attempt("protocol-relative //other.test", "//other.test/admin/users")
attempt("userinfo app.test@other.test", "https://app.test@other.test/admin/users")
attempt("suffix lookalike evilapp.test", "https://evilapp.test/admin/users", proj_domains=("app.test", "evilapp.test"))
attempt("own path (control, must pass)", "/admin/users")
attempt("own subdomain default include_subdomains (control)", "https://api.app.test/admin/users")
attempt("trailing-dot host app.test.", "https://app.test./admin/users")
attempt("uppercase host APP.TEST", "https://APP.TEST/admin/users")
p = Platform(id="primary", name="P", base_url=BASE, allowed_domains=["app.test"])
for u in ("https://other.test\@app.test/x", "https://app.test\@other.test/x", "https://other.test#@app.test/x"):
    print("parser-diff", repr(u), "->in_scope", _in_scope(p, abs_url(p, u)))

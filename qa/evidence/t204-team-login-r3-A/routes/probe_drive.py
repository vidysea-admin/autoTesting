import os, sys, tempfile, re
root = tempfile.mkdtemp(prefix="at-drive-")
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
from starlette.routing import Match
from autotester.ui.app import app
from autotester.auth import accounts, groups, policy
from autotester.auth.access import set_owner, set_relation
from autotester.auth.ratelimit import login_limiter
from autotester.schema.auth import ProjectRelation
from autotester.schema.intake import DriveJob, IntakeReport
from autotester.schema.project import Project
from autotester.sources.drive_jobs import save_job
from autotester.store.project_store import ProjectStore

PW = "correct-horse-battery"
tc = lambda: TestClient(app, follow_redirects=False, raise_server_exceptions=False)


def mkproject(slug):
    ProjectStore(slug, Path(root)).save_project(Project(slug=slug, name=slug.title(), base_url=f"https://{slug}.test", allowed_domains=[f"{slug}.test"]))


def gid(seed):
    return next(g.id for g in groups.list_groups() if g.seed == seed)


def login(e):
    login_limiter.reset()
    c = tc()
    r = c.post("/auth/login", data={"email": e, "password": PW})
    assert r.status_code == 303
    return c


for e in ("admin@team.test", "dev@team.test", "dev2@team.test", "tester@team.test", "sub@team.test"):
    tc().post("/auth/signup", data={"email": e, "password": PW})
mkproject("alpha"); mkproject("beta")
dev = accounts.find_user("dev@team.test"); dev2 = accounts.find_user("dev2@team.test")
t = accounts.find_user("tester@team.test"); sub = accounts.find_user("sub@team.test")
accounts.set_user_groups(dev.id, [gid("developer")]); accounts.set_user_groups(dev2.id, [gid("developer")])
accounts.set_user_groups(t.id, [gid("tester")]); accounts.set_user_groups(sub.id, [gid("sub-admin")])
set_owner("alpha", dev.id); set_owner("beta", dev2.id)
set_relation("alpha", t.id, ProjectRelation.SHARED, True)
from autotester.auth.access import set_relation as sr
sr("alpha", sub.id, ProjectRelation.ASSIGNED, True)

# jobs
JA = "01HAAAAAAAAAAAAAAAAAAAAAAA"; JB = "01HBBBBBBBBBBBBBBBBBBBBBBB"
save_job(Path(root), DriveJob(id=JA, project="alpha", drive_id="SECRETDRIVEID_ALPHA", state="failed", message="The fetch stopped unexpectedly."))
save_job(Path(root), DriveJob(id=JB, project="beta", drive_id="SECRETDRIVEID_BETA", state="refused", message="not allowed"))
P = {n: login(f"{n}@team.test") for n in ("admin", "dev", "dev2", "tester", "sub")}
anon = tc()
H = {"accept": "text/html"}
print("\nDRIVE JOB PAGE (GET /projects/<slug>/sources/drive/<id>)")
cases = [("alpha", JA), ("alpha", JB), ("beta", JB), ("beta", JA), ("ghost", JA)]
for slug, jid in cases:
    row = {}
    for n, c in {"anon": anon, **P}.items():
        r = c.get(f"/projects/{slug}/sources/drive/{jid}", headers=H)
        row[n] = r.status_code
    print(f"   /projects/{slug}/sources/drive/{jid[:6]}..  {row}")
r = P["tester"].get(f"/projects/alpha/sources/drive/{JA}", headers=H)
body = r.text
print("   tester-shared body leaks drive_id?", "SECRETDRIVEID" in body, "| mentions 'token'/'http'?", bool(re.search(r"token|https?://drive", body, re.I)), "| len", len(body))
print("   body text fragment:", re.sub(r"<[^>]+>", " ", body)[-260:].split())
print("   NOTE: handler = routes_intake.drive_job_page(slug, job_id); load_job(root, slug, job_id) -> .work/drive-jobs/<slug>/<id>.json")

print("\nSAME-SLUG COOKIE/STATE: dev(owner alpha) -> beta's job via beta slug:", P["dev"].get(f"/projects/beta/sources/drive/{JB}", headers=H).status_code)

print("\nDAMAGE REPORT scope (GET /projects/<slug>/damage-report)")
for slug in ("alpha", "beta", "ghost"):
    print("  ", slug, {n: c.get(f"/projects/{slug}/damage-report", headers=H).status_code for n, c in {"anon": anon, **P}.items()})
print("   with ?run=../x :", P["dev"].get("/projects/alpha/damage-report?run=../../x", headers=H).status_code, P["dev"].get("/projects/alpha/damage-report?run=nope", headers=H).status_code)

print("\nUPLOAD POST scope (empty body; 400/422 = reached handler, 403/404 = gate)")
for slug in ("alpha", "beta"):
    print("  upload", slug, {n: c.post(f"/projects/{slug}/sources/upload", data={}).status_code for n, c in {"anon": anon, **P}.items()})
    print("  drive ", slug, {n: c.post(f"/projects/{slug}/sources/drive", data={"link": "not a link"}).status_code for n, c in {"anon": anon, **P}.items()})

print("\nAUTOMATIC DISAMBIGUATION: for each served route, concrete path -> every app route with a FULL match vs policy template")
def routes_flat():
    out = []
    pending = list(app.routes)
    while pending:
        r = pending.pop(0)
        inner = getattr(r, "original_router", None)
        if inner is not None:
            pending.extend(inner.routes); continue
        out.append(r)
    return out
RT = routes_flat()
def conc(p):
    p = re.sub(r"\{[^}:]+:path\}", "a/b.mp4", p)
    return re.sub(r"\{[^}]+\}", "x1", p)
issues = 0
checked = 0
# also try adversarial values: segments named like sibling literals
LIT = ["drive", "upload", "new", "report", "damage-report", "access", "env", "cases", "sources", "pin", "analyze", "approve", "merge", "generate", "delete", "rename", "add", "url", "secrets", "run", "explore"]
paths = set()
for r in RT:
    for m in (getattr(r, "methods", None) or ()):
        if m == "HEAD": continue
        base = r.path
        paths.add((m, conc(base)))
        # substitute each placeholder with each sibling literal
        for ph in re.findall(r"\{[^}]+\}", base):
            if ph.startswith("{slug"): continue
            for lit in LIT:
                p = base.replace(ph, lit)
                paths.add((m, conc(p)))
for m, p in sorted(paths):
    scope = {"type": "http", "method": m, "path": p, "root_path": "", "query_string": b"", "headers": [], "app": app}
    full = [r.path for r in RT if r.matches(scope)[0] is Match.FULL and m in (getattr(r, "methods", None) or ())]
    found = policy.route_for(m, p)
    checked += 1
    first = full[0] if full else None
    if first is None and found is None: continue
    if first is None and found is not None:
        # policy has a row but no handler -> harmless (404/405 after gate); report
        print("   policy-row-without-handler:", m, p, found[0]); continue
    if found is None or found[0] != first:
        issues += 1
        print("   MISMATCH", m, p, "router->", first, "| policy->", None if found is None else found[0], "| all FULL:", full)
print(f"   checked {checked} (method,path) pairs; mismatches: {issues}")

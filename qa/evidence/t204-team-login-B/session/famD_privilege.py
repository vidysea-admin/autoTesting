from common import *
root = setup("famD")
import re
from fastapi.testclient import TestClient
from autotester.ui.app import app
from autotester.auth.ratelimit import login_limiter, signup_limiter
from autotester.auth import accounts, groups, access
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

ADMIN = "admin@team.test"
BASE = "http://testserver"


def C():
    return TestClient(app, follow_redirects=False, raise_server_exceptions=False)


def gid(seed):
    return next(g.id for g in groups.list_groups() if g.seed == seed)


def mk(email, seed=None):
    u = accounts.signup(email, PW)
    if seed:
        accounts.set_user_groups(u.id, [gid(seed)])
    return u.id


def login(email):
    login_limiter.reset()
    r = C().post("/auth/login", data={"email": email, "password": PW})
    assert r.status_code == 303, (email, r.status_code)
    return r.headers["set-cookie"].split(";")[0]


def req(ck, method, path, **kw):
    h = kw.pop("headers", {})
    h["Cookie"] = ck
    h.setdefault("Accept", "text/html")
    return C().request(method, path, headers=h, **kw)


# --- build the cast -------------------------------------------------------------------
admin_id = mk(ADMIN)  # first signup -> Admin/CEO (local mode)
ceo2_id = mk("ceo2@team.test", "admin")
sub_id = mk("sub@team.test", "sub-admin")
dev_id = mk("dev@team.test", "developer")
tester_id = mk("tester@team.test", "tester")
none_id = mk("none@team.test")
cust_id = mk("custom@team.test")
ops_id = mk("ops@team.test")
victim_id = mk("victim@team.test")
p("seeds:", [(g.seed, g.id) for g in groups.list_groups()])
cg = groups.create_group("CustomMgr", ["users.manage", "groups.manage"])
og = groups.create_group("Ops", ["settings.manage"])
groups.update_group(cg.id, "CustomMgr", ["users.manage", "groups.manage"], [cust_id])
groups.update_group(og.id, "Ops", ["settings.manage"], [ops_id])
GIDS = {g.seed: g.id for g in groups.list_groups()}
gid = lambda seed: GIDS[seed]  # noqa: E731  (default groups can be deleted later in the run)
ADM_G = gid("admin")
p("custom perms:", groups.get_group(cg.id).permissions, "| Admin/CEO members:", groups.get_group(ADM_G).member_ids, "admin ids:", admin_id, ceo2_id)
cookies = {n: login(f"{n}@team.test") for n in ("sub", "dev", "tester", "none", "custom", "ceo2")}
cookies["admin"] = login(ADMIN)
ID = {"admin": admin_id, "ceo2": ceo2_id, "sub": sub_id, "dev": dev_id, "tester": tester_id, "none": none_id,
      "custom": cust_id, "ops": ops_id, "victim": victim_id}

store = ProjectStore("p-dev", __import__("pathlib").Path(root))
for slug in ("p-dev", "p-admin"):
    ProjectStore(slug, __import__("pathlib").Path(root)).save_project(Project(
        slug=slug, name=slug.title(), base_url=f"https://{slug}.test", allowed_domains=[f"{slug}.test"]))
access.set_owner("p-dev", dev_id)
access.set_owner("p-admin", admin_id)


def probe(actor, label, method, path, **kw):
    """Run one request; report status, whether store snapshot changed, new audit lines."""
    before, a0 = snapshot(root), len(audit_lines(root))
    r = req(cookies[actor], method, path, **kw)
    after, a1 = snapshot(root), len(audit_lines(root))
    changed = [t for t in before if before[t] != after[t]]
    new = [json.loads(x) for x in audit_lines(root)[a0:a1]]
    new = [{k: v for k, v in d.items() if k != "ts"} for d in new]
    msg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    m = re.search(r"(refused[^.]*\.?|you do not have permission[^.]*|this page is not available[^.]*)", msg)
    p(f"  [{actor:6s}] {label:46s} -> {r.status_code}  stored-changed={changed or 'no'}  note={(m.group(1)[:70] if m else '')!r}  audit={new}")
    return r, changed


p("== D1 every admin route as every non-admin")
EXPECT = {"sub", "dev", "tester", "none"}
for actor in ("sub", "dev", "tester", "none", "custom"):
    p(f"-- actor {actor}")
    probe(actor, "GET /admin/users", "GET", "/admin/users")
    probe(actor, "GET /admin/groups", "GET", "/admin/groups")
    probe(actor, "disable admin", "POST", f"/admin/users/{admin_id}/disable")
    probe(actor, "delete admin", "POST", f"/admin/users/{admin_id}/delete")
    probe(actor, "reset admin password", "POST", f"/admin/users/{admin_id}/password", data={"password": PW2})
    probe(actor, "rename admin", "POST", f"/admin/users/{admin_id}/name", data={"display_name": "pwned"})
    probe(actor, "self -> Admin/CEO (groups action)", "POST", f"/admin/users/{ID[actor]}/groups", data={"group_id": str(ADM_G)})
    probe(actor, "none-user -> Admin/CEO", "POST", f"/admin/users/{none_id}/groups", data={"group_id": str(ADM_G)})
    probe(actor, "self -> Developer group (perms not held)", "POST", f"/admin/users/{ID[actor]}/groups", data={"group_id": str(gid("developer"))})
    probe(actor, "self -> Ops group (settings.manage)", "POST", f"/admin/users/{ID[actor]}/groups", data={"group_id": str(og.id)})
    probe(actor, "create group with project.run@all", "POST", "/admin/groups", data={"name": f"G-{actor}", "permission": "project.run@all"})
    probe(actor, "create group with users.manage", "POST", "/admin/groups", data={"name": f"G2-{actor}", "permission": "users.manage"})
    probe(actor, "tick settings.manage on CustomMgr", "POST", f"/admin/groups/{cg.id}",
          data={"name": "CustomMgr", "permission": ["users.manage", "groups.manage", "settings.manage"]})
    probe(actor, "tick credentials.view on Developer", "POST", f"/admin/groups/{gid('developer')}",
          data={"name": "Developer", "permission": ["credentials.view"]})
    probe(actor, "edit Sub-admin: add settings.manage", "POST", f"/admin/groups/{gid('sub-admin')}",
          data={"name": "Sub-admin", "permission": ["settings.manage", "project.view@assigned"]})
    probe(actor, "rename Admin/CEO", "POST", f"/admin/groups/{ADM_G}", data={"name": "Admin/CEO2", "permission": ["users.manage"]})
    probe(actor, "Admin/CEO: add self as member", "POST", f"/admin/groups/{ADM_G}",
          data={"name": "Admin/CEO", "permission": [p_ for p_ in groups.get_group(ADM_G).permissions], "members_shown": "1", "member_id": [str(admin_id), str(ceo2_id), str(ID[actor])]})
    probe(actor, "delete Admin/CEO group", "POST", f"/admin/groups/{ADM_G}/delete", data={"confirm": "yes"})
    probe(actor, "POST /settings/providers", "POST", "/settings/providers", data={"ANTHROPIC_API_KEY": "x"})
    probe(actor, "GET /settings/providers", "GET", "/settings/providers")
    probe(actor, "p-dev: assign SELF", "POST", "/projects/p-dev/access", data={"email": f"{actor}@team.test", "relation": "assigned", "change": "add"})
    probe(actor, "p-admin: share to SELF", "POST", "/projects/p-admin/access", data={"email": f"{actor}@team.test", "relation": "shared", "change": "add"})
    probe(actor, "GET p-admin/access vs missing", "GET", "/projects/p-admin/access")

p("== D2 custom (users.manage+groups.manage, NOT Admin) - what IS allowed")
r, ch = probe("custom", "reset NON-admin 'victim' pw", "POST", f"/admin/users/{victim_id}/password", data={"password": PW2})
r, ch = probe("custom", "reset 'sub' (Sub-admin) pw", "POST", f"/admin/users/{sub_id}/password", data={"password": PW2})
r, ch = probe("custom", "reset 'ops' (settings.manage) pw", "POST", f"/admin/users/{ops_id}/password", data={"password": PW2})
login_limiter.reset()
rr = C().post("/auth/login", data={"email": "ops@team.test", "password": PW2})
p("   custom now logs in as ops with the password it set:", rr.status_code)
if rr.status_code == 303:
    ck_ops = rr.headers["set-cookie"].split(";")[0]
    cookies["ops_taken"] = ck_ops
    g = req(ck_ops, "GET", "/settings/providers")
    p("   -> /settings/providers as taken-over ops (custom itself gets 403 there):", g.status_code, " custom itself:", req(cookies['custom'], 'GET', '/settings/providers').status_code)
login_limiter.reset()
rr = C().post("/auth/login", data={"email": "sub@team.test", "password": PW2})
p("   custom logs in as 'sub' (Sub-admin) w/ reset pw:", rr.status_code)
probe("custom", "disable non-admin victim", "POST", f"/admin/users/{victim_id}/disable")
probe("custom", "enable non-admin victim", "POST", f"/admin/users/{victim_id}/enable")
probe("custom", "create empty group", "POST", "/admin/groups", data={"name": "EmptyG"})
eg = next(g for g in groups.list_groups() if g.name == "EmptyG")
probe("custom", "add self to EmptyG via group edit", "POST", f"/admin/groups/{eg.id}", data={"name": "EmptyG", "members_shown": "1", "member_id": str(cust_id)})
for variant in ["users.manage", " users.manage", "USERS.MANAGE", "users.manage@", "users.manage\x00", "users.manage@all", "settings.manage", "credentials.view",
                "project.view@all", "project.view@ALL", "project.view@all\n", "project.view@all@all", "live.view"]:
    probe("custom", f"EmptyG tick {variant!r}", "POST", f"/admin/groups/{eg.id}", data={"name": "EmptyG", "permission": variant})

p("== D3 mass assignment / extra fields / dup params")
login_limiter.reset(); signup_limiter.reset()
before = snapshot(root)
r = C().post("/auth/signup", data={"email": "mass@x.test", "password": PW, "role": "admin", "is_admin": "1", "group_id": str(ADM_G),
                                    "groups": "Admin/CEO", "permissions": "users.manage", "user_id": "1", "disabled": "0", "email2": ADMIN, "seed": "admin"})
u = accounts.find_user("mass@x.test")
p(" signup w/ extra fields:", r.status_code, "-> groups:", u.groups, "location:", r.headers.get("location"))
login_limiter.reset()
r = C().post("/auth/login", data={"email": "mass@x.test", "password": PW, "role": "admin", "group_id": str(ADM_G), "user_id": "1"})
ck_mass = r.headers["set-cookie"].split(";")[0]
cookies["mass"] = ck_mass
p(" login w/ extra fields:", r.status_code, "groups:", accounts.find_user("mass@x.test").groups)
for path in ("/admin/users", "/onboard", "/settings/providers"):
    p("   mass user", path, req(ck_mass, "GET", path).status_code)
probe("custom", "name edit w/ extras (email, password, group_id, disabled)", "POST", f"/admin/users/{victim_id}/name",
      data={"display_name": "Vic", "email": "evil@x.test", "password": "zzzzzzzzzzzz", "group_id": str(ADM_G), "disabled": "1"})
v = accounts.get_user(victim_id)
p("   victim after: email", v.email, "display", v.display_name, "groups", v.groups, "disabled", v.disabled)
probe("custom", "group edit w/ seed/id extras, no members_shown", "POST", f"/admin/groups/{eg.id}",
      data={"name": "EmptyG", "seed": "admin", "id": str(ADM_G), "member_id": str(cust_id)})
p("   EmptyG members after (member_id w/o members_shown ignored => unchanged):", groups.get_group(eg.id).member_ids, "seed:", groups.get_group(eg.id).seed)
probe("custom", "member_id w/ members_shown=0", "POST", f"/admin/groups/{eg.id}", data={"name": "EmptyG", "members_shown": "0", "member_id": str(none_id)})
probe("custom", "dup group_id=Tester&group_id=Admin (mixed)", "POST", f"/admin/users/{none_id}/groups", content=f"group_id={gid('tester')}&group_id={ADM_G}", headers={"Content-Type": "application/x-www-form-urlencoded"})
probe("custom", "JSON body to groups action (empty form)", "POST", f"/admin/users/{victim_id}/groups", json={"group_id": [ADM_G]})
probe("dev", "dev edits own record (name) via admin route", "POST", f"/admin/users/{dev_id}/name", data={"display_name": "x"})

p("== D4 IDOR / odd ids as Admin")
for uid in ("0", "-1", "99999999999999999999", "1.5", "abc", "%20", "1e3", "٣", "+3"):
    r = req(cookies["admin"], "POST", f"/admin/users/{uid}/name", data={"display_name": "n"})
    p(f"  users/{uid!r}/name -> {r.status_code}")
for gidv in ("0", "-1", "99999999999999999999", "abc", "1.0"):
    r = req(cookies["admin"], "GET", f"/admin/groups/{gidv}")
    p(f"  GET groups/{gidv!r} -> {r.status_code}")
r = req(cookies["admin"], "POST", f"/admin/users/{victim_id}/groups", data={"group_id": ["99999999999999999999"]})
p("  groups action w/ huge group id ->", r.status_code)
r = req(cookies["admin"], "POST", f"/admin/users/{victim_id}/groups", data={"group_id": ["abc"]})
p("  groups action w/ non-int group id ->", r.status_code)
r = req(cookies["admin"], "POST", f"/admin/groups/{eg.id}", data={"name": "EmptyG", "members_shown": "1", "member_id": ["99999999999999999999"]})
p("  group edit w/ huge member id ->", r.status_code)
r = req(cookies["admin"], "POST", f"/admin/users/{victim_id}/bogus")
p("  unknown action ->", r.status_code)
bodies = {}
for slug in ("p-admin", "nope", "..%2f..%2fetc", "p-admin%00"):
    r = req(cookies["dev"], "GET", f"/projects/{slug}")
    bodies[slug] = (r.status_code, re.sub(slug.split('%')[0], "SLUG", r.text)[:0] + str(len(r.text)))
    r2 = req(cookies["dev"], "POST", f"/projects/{slug}/access", data={"email": "x@x.test", "relation": "shared"})
    p(f"  dev GET /projects/{slug} -> {r.status_code} len {len(r.text)} | POST access -> {r2.status_code}")
p("  dev own project p-dev:")
for rel in ("assigned", "shared"):
    r = req(cookies["dev"], "POST", "/projects/p-dev/access", data={"email": "tester@team.test", "relation": rel, "change": "add"})
    p(f"   dev POST access relation={rel} ->", r.status_code)
r = req(cookies["dev"], "POST", "/projects/p-dev/access", data={"email": "nobody@team.test", "relation": "shared", "change": "add"})
r2 = req(cookies["dev"], "POST", "/projects/p-dev/access", data={"email": "admin@team.test", "relation": "shared", "change": "add"})
p("   dev share to unknown vs existing email (enumeration):", r.status_code, r2.status_code)
r = req(cookies["tester"], "POST", "/projects/p-dev/access", data={"email": "tester@team.test", "relation": "shared"})
p("   tester (shared on p-dev) tries POST access:", r.status_code)
r = req(cookies["sub"], "GET", "/projects/p-dev/access")
p("   sub (not assigned) GET p-dev/access:", r.status_code)
r = req(cookies["admin"], "POST", "/projects/p-dev/access", data={"email": "sub@team.test", "relation": "assigned", "change": "add"})
p("   Admin assigns sub to p-dev:", r.status_code)
r = req(cookies["sub"], "POST", "/projects/p-dev/access", data={"email": "none@team.test", "relation": "assigned"})
p("   sub (assigned, no project.assign) assigns other:", r.status_code)
r = req(cookies["sub"], "POST", "/projects/p-dev/access", data={"email": "none@team.test", "relation": "shared"})
p("   sub (assigned) shares to other:", r.status_code)

p("== D5 Admin can do the same / AU9 last-admin")
# reset: ops_taken & friends fine. Disable ceo2 so admin is sole enabled
def adm(label, method, path, **kw):
    return probe("admin", label, method, path, **kw)
adm("disable ceo2", "POST", f"/admin/users/{ceo2_id}/disable")
adm("admin disable SELF (ceo2 disabled -> last)", "POST", f"/admin/users/{admin_id}/disable")
adm("admin delete SELF", "POST", f"/admin/users/{admin_id}/delete")
adm("admin remove self from all groups", "POST", f"/admin/users/{admin_id}/groups")
adm("untick users.manage on Admin/CEO", "POST", f"/admin/groups/{ADM_G}", data={"name": "Admin/CEO", "permission": [x for x in groups.get_group(ADM_G).permissions if x != "users.manage"]})
adm("remove admin via group member list", "POST", f"/admin/groups/{ADM_G}", data={"name": "Admin/CEO", "permission": groups.get_group(ADM_G).permissions, "members_shown": "1", "member_id": [str(ceo2_id)]})
adm("delete Admin/CEO group", "POST", f"/admin/groups/{ADM_G}/delete", data={"confirm": "yes"})
adm("delete disabled ceo2 (leaves sole admin)", "POST", f"/admin/users/{ceo2_id}/delete")
adm("enable no-op", "POST", f"/admin/users/{victim_id}/enable")
adm("admin adds custom to Admin/CEO (allowed)", "POST", f"/admin/users/{cust_id}/groups", data=[("group_id", str(ADM_G)), ("group_id", str(cg.id))])
adm("admin ticks settings.manage on Ops (allowed)", "POST", f"/admin/groups/{og.id}", data={"name": "Ops", "permission": ["settings.manage"]})
adm("admin creates group w/ credentials.view", "POST", "/admin/groups", data={"name": "CredView", "permission": ["credentials.view"]})
adm("admin resets ceo password (now 2 admins: custom + admin)", "POST", f"/admin/users/{cust_id}/password", data={"password": PW2})
adm("admin disable custom (now an Admin) - allowed with other admin", "POST", f"/admin/users/{cust_id}/disable")
# (last admin self-disable runs after D6)
p("final Admin/CEO members:", groups.get_group(ADM_G).member_ids, "enabled admins:", [u.email for u in accounts.list_users() if "Admin/CEO" in u.groups and not u.disabled])

p("== D6 XSS in rendered admin pages (script-tag email/group/display name)")
accounts.signup("<script>alert(1)</script>@x.test", PW)
groups.create_group("<img src=x onerror=alert(2)>", [])
accounts.set_display_name(accounts.find_user("victim@team.test").id, "<b onmouseover=alert(3)>x")
r = req(cookies["admin"], "GET", "/admin/users")
p(" /admin/users raw '<script>alert(1)' present:", "<script>alert(1)" in r.text, " raw '<img src=x onerror' present:", "<img src=x onerror" in r.text,
  " raw '<b onmouseover' present:", "<b onmouseover" in r.text, " status", r.status_code)

adm("admin disable SELF (custom disabled -> sole)", "POST", f"/admin/users/{admin_id}/disable")

p("== D7 destructive edits by a non-admin groups.manage holder (run last; they break the cast)")
cookies["custom"] = cookies["custom"]  # custom is an Admin now (D5), so use a fresh non-admin manager
mgr_id = mk("mgr@team.test")
groups.update_group(cg.id, "CustomMgr", ["users.manage", "groups.manage"], [mgr_id])
groups.update_group(ADM_G, "Admin/CEO", groups.get_group(ADM_G).permissions, [admin_id])
cookies["mgr"] = login("mgr@team.test")
ID["mgr"] = mgr_id
probe("mgr", "delete default group Tester (non-admin group)", "POST", f"/admin/groups/{gid('tester')}/delete", data={"confirm": "yes"})
probe("mgr", "untick all from Developer group", "POST", f"/admin/groups/{gid('developer')}", data={"name": "Developer"})
probe("mgr", "untick all from Sub-admin group", "POST", f"/admin/groups/{gid('sub-admin')}", data={"name": "Sub-admin"})
p("   Tester group still there:", any(g.seed == "tester" for g in groups.list_groups()), "| Developer perms now:", len(groups.get_group(gid('developer')).permissions))
p("   dev (Developer group stripped) now sees:", req(cookies["dev"], "GET", "/").status_code)
p("   mgr can restore Developer perms?:", probe("mgr", "re-tick project.view@own", "POST", f"/admin/groups/{gid('developer')}", data={"name": "Developer", "permission": "project.view@own"})[0].status_code)

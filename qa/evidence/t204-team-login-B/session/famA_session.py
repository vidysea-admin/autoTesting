from common import *
root = setup("famA")
import re, subprocess, hashlib
from datetime import datetime
from fastapi.testclient import TestClient
from autotester.ui.app import app
from autotester.auth.ratelimit import login_limiter, signup_limiter

ADMIN = "admin@team.test"


def C(base="http://testserver"):
    return TestClient(app, follow_redirects=False, base_url=base)


def req(method, path, cookie=None, base="http://testserver", headers=None, **kw):
    c = C(base)
    h = dict(headers or {})
    if cookie:
        h["Cookie"] = cookie
    return c.request(method, path, headers=h, **kw)


def sc(resp):
    return resp.headers.get_list("set-cookie")


def cookie_of(resp):
    for s in sc(resp):
        m = re.match(r"([^=]+)=([^;]*)", s)
        if m and m.group(2) and "Max-Age=0" not in s:
            return f"{m.group(1)}={m.group(2)}", s
    return None, None


def short(s):
    return re.sub(r"=[A-Za-z0-9_\-]{20,}", "=<tok>", s) if s else s


def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()


p("== A1 cookie flags")
os.environ["AUTOTESTER_HOSTED"] = ""   # local mode
r = req("POST", "/auth/signup", data={"email": ADMIN, "password": PW})
p("local signup first:", r.status_code, [short(s) for s in sc(r)])
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
p("local http login:", r.status_code, r.headers.get("location"), [short(s) for s in sc(r)])
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW}, base="https://testserver")
p("local https-base login:", r.status_code, [short(s) for s in sc(r)])
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
pm = ProxyHeadersMiddleware(app, trusted_hosts="*")
tc = TestClient(pm, follow_redirects=False)
r = tc.post("/auth/login", data={"email": ADMIN, "password": PW}, headers={"X-Forwarded-Proto": "https"})
p("local + XFP https via uvicorn ProxyHeadersMiddleware(trusted *):", r.status_code, [short(s) for s in sc(r)])
r = C().post("/auth/login", data={"email": ADMIN, "password": PW}, headers={"X-Forwarded-Proto": "https"})
p("local + raw XFP https header, app alone (no proxy middleware):", r.status_code, [short(s) for s in sc(r)])
os.environ["AUTOTESTER_HOSTED"] = "1"
os.environ["AUTOTESTER_FIRST_ADMIN_EMAIL"] = ADMIN
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
p("hosted http-base login:", r.status_code, [short(s) for s in sc(r)])
os.environ["AUTOTESTER_COOKIE_SECURE"] = "0"
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
p("hosted + COOKIE_SECURE=0 login:", r.status_code, [short(s) for s in sc(r)])
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW}, base="https://testserver")
p("hosted + COOKIE_SECURE=0 + https base:", r.status_code, [short(s) for s in sc(r)])
for v in ("", "false", "00", " 0 "):
    os.environ["AUTOTESTER_COOKIE_SECURE"] = v
    r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
    p(f"hosted + COOKIE_SECURE={v!r}:", [short(s)[:40] for s in sc(r)])
del os.environ["AUTOTESTER_COOKIE_SECURE"]
r = req("POST", "/auth/logout", cookie=None)
p("logout set-cookie (unauth):", r.status_code, [short(s) for s in sc(r)])

p("== A2 fixation")
os.environ["AUTOTESTER_HOSTED"] = ""
login_limiter.reset()
PRESET = "ATTACKERCHOSENVALUE0123456789abcdefghij0123456789"
attacker = "at_session=" + PRESET
r1 = req("POST", "/auth/login", cookie=attacker, data={"email": ADMIN, "password": PW})
c1, s1 = cookie_of(r1)
p("login with preset cookie: new cookie value != preset:", c1 is not None and PRESET not in (c1 or ""))
p("attacker value present in sessions table:",
  q(root, "select count(*) n from sessions where token_hash=?", (sha(PRESET),))[0]["n"])
p("preset cookie used after login:", req("GET", "/", cookie=attacker).status_code)
r2 = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
c2, _ = cookie_of(r2)
p("two logins same user -> distinct ids:", c1 != c2, " token length:", len(c1.split('=')[1]))
p("sessions rows now:", q(root, "select count(*) n from sessions")[0]["n"],
  " stored hash length:", q(root, "select length(token_hash) l from sessions")[0])
raw = c1.split("=")[1]
p("raw token appears in sqlite file bytes:", raw.encode() in open(db_path(root), 'rb').read())
os.environ["AUTOTESTER_HOSTED"] = "1"
r = req("POST", "/auth/login", cookie="__Host-at_session=FIXED123", data={"email": ADMIN, "password": PW})
c3, s3 = cookie_of(r)
p("hosted preset __Host- cookie -> new id:", "FIXED123" not in (c3 or ""), short(s3))
os.environ["AUTOTESTER_HOSTED"] = ""

p("== A3 logout")
login_limiter.reset()
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
ck, _ = cookie_of(r)
p("GET / with cookie:", req("GET", "/", cookie=ck).status_code)
n0 = q(root, "select count(*) n from sessions")[0]["n"]
g = req("GET", "/auth/logout", cookie=ck)
n1 = q(root, "select count(*) n from sessions")[0]["n"]
p("GET /auth/logout:", g.status_code, "sessions before/after:", n0, n1,
  "cookie still valid:", req("GET", "/", cookie=ck).status_code)
lo = req("POST", "/auth/logout", cookie=ck, headers={"Accept": "text/html"})
n2 = q(root, "select count(*) n from sessions")[0]["n"]
p("POST logout:", lo.status_code, lo.headers.get("location"), [short(s) for s in sc(lo)], "rows:", n1, "->", n2)
p("replay old cookie html/json:", req("GET", "/", cookie=ck, headers={"Accept": "text/html"}).status_code,
  req("GET", "/", cookie=ck).status_code)
p("logout again with dead cookie:", req("POST", "/auth/logout", cookie=ck).status_code)
p("logout with evil Origin (live cookie first):")
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
ck, _ = cookie_of(r)
cx = req("POST", "/auth/logout", cookie=ck, headers={"Origin": "http://evil.example"})
p("  ->", cx.status_code, "cookie still valid:", req("GET", "/", cookie=ck).status_code)

p("== A4 expiry")
for env in ("1", "0", "-5", "abc", "999999", ""):
    os.environ["AUTOTESTER_SESSION_HOURS"] = env
    r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
    ck, s = cookie_of(r)
    ma = re.search(r"Max-Age=(\d+)", s).group(1)
    row = q(root, "select created_at, expires_at from sessions order by created_at desc limit 1")[0]
    hrs = (datetime.fromisoformat(row["expires_at"]) - datetime.fromisoformat(row["created_at"])).total_seconds() / 3600
    p(f"SESSION_HOURS={env!r}: Max-Age={ma} row lifetime hours={hrs:.2f}")
os.environ.pop("AUTOTESTER_SESSION_HOURS")
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
ck, _ = cookie_of(r)
tokh = sha(ck.split('=')[1])
c = sqlite3.connect(db_path(root))
c.execute("update sessions set expires_at=? where token_hash=?", ("2000-01-01T00:00:00+00:00", tokh))
c.commit()
p("aged row (expires_at=2000) -> request:", req("GET", "/", cookie=ck).status_code,
  " row dropped after refusal:", c.execute("select count(*) from sessions where token_hash=?", (tokh,)).fetchone()[0] == 0)
c.close()
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
ck, _ = cookie_of(r)
tokh = sha(ck.split('=')[1])
c = sqlite3.connect(db_path(root))
c.execute("update sessions set created_at='2000-01-01T00:00:00+00:00' where token_hash=?", (tokh,))
c.commit()
c.close()
p("created_at ancient but expires_at future (check is on expires_at only):", req("GET", "/", cookie=ck).status_code)

p("== A5 tampered cookie")
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
ck, _ = cookie_of(r)
name, val = ck.split("=")


def flip(v):
    return v[:-1] + ("A" if v[-1] != "A" else "B")


cases = {
    "valid": ck, "flip last char": f"{name}={flip(val)}", "truncated": f"{name}={val[:-5]}",
    "appended": f"{name}={val}x", "empty": f"{name}=", "100KB": f"{name}={'a' * 100_000}",
    "129 chars": f"{name}={'a' * 129}", "128 chars": f"{name}={'a' * 128}",
    "dup bad,good": f"{name}=bad; {ck}", "dup good,bad": f"{ck}; {name}=bad",
    "quoted": f'{name}="{val}"', "space-padded": f"{name}= {val}",
    "wrong name": f"x_session={val}", "__Host- name in local mode": f"__Host-at_session={val}",
}
for k, v in cases.items():
    try:
        r = req("GET", "/", cookie=v)
        p(f"  {k:28s} -> {r.status_code}")
    except Exception as e:
        p(f"  {k:28s} -> EXC {type(e).__name__}: {str(e)[:60]}")
try:
    r = C().get("/", headers=[("Cookie", f"{name}=bad"), ("Cookie", ck)])
    p("  two Cookie headers (bad first, good second):", r.status_code)
    r = C().get("/", headers=[("Cookie", ck), ("Cookie", f"{name}=bad")])
    p("  two Cookie headers (good first, bad second):", r.status_code)
except Exception as e:
    p("  two Cookie hdrs EXC", repr(e)[:100])
try:
    r = C().get("/", headers={"Cookie": f"{name}=café中".encode("utf-8")})
    p("  unicode value (utf-8 bytes):", r.status_code)
except Exception as e:
    p("  unicode EXC", repr(e)[:100])
os.environ["AUTOTESTER_HOSTED"] = "1"
os.environ["AUTOTESTER_FIRST_ADMIN_EMAIL"] = ADMIN
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW}, base="https://testserver")
hk, _ = cookie_of(r)
hn, hv = hk.split("=")
H = "https://testserver"
p("hosted cookie name:", hn)
p("  hosted: __Host- cookie works:", req("GET", "/", cookie=hk, base=H).status_code)
p("  hosted: plain at_session with same value (cookie tossing):", req("GET", "/", cookie=f"at_session={hv}", base=H).status_code)
p("  hosted: plain bad + __Host- good:", req("GET", "/", cookie=f"at_session=bad; {hk}", base=H).status_code)
p("  hosted: __Host- bad + plain good:", req("GET", "/", cookie=f"__Host-at_session=bad; at_session={hv}", base=H).status_code)
os.environ["AUTOTESTER_HOSTED"] = ""

p("== A6 state change takes effect on next request (disable/delete/reset/group)")
from autotester.auth import accounts, groups
login_limiter.reset()
signup_limiter.reset()


def gid(seed):
    return next(g.id for g in groups.list_groups() if g.seed == seed)


adm_ck = cookie_of(req("POST", "/auth/login", data={"email": ADMIN, "password": PW}))[0]


def mk(email, seed=None):
    u = accounts.signup(email, PW)
    if seed:
        accounts.set_user_groups(u.id, [gid(seed)])
    return u.id


uid = mk("dev1@team.test", "developer")


def login(email, pw=PW):
    return cookie_of(req("POST", "/auth/login", data={"email": email, "password": pw}))[0]


def adm(action, uid, **data):
    return req("POST", f"/admin/users/{uid}/{action}", cookie=adm_ck, data=data)


d1 = login("dev1@team.test")
p("dev baseline /onboard:", req("GET", "/onboard", cookie=d1).status_code)
r = adm("groups", uid, group_id=str(gid("tester")))
p("group dev->tester:", r.status_code, " next /onboard:", req("GET", "/onboard", cookie=d1).status_code,
  " /:", req("GET", "/", cookie=d1).status_code)
r = adm("groups", uid)
p("group -> none:", r.status_code, " next / json/html:", req("GET", "/", cookie=d1).status_code,
  req("GET", "/", cookie=d1, headers={"Accept": "text/html"}).status_code)
adm("groups", uid, group_id=str(gid("developer")))
p("re-add dev group: /onboard", req("GET", "/onboard", cookie=d1).status_code)
r = adm("disable", uid)
p("disable:", r.status_code, " next:", req("GET", "/", cookie=d1).status_code, " login:",
  req("POST", "/auth/login", data={"email": "dev1@team.test", "password": PW}).status_code)
adm("enable", uid)
p("enable: old cookie (revoked at disable):", req("GET", "/", cookie=d1).status_code, " fresh login:",
  req("POST", "/auth/login", data={"email": "dev1@team.test", "password": PW}).status_code)
d2 = login("dev1@team.test")
d3 = login("dev1@team.test")
p("two concurrent sessions both valid:", req("GET", "/", cookie=d2).status_code, req("GET", "/", cookie=d3).status_code)
req("POST", "/auth/logout", cookie=d2)
p("after logout of one: d2", req("GET", "/", cookie=d2).status_code, " d3", req("GET", "/", cookie=d3).status_code)
r = adm("password", uid, password=PW2)
p("admin reset pw:", r.status_code, " d3 next:", req("GET", "/", cookie=d3).status_code, " old pw login:",
  req("POST", "/auth/login", data={"email": "dev1@team.test", "password": PW}).status_code, " new pw login:",
  req("POST", "/auth/login", data={"email": "dev1@team.test", "password": PW2}).status_code)
d4 = login("dev1@team.test", PW2)
r = adm("delete", uid)
p("delete:", r.status_code, " d4 next:", req("GET", "/", cookie=d4).status_code, " sessions rows for user:",
  q(root, "select count(*) n from sessions where user_id=?", (uid,))[0]["n"])

p("== A7 restart persistence")
r = req("POST", "/auth/login", data={"email": ADMIN, "password": PW})
live, _ = cookie_of(r)
tmp = os.path.join(BASE, "famA_cookie.tmp")
open(tmp, "w").write(live)
code = f"""
import os,sys
sys.path.insert(0,{SRC!r})
os.environ["AUTOTESTER_ROOT"]={root!r}; os.environ["AUTOTESTER_ALLOWED_HOSTS"]="testserver"
for k in {CLEAR!r}:
    if k != "AUTOTESTER_ALLOWED_HOSTS": os.environ.pop(k,None)
from fastapi.testclient import TestClient
from autotester.ui.app import app
ck=open({tmp!r}).read()
c=TestClient(app,follow_redirects=False)
print("new process, old cookie:",c.get("/",headers={{"Cookie":ck}}).status_code)
"""
out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                     env={**os.environ, "PYTHONPATH": SRC})
p(out.stdout.strip(), out.stderr.strip()[-200:])
os.remove(tmp)

from common import *
root = setup("famF")
import re, collections
from fastapi.testclient import TestClient
from autotester.ui.app import app
from autotester.auth.ratelimit import login_limiter, signup_limiter
from autotester.auth import accounts, groups

ADMIN = "admin@team.test"
CAN_Q = "QCANARY" + secrets.token_hex(4)
CAN_B = "BCANARY" + secrets.token_hex(4)
CAN_C = "CCANARY" + secrets.token_hex(4)


def C():
    return TestClient(app, follow_redirects=False, raise_server_exceptions=False)


accounts.signup(ADMIN, PW)
dev = accounts.signup("dev@team.test", PW)
accounts.set_user_groups(dev.id, [next(g.id for g in groups.list_groups() if g.seed == "developer")])
login_limiter.reset()
r = C().post("/auth/login", data={"email": ADMIN, "password": PW})
adm = r.headers["set-cookie"].split(";")[0]


def lines():
    return audit_lines(root)


p("== F1 unauthenticated state-changing requests write nothing")
n0 = len(lines())
sc = []
for m, path in [("POST", "/admin/users/1/delete"), ("POST", "/projects/x/run"), ("POST", "/unknown"), ("POST", "/auth/logout"),
                ("POST", "/settings/providers"), ("POST", "/onboard"), ("DELETE", "/"), ("PUT", "/admin/groups"), ("PATCH", "/admin/groups/1"),
                ("POST", "/admin/groups/1/delete")]:
    rr = C().request(m, path + f"?q={CAN_Q}", data={"password": CAN_B}, headers={"Cookie": f"at_session={CAN_C}"})
    sc.append((m, path, rr.status_code))
p(" statuses:", sc)
p(" audit lines added by 10 unauthenticated state-changing requests:", len(lines()) - n0)
r = C().get("/admin/users")
p(" unauth GET adds:", len(lines()) - n0)

p("== F2 login-failure line, login success, signup lines")
n0 = len(lines())
C().post("/auth/login", data={"email": "  GHOST@Team.TEST ", "password": PW2})
C().post("/auth/login", data={"email": "not an email" + CAN_B, "password": PW2})
C().post("/auth/login", data={"email": "x" * 300 + "@team.test", "password": PW2})
C().post("/auth/login", data={"email": ADMIN, "password": PW2})
login_limiter.reset()
C().post("/auth/login", data={"email": ADMIN, "password": PW})
C().post("/auth/signup", data={"email": "short@team.test", "password": "x"})
C().post("/auth/signup", data={"email": ADMIN, "password": PW})  # duplicate
C().post("/auth/signup", data={"email": "fine@team.test", "password": PW})
for l in lines()[n0:]:
    d = json.loads(l)
    p("  ", {k: v for k, v in d.items() if k != "ts"})
p(" => signup refusals (400) and login 429 leave no trace; login/signup lines are {actor,target,action} only (no method/path/status)")
n0 = len(lines())
for i in range(21):
    C().post("/auth/login", data={"email": f"u{i}@team.test", "password": PW2})
p(" 21 failed logins from one address -> audit lines:", len(lines()) - n0, "(21st = 429, unaudited)")
login_limiter.reset()

p("== F3 authenticated state-changing: lines + secrets scan")
n0 = len(lines())
h = {"Cookie": adm}
C().request("POST", f"/admin/users/{dev.id}/password?leak={CAN_Q}", data={"password": PW2 + CAN_B}, headers={**h, "X-Canary": CAN_C})
C().request("POST", f"/admin/users/{dev.id}/name?leak={CAN_Q}", data={"display_name": "Dev " + CAN_B}, headers=h)
C().request("POST", f"/settings/providers?leak={CAN_Q}", data={"ANTHROPIC_API_KEY": CAN_B}, headers=h)
C().request("POST", f"/nonexistent/{CAN_Q}", data={"a": CAN_B}, headers=h)
C().request("PUT", f"/admin/groups?leak={CAN_Q}", data={"a": CAN_B}, headers=h)
C().request("DELETE", f"/admin/groups/1?leak={CAN_Q}", headers=h)
C().request("POST", f"/admin/groups/99/delete?leak={CAN_Q}", data={"confirm": "yes"}, headers=h)
C().request("POST", f"/projects/{CAN_Q}/run", data={"a": CAN_B}, headers=h)
C().request("POST", "/auth/logout", headers=h)
new = lines()[n0:]
for l in new:
    d = json.loads(l)
    p("  ", {k: v for k, v in d.items() if k != "ts"})
blob = "\n".join(lines())
hit = {n: (x in blob) for n, x in (("query canary", CAN_Q), ("body canary", CAN_B), ("cookie canary", CAN_C), ("session cookie", adm.split("=")[1]), ("password", PW), ("argon2", "argon2"))}
p(" secrets in audit file:", hit)

p("== F4 log injection")
n0 = len(lines())
evil = ['x","actor":"admin@team.test","action":"login"}@b.test', 'a\\"b@b.test', "q'q@b.test", 'a@b.test\r\n{"forged":1}', 'a\nb@b.test', 'a@b.test {"f":1}',
        'a\x85b@b.test', 'lone%ED%A0%80@b.test', '{"x":1}@b.test', 'a@b.test\x1b[31m']
res = []
for e in evil:
    signup_limiter.reset()
    if "%ED" in e:
        rr = C().post("/auth/signup", content=f"email={e}&password={PW}", headers={"Content-Type": "application/x-www-form-urlencoded"})
    else:
        rr = C().post("/auth/signup", data={"email": e, "password": PW})
    login_limiter.reset()
    C().post("/auth/login", data={"email": e, "password": PW2})
    res.append((repr(e)[:50], rr.status_code))
p(" signups:", res)
raw = open(os.path.join(root, ".work", "audit.jsonl"), "rb").read().decode("utf-8")
phys = raw.split("\n")[:-1]
ok = True
for i, l in enumerate(phys):
    try:
        d = json.loads(l)
        assert isinstance(d, dict)
    except Exception:
        ok = False
        p("  NON-JSON physical line", i, repr(l)[:100])
p(" every physical \\n-delimited audit line is one valid JSON object:", ok, "lines:", len(phys))
p(" python splitlines() count == \\n count (no U+2028/U+0085/VT/FF smuggled):", len(raw.splitlines()) == len(phys))
newl = [json.loads(l) for l in phys[len(lines()) - len(phys) + n0:]]
forged = [d for d in [json.loads(l) for l in phys] if "forged" in d or d.get("f") == 1]
p(" forged top-level keys present:", bool(forged))
fake = [json.loads(l) for l in phys if json.loads(l).get("actor") == "admin@team.test" and json.loads(l).get("action") == "login"]
p(" lines claiming actor=admin action=login (genuine count = 1 real login):", len(fake))
# display name / group name through admin routes
n0 = len(lines())
C().request("POST", f"/admin/users/{dev.id}/name", data={"display_name": 'N","action":"x\nforged'}, headers={"Cookie": adm})
login_limiter.reset()
r = C().post("/auth/login", data={"email": ADMIN, "password": PW})
adm = r.headers["set-cookie"].split(";")[0]
C().request("POST", "/admin/groups", data={"name": 'G","actor":"root" x'}, headers={"Cookie": adm})
raw = open(os.path.join(root, ".work", "audit.jsonl"), "rb").read().decode("utf-8")
p(" after display-name/group-name injection: all lines JSON:", all(json.loads(l) for l in raw.split("\n")[:-1]), "splitlines==\\n:", len(raw.splitlines()) == len(raw.split("\n")) - 1)
p("== F5 summary of line shapes")
shape = collections.Counter(tuple(sorted(k for k in json.loads(l) if k != "ts")) for l in raw.split("\n")[:-1])
for k, v in shape.items():
    p("  ", v, k)
st = os.stat(os.path.join(root, ".work", "audit.jsonl"))
p(" audit file mode (Windows, informational):", oct(st.st_mode)[-3:], "size bytes:", st.st_size)

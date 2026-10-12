from common import *
root = setup("famB")
import io, logging, re, statistics, hashlib, glob
from fastapi.testclient import TestClient

# capture ALL logging at DEBUG before importing the app
buf = io.StringIO()
h = logging.StreamHandler(buf)
h.setLevel(logging.DEBUG)
logging.getLogger().addHandler(h)
logging.getLogger().setLevel(logging.DEBUG)
for n in ("uvicorn", "uvicorn.error", "uvicorn.access", "starlette", "fastapi", "autotester", "httpx", "httpcore",
          "multipart", "python_multipart", "asyncio", "argon2"):
    lg = logging.getLogger(n)
    lg.setLevel(logging.DEBUG)
    lg.propagate = True
errbuf = io.StringIO()
real_stderr, real_stdout = sys.stderr, sys.stdout

from autotester.ui.app import app
from autotester.auth.ratelimit import login_limiter, signup_limiter
from autotester.auth import accounts, groups

ALL = []   # every response (status, headers, body text, request path) for canary scan


class Rec(TestClient):
    def request(self, *a, **kw):
        r = super().request(*a, **kw)
        ALL.append((a, r.status_code, dict(r.headers), r.text, str(r.url)))
        return r


def C(**kw):
    return Rec(app, follow_redirects=False, raise_server_exceptions=False, **kw)


ADMIN = "admin@team.test"
CAN = [PW, PW2]
p("canaries (prefix only):", PW[:11], "...")

# ---- B1: hashing & storage -----------------------------------------------------------
p("== B1 storage")
c = C()
r = c.post("/auth/signup", data={"email": ADMIN, "password": PW})
p("signup admin:", r.status_code)
for em in ("u1@team.test", "u2@team.test"):
    r = C().post("/auth/signup", data={"email": em, "password": PW})
    p(f"signup {em} (same password):", r.status_code)
rows = q(root, "select email, password_hash from users order by id")
pat = re.compile(r"^\$argon2id\$v=(\d+)\$m=(\d+),t=(\d+),p=(\d+)\$([^$]+)\$([^$]+)$")
salts = set()
hashes = set()
for row in rows:
    m = pat.match(row["password_hash"])
    p("  ", row["email"], "prefix ok:" , bool(m), "v/m/t/p:", m.groups()[:4] if m else None, "salt b64 len:", len(m.group(5)), "hash len:", len(m.group(6)))
    salts.add(m.group(5))
    hashes.add(row["password_hash"])
p("distinct salts / distinct full hashes among 3 users with the SAME password:", len(salts), len(hashes))
ver = q(root, "select sqlite_version() v")[0]["v"]

# ---- B2: flows to feed logs, audit, responses --------------------------------------------
p("== B2 flows")
login_limiter.reset(); signup_limiter.reset()
C().post("/auth/login", data={"email": ADMIN, "password": PW})
C().post("/auth/login", data={"email": ADMIN, "password": PW2})          # wrong
C().post("/auth/login", data={"email": "nobody@team.test", "password": PW2})  # unknown
login_limiter.reset()
ck = C().post("/auth/login", data={"email": ADMIN, "password": PW}).headers["set-cookie"].split(";")[0]
cl = C()
cl.headers["Cookie"] = ck
uid = rows[1]["email"]
u1 = accounts.find_user("u1@team.test").id
r = cl.post(f"/admin/users/{u1}/password", data={"password": PW2})
p("admin reset u1 password to PW2:", r.status_code)
r = cl.post(f"/admin/users/{u1}/password", data={"password": "short" + PW[:3]})
p("admin reset with weak:", r.status_code, "body echoes the weak password:", ("short" + PW[:3]) in r.text)
r = cl.post(f"/admin/users/{u1}/disable")
login_limiter.reset()
r = C().post("/auth/login", data={"email": "u1@team.test", "password": PW2})
p("disabled account login:", r.status_code)
# weak signup
r = C().post("/auth/signup", data={"email": "weak@team.test", "password": PW[:6]})
p("short password signup:", r.status_code, "echo:", PW[:6] in r.text)
r = C().post("/auth/signup", data={"email": "long@team.test", "password": PW + "x" * 130})
p("129+ password signup:", r.status_code, "echo canary:", PW in r.text)
# malformed forms / error paths
bad = []
def attempt(label, **kw):
    try:
        r = C().post("/auth/login", **kw)
        bad.append((label, r.status_code, PW in r.text or PW2 in r.text, len(r.text)))
    except Exception as e:
        bad.append((label, "EXC " + type(e).__name__, False, 0))
attempt("json body", json={"email": ADMIN, "password": PW})
attempt("json content-type, form body", content=f"email={ADMIN}&password={PW}", headers={"Content-Type": "application/json"})
attempt("multipart no boundary", content=f"--x\r\nContent-Disposition: form-data; name=password\r\n\r\n{PW}", headers={"Content-Type": "multipart/form-data"})
attempt("multipart bad boundary", content=f"--x\r\nContent-Disposition: form-data; name=password\r\n\r\n{PW}\r\n--x--", headers={"Content-Type": "multipart/form-data; boundary=y"})
attempt("urlencoded bad percent", content=f"email={ADMIN}&password={PW}%ZZ%", headers={"Content-Type": "application/x-www-form-urlencoded"})
attempt("lone surrogate pct-encoded", content=f"email={ADMIN}&password={PW}%ED%A0%80", headers={"Content-Type": "application/x-www-form-urlencoded"})
attempt("invalid utf8 byte", content=f"email={ADMIN}&password={PW}%FF".encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
attempt("NUL in password", data={"email": ADMIN, "password": PW + "\x00"})
attempt("no content-type with body", content=f"email={ADMIN}&password={PW}")
attempt("dup password fields", content=f"email={ADMIN}&password=bad&password={PW}", headers={"Content-Type": "application/x-www-form-urlencoded"})
attempt("next=password", data={"email": ADMIN, "password": PW2, "next": "/" + PW2})
for b in bad:
    p("  ", b)
# admin route validation error (non-int id)
r = cl.post(f"/admin/users/abc/password", data={"password": PW})
p("admin /users/abc/password:", r.status_code, "echo canary:", PW in r.text, r.text[:160].replace("\n", " "))
r = cl.post(f"/admin/users/{u1}/password", content=f"password={PW}%ED%A0%80", headers={"Content-Type": "application/x-www-form-urlencoded"})
p("admin reset with lone surrogate:", r.status_code)
# signup with a surrogate
r = C().post("/auth/signup", content=f"email=sur@team.test&password={PW}%ED%A0%80", headers={"Content-Type": "application/x-www-form-urlencoded"})
p("signup w/ lone-surrogate password:", r.status_code, r.text[:120].replace("\n", " "))

# ---- scans ----------------------------------------------------------------------------
p("== B3 canary scans")
sys.stdout, sys.stderr = real_stdout, real_stderr
logtxt = buf.getvalue()
p("captured log bytes:", len(logtxt), " canary in logging capture:", any(x in logtxt for x in CAN))
hits = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        pth = os.path.join(dp, f)
        data = open(pth, "rb").read()
        for x in CAN:
            if x.encode() in data or x.encode("utf-16-le") in data:
                hits.append(pth)
        p("   file", os.path.relpath(pth, root), len(data), "bytes")
p("canary in any file under data root:", hits)
rh = [(a[0][1] if a and len(a[0]) > 1 else "?", s) for a, s, hd, body, url in ALL
      if any(x in body or x in json.dumps(hd) or x in url for x in CAN)]
p("canary in any response body/header/url (", len(ALL), "responses ):", rh)
au = "\n".join(audit_lines(root))
p("audit lines:", len(audit_lines(root)), " canary in audit:", any(x in au for x in CAN))
for l in audit_lines(root)[:50]:
    d = json.loads(l)
    p("   audit", {k: v for k, v in d.items() if k != "ts"})
# pwd hash not in audit/response
hashfrag = "argon2id"
p("'argon2' in audit / any response:", "argon2" in au, any("argon2" in b or "argon2" in json.dumps(hd) for a, s, hd, b, u in ALL))

# ---- B4: AU2 equality + timing ----------------------------------------------------------
p("== B4 AU2 equality and timing")
login_limiter.reset(); signup_limiter.reset()
# prepare: disabled user with real password
accounts.signup("dis@team.test", PW)
dis_id = accounts.find_user("dis@team.test").id
accounts.set_disabled(dis_id, True)
accounts.signup("real@team.test", PW)
# cheap-hash user (low-cost params), simulating an account hashed before a parameter upgrade
from argon2 import PasswordHasher
cheap = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PW)
accounts.signup("cheap@team.test", PW)
cc = sqlite3.connect(db_path(root)); cc.execute("update users set password_hash=? where email='cheap@team.test'", (cheap,)); cc.commit(); cc.close()
cases = {
    "unknown": ("ghost@team.test", PW2), "wrong pw": ("real@team.test", PW2),
    "disabled (right pw)": ("dis@team.test", PW), "disabled (wrong pw)": ("dis@team.test", PW2),
    "cheap-hash user, wrong pw": ("cheap@team.test", PW2), "right pw": ("real@team.test", PW),
}
samples = {k: [] for k in cases}
bodies = {k: set() for k in cases}
stat = {k: set() for k in cases}
c2 = C()
for i in range(25):
    for k, (em, pw) in cases.items():
        login_limiter.reset()
        t = time.perf_counter()
        r = c2.post("/auth/login", data={"email": em, "password": pw, "next": "/"})
        samples[k].append((time.perf_counter() - t) * 1000)
        stat[k].add(r.status_code)
        bodies[k].add(hashlib.sha256(r.content).hexdigest())
for k in cases:
    s = samples[k]
    p(f"  {k:28s} status={sorted(stat[k])} distinct bodies={len(bodies[k])} median={statistics.median(s):7.1f}ms min={min(s):7.1f} max={max(s):7.1f} n={len(s)}")
fail = [k for k in cases if k != "right pw"]
p("  failure cases share one body hash:", len(set().union(*[bodies[k] for k in fail])) == 1)
h = lambda k: statistics.median(samples[k])
p(f"  ratio wrong/unknown={h('wrong pw') / h('unknown'):.2f}  disabled/unknown={h('disabled (right pw)') / h('unknown'):.2f}  cheap/unknown={h('cheap-hash user, wrong pw') / h('unknown'):.2f}")
# invalid-format email path
ts = []
for i in range(10):
    login_limiter.reset()
    t = time.perf_counter(); C().post("/auth/login", data={"email": "not-an-email", "password": PW2}); ts.append((time.perf_counter() - t) * 1000)
p(f"  invalid-format email median={statistics.median(ts):.1f}ms")
ts = []
for i in range(10):
    login_limiter.reset()
    t = time.perf_counter(); C().post("/auth/login", data={"email": "", "password": ""}); ts.append((time.perf_counter() - t) * 1000)
p(f"  empty email+password median={statistics.median(ts):.1f}ms")

# ---- B5: email / password normalisation -----------------------------------------------
p("== B5 normalisation")
import unicodedata
login_limiter.reset(); signup_limiter.reset()


def su(email, pw=PW):
    signup_limiter.reset()
    r = C().post("/auth/signup", data={"email": email, "password": pw})
    return r.status_code, (re.search(r"class=.?error.?[^>]*>([^<]+)", r.text) or re.search(r"<p[^>]*>([^<]*(?:valid|exist)[^<]*)", r.text) or [None, ""])[1] if r.status_code != 303 else ""


for em in ["Admin@Team.test", " a@b.test ", "a@b.test", "a@b.test\n", "A@B.TEST", "a@b.test%00", "a@b.test\x00", "a+tag@b.test",
           "ａ@b.test", "İ@b.test", "ı@b.test", "K@b.test", "k@b.test", unicodedata.normalize("NFC", "café@b.test"),
           unicodedata.normalize("NFD", "café@b.test"), "a b@b.test", "a@b@b.test", "@b.test", "a@b", "a@.test.", "\"x\"@b.test", "<i/src=x/onerror=alert(1)>@b.test"]:
    st, msg = su(em)
    p(f"  signup {em!r:50s} -> {st} {msg}")
emails = [r["email"] for r in q(root, "select email from users order by id")]
p("stored email forms (repr):", [e for e in emails if not e.endswith("team.test")])
# login with case variants / NFC-NFD password
login_limiter.reset()
for label, em, pw in [("login UPPER", "ADMIN@TEAM.TEST", PW), ("login padded", "  admin@team.test ", PW),
                      ("login trailing newline", "admin@team.test\n", PW)]:
    login_limiter.reset()
    p(" ", label, C().post("/auth/login", data={"email": em, "password": pw}).status_code)
npw = "Zq7-canary-café-" + secrets.token_hex(3)
su("nfc@b.test", npw)
for label, pw in [("same NFC", npw), ("NFD of same", unicodedata.normalize("NFD", npw)), ("NFKC fullwidth", npw.replace("Z", "Ｚ"))]:
    login_limiter.reset()
    p("  password", label, C().post("/auth/login", data={"email": "nfc@b.test", "password": pw}).status_code)
# whitespace-only / leading-trailing space pw
for label, pw in [("whitespace-only 12", " " * 12), ("lead/trail spaces", "  " + PW + "  "), ("NUL inside", PW + "\x00zz"), ("emoji 10", "\U0001F600" * 10), ("9 chars", "a" * 9), ("10 chars", "a" * 10), ("128", "a" * 128), ("129", "a" * 129)]:
    e = f"pw{abs(hash(label)) % 99999}@b.test"
    st = su(e, pw)
    login_limiter.reset()
    lg = C().post("/auth/login", data={"email": e, "password": pw}).status_code if st[0] == 303 else "-"
    p(f"  signup pw {label:20s} -> {st[0]} {st[1]}  re-login same exact pw -> {lg}")
# existing email response compare
signup_limiter.reset()
r_fresh = C().post("/auth/signup", data={"email": "fresh1@b.test", "password": PW})
signup_limiter.reset()
r_dup = C().post("/auth/signup", data={"email": "fresh1@b.test", "password": PW2})
p("fresh signup:", r_fresh.status_code, "location", r_fresh.headers.get("location"), "| duplicate:", r_dup.status_code, re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", r_dup.text))[-120:])
r = C().post("/auth/login", data={"email": "fresh1@b.test", "password": PW2})
p("   existing account untouched by dup signup (login with dup-signup pw):", r.status_code, "(401 expected)")

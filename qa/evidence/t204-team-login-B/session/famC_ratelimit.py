from common import *
root = setup("famC")
import re, hashlib, tracemalloc
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from autotester.ui.app import app
from autotester.auth import ratelimit
from autotester.auth.ratelimit import login_limiter, signup_limiter, WINDOW_SECONDS, LoginRateLimiter
from autotester.auth import accounts

p("constants: per_account", ratelimit.MAX_FAILURES_PER_ACCOUNT, "per_address", ratelimit.MAX_FAILURES_PER_ADDRESS,
  "signups/addr", ratelimit.MAX_SIGNUPS_PER_ADDRESS, "window s", WINDOW_SECONDS, "max tracked keys", ratelimit.MAX_TRACKED_KEYS)

ADMIN = "admin@team.test"
VICTIM = "victim@team.test"
accounts.signup(ADMIN, PW)
accounts.signup(VICTIM, PW)


def C(addr="203.0.113.7", target=None, **kw):
    return TestClient(target or app, follow_redirects=False, client=(addr, 4444), **kw)


def login(c, email, pw, **hdr):
    return c.post("/auth/login", data={"email": email, "password": pw}, headers=hdr)


def txt(r):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[-110:]


def reset():
    login_limiter.reset(); signup_limiter.reset()


# C1 per-address across different emails
p("== C1 20 failures across DIFFERENT emails from one address")
reset()
a = C("198.51.100.1")
codes = [login(a, f"ghost{i}@team.test", PW2).status_code for i in range(24)]
p(" statuses for 24 attempts:", codes)
p(" same address, right password for victim:", login(a, VICTIM, PW).status_code, "| admin right pw:", login(a, ADMIN, PW).status_code)
b = C("198.51.100.2")
p(" other address, right password:", login(b, VICTIM, PW).status_code)
r429 = login(a, VICTIM, PW)
p(" 429 headers:", {k: v for k, v in r429.headers.items() if k.lower() in ("retry-after", "content-type", "cache-control")})
p(" 429 body tail:", txt(r429))

# C2 which header does the limiter key on?
p("== C2 spoofed XFF / X-Real-IP / Forwarded with default app (no proxy middleware)")
reset()
a = C("198.51.100.3")
codes = [login(a, f"g{i}@team.test", PW2, **{"X-Forwarded-For": f"10.9.{i}.{i}"}).status_code for i in range(24)]
p(" XFF varied per request, 24 failures:", codes)
reset()
codes = [login(a, f"g{i}@team.test", PW2, **{"X-Real-IP": f"10.8.{i}.1", "Forwarded": f"for=10.7.{i}.1"}).status_code for i in range(24)]
p(" X-Real-IP + Forwarded varied:", codes)
reset()
codes = [login(a, f"g{i}@team.test", PW2).status_code for i in range(22)]
p(" no header, 22 failures:", codes[-4:], "first 429 at attempt", codes.index(429) + 1 if 429 in codes else None)
# (misconfigured) trusted proxy middleware: uvicorn --forwarded-allow-ips='*'
reset()
pm = ProxyHeadersMiddleware(app, trusted_hosts="*")
a = C("198.51.100.4", target=pm)
codes = [login(a, f"g{i}@team.test", PW2, **{"X-Forwarded-For": f"10.6.{i}.1"}).status_code for i in range(40)]
p(" WITH trusted_hosts='*' (FORWARDED_ALLOW_IPS=*): XFF varied, 40 failures, any 429?:", 429 in codes, "(spoof bypasses address limit)")
reset()
codes = [login(a, VICTIM, PW2, **{"X-Forwarded-For": f"10.5.{i}.1"}).status_code for i in range(10)]
p(" WITH trusted '*': per-account limit still holds vs XFF-varying single victim:", codes)
# default uvicorn: trusts only 127.0.0.1
reset()
pm2 = ProxyHeadersMiddleware(app, trusted_hosts="127.0.0.1")
a = C("10.0.0.2", target=pm2)
codes = [login(a, f"g{i}@team.test", PW2, **{"X-Forwarded-For": f"10.4.{i}.1"}).status_code for i in range(24)]
p(" default uvicorn trust (127.0.0.1) + client=10.0.0.2 proxy: XFF ignored ->", codes[-4:])

# C3 victim lockout / DoS
p("== C3 lock a victim from anywhere")
reset()
atk = C("192.0.2.10")
codes = [login(atk, VICTIM, PW2).status_code for _ in range(7)]
p(" attacker 7 wrong logins vs victim:", codes)
ok = C("198.51.100.99")
r = login(ok, VICTIM, PW)
p(" victim (different address), CORRECT password:", r.status_code, "|", txt(r))
r_nx = None
for _ in range(7):
    r_nx = login(atk, "doesnotexist@team.test", PW2)
r_nx2 = login(C("198.51.100.98"), "doesnotexist@team.test", PW)
r_ex2 = login(C("198.51.100.97"), VICTIM, PW)
p(" 429 body identical existing vs non-existing locked account:", r_nx2.content == r_ex2.content, r_nx2.status_code, r_ex2.status_code)
# per-account 429 body vs per-address 429 body
reset()
a = C("198.51.100.20")
for i in range(20): login(a, f"z{i}@team.test", PW2)
r_addr = login(a, VICTIM, PW)
reset()
for _ in range(5): login(C("198.51.100.21"), VICTIM, PW2)
r_acct = login(C("198.51.100.22"), VICTIM, PW)
p(" 429 body identical (address-lock vs account-lock):", r_addr.content == r_acct.content)
# expiry via the limiter's injectable clock
p("== C3b expiry (limiter clock is the injectable `_clock`; routes use module singleton)")
reset()
now = [1000.0]
orig = login_limiter._clock
login_limiter._clock = lambda: now[0]
for _ in range(5): login(C("192.0.2.30"), VICTIM, PW2)
p(" t0 locked:", login(C("192.0.2.31"), VICTIM, PW).status_code)
now[0] += WINDOW_SECONDS - 1
p(" t0+599s:", login(C("192.0.2.31"), VICTIM, PW).status_code)
now[0] += 2
p(" t0+601s:", login(C("192.0.2.31"), VICTIM, PW).status_code)
# hammering during the lock does not extend it?
reset(); now[0] = 5000.0
for _ in range(5): login(C("192.0.2.40"), VICTIM, PW2)
now[0] += 300
for _ in range(50): login(C("192.0.2.41"), VICTIM, PW2)
now[0] += 301   # 601 s after first failure
p(" hammered 50x during lock at t0+300; at t0+601 victim right pw:", login(C("192.0.2.42"), VICTIM, PW).status_code, "(200/303 => hammering does not extend)")
# does success reset counters?
reset(); now[0] = 9000.0
for _ in range(4): login(C("192.0.2.50"), VICTIM, PW2)
s = login(C("192.0.2.51"), VICTIM, PW).status_code
l5 = login(C("192.0.2.52"), VICTIM, PW2).status_code
p(" 4 failures, 1 success (", s, "), 1 more failure ->", l5, "then right pw:", login(C("192.0.2.53"), VICTIM, PW).status_code, "(429 => success does not reset counter)")
login_limiter._clock = orig

# C4 compose/Caddy topology
p("== C4 Caddy topology: every request arrives from the proxy 10.0.0.2")
reset()
proxy_c = lambda: C("10.0.0.2")
codes = [login(proxy_c(), f"anon{i}@x.test", PW2, **{"X-Forwarded-For": f"203.0.113.{i}"}).status_code for i in range(21)]
p(" attacker 21 failures with varied XFF:", codes[-3:])
p(" legit admin, right password, other XFF:", login(proxy_c(), ADMIN, PW, **{"X-Forwarded-For": "198.51.100.200"}).status_code)
p(" legit victim right password:", login(proxy_c(), VICTIM, PW).status_code)
# signup limiter
p("== C5 signup limiter")
reset()
codes = []
for i in range(14):
    codes.append(C("198.51.100.60").post("/auth/signup", data={"email": f"mass{i}@x.test", "password": PW}, headers={"X-Forwarded-For": f"9.9.9.{i}"}).status_code)
p(" 14 signups from one address (XFF varied):", codes)
n = q(root, "select count(*) n from users")[0]["n"]
p(" users in store:", n)
reset()
codes = [C("10.0.0.2").post("/auth/signup", data={"email": f"proxy{i}@x.test", "password": PW}, headers={"X-Forwarded-For": f"9.8.7.{i}"}).status_code for i in range(12)]
p(" Caddy topology, 12 signups with distinct XFF:", codes, "(11th+ refused for EVERYONE behind the proxy)")
# signup failure counting & the same limiter for different addresses
reset()
codes = [C(f"198.51.101.{i}").post("/auth/signup", data={"email": f"bulk{i}@x.test", "password": PW}).status_code for i in range(60)]
p(" 60 signups from 60 different addresses:", set(codes), "-> no global signup cap; count users:", q(root, "select count(*) n from users")[0]["n"])
# table cap
p("== C6 tracked-key cap")
lim = LoginRateLimiter()
for i in range(ratelimit.MAX_TRACKED_KEYS):
    lim.record_failure(f"e{i}", f"a{i}")
p(" keys tracked after 50k record_failure calls:", len(lim._failures))
for _ in range(10):
    lim.record_failure("victim-new@x.test", "fresh-addr")
p(" fresh victim key tracked:", "acct:victim-new@x.test" in lim._failures, " blocked after 10 failures:", lim.blocked("victim-new@x.test", "fresh-addr"))
# invalid-format emails share one key
reset()
codes = [login(C(f"198.51.102.{i}"), f"bad format {i}", PW2).status_code for i in range(7)]
p(" invalid-format emails from 7 addresses share acct '' key:", codes)
p(" ...then a valid-format login for victim from same addrs:", login(C("198.51.102.1"), VICTIM, PW).status_code)

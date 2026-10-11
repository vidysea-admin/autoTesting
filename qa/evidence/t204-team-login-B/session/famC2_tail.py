from common import *
root = setup("famC2")
import re
from fastapi.testclient import TestClient
from autotester.ui.app import app
from autotester.auth import ratelimit, accounts
from autotester.auth.ratelimit import login_limiter, signup_limiter, LoginRateLimiter

VICTIM = "victim@team.test"
accounts.signup("admin@team.test", PW)
accounts.signup(VICTIM, PW)


def C(addr):
    return TestClient(app, follow_redirects=False, client=(addr, 4444))


def reset():
    login_limiter.reset(); signup_limiter.reset()


p("== C5b signups from many addresses (continuation)")
reset()
t = time.perf_counter()
codes = [C(f"198.51.101.{i}").post("/auth/signup", data={"email": f"bulk{i}@x.test", "password": PW}).status_code for i in range(40)]
p(" 40 signups from 40 different addresses:", set(codes), "users:", q(root, "select count(*) n from users")[0]["n"],
  f"{time.perf_counter() - t:.1f}s -> no global signup cap, no user-count cap")
p("== C6 tracked-key cap")
lim = LoginRateLimiter()
for i in range(ratelimit.MAX_TRACKED_KEYS):
    lim.record_failure(f"e{i}", f"a{i}")
p(" keys tracked after 50k record_failure calls (2 keys each => 100k attempted):", len(lim._failures))
for _ in range(10):
    lim.record_failure("victim-new@x.test", "fresh-addr")
p(" fresh victim key tracked:", "acct:victim-new@x.test" in lim._failures, " blocked after 10 failures:", lim.blocked("victim-new@x.test", "fresh-addr"))
reset()
codes = [C(f"198.51.102.{i}").post("/auth/login", data={"email": f"bad format {i}", "password": PW2}).status_code for i in range(7)]
p(" invalid-format emails from 7 addresses share acct '' key:", codes)
p(" then valid login for victim from one of those addrs:", C("198.51.102.1").post("/auth/login", data={"email": VICTIM, "password": PW}).status_code)

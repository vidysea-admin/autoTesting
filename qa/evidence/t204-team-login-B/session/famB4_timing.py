from common import *
root = setup("famB4")
import statistics, hashlib
from fastapi.testclient import TestClient
from argon2 import PasswordHasher
from autotester.ui.app import app
from autotester.auth.ratelimit import login_limiter
from autotester.auth import accounts
accounts.signup("admin@team.test", PW)
accounts.signup("real@team.test", PW)
accounts.signup("dis@team.test", PW); accounts.set_disabled(accounts.find_user("dis@team.test").id, True)
accounts.signup("cheap@team.test", PW)
cc = sqlite3.connect(db_path(root)); cc.execute("update users set password_hash=? where email='cheap@team.test'", (PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PW),)); cc.commit(); cc.close()
cases = {"unknown": ("ghost@team.test", PW2), "wrong pw": ("real@team.test", PW2), "disabled (right pw)": ("dis@team.test", PW),
         "disabled (wrong pw)": ("dis@team.test", PW2), "invalid-format email": ("nope", PW2), "legacy cheap-hash, wrong pw": ("cheap@team.test", PW2), "right pw": ("real@team.test", PW)}
S = {k: [] for k in cases}; B = {k: set() for k in cases}; ST = {k: set() for k in cases}
c = TestClient(app, follow_redirects=False)
for i in range(25):
    for k, (em, pw) in cases.items():
        login_limiter.reset()
        t = time.perf_counter(); r = c.post("/auth/login", data={"email": em, "password": pw, "next": "/"}); S[k].append((time.perf_counter() - t) * 1000)
        ST[k].add(r.status_code); B[k].add(hashlib.sha256(r.content).hexdigest())
for k in cases:
    s = S[k]; p(f"  {k:30s} status={sorted(ST[k])} bodies={len(B[k])} median={statistics.median(s):6.1f}ms p10={sorted(s)[2]:6.1f} p90={sorted(s)[-3]:6.1f} n={len(s)}")
fails = [k for k in cases if k not in ("right pw", "legacy cheap-hash, wrong pw")]
p("  failure cases (unknown/wrong/disabled x2/invalid) one body hash:", len(set().union(*[B[k] for k in cases if k != 'right pw'])) == 1)

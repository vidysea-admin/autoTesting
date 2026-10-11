import sys, time
sys.path.insert(0, "D:/autoTesting/.worktrees/t204-team-login/src")
from autotester.auth import ratelimit
from autotester.auth.ratelimit import LoginRateLimiter
lim = LoginRateLimiter()
for i in range(25_000):
    lim.record_failure(f"e{i}", f"a{i}")
print("keys:", len(lim._failures))
t = time.perf_counter()
for i in range(20):
    lim.record_failure(f"x{i}", f"y{i}")
print("keys after 20 more:", len(lim._failures), f"avg ms per record_failure at full table: {(time.perf_counter()-t)/20*1000:.1f}")
t = time.perf_counter(); lim.blocked("v@x.test", "q"); print(f"blocked() ms: {(time.perf_counter()-t)*1000:.3f}")
for _ in range(10):
    lim.record_failure("victim-new@x.test", "fresh-addr")
print("fresh victim key tracked:", "acct:victim-new@x.test" in lim._failures, "| blocked after 10 failures:", lim.blocked("victim-new@x.test", "fresh-addr"))

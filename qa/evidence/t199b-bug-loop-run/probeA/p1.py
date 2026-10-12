from common import *
import tempfile, json
from datetime import timedelta, datetime, UTC
print("autotester:", autotester.__file__)
BASE = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
NOW = T0 + timedelta(days=1)
def mk(name, ncrit=2, runs=("run1",)):
    root = BASE/name
    store, case = build(root, ncrit)
    for i, r in enumerate(runs):
        finished_run(store, r, 5+i, [verdict(case, r, Result.FAIL, failing=tuple(f"C{j+1}" for j in range(ncrit)), total=ncrit)], [case])
    return store, case, BugStore(root/"bugs", clock=lambda: NOW)

# 1.1 repeated
s, c, b = mk("rep")
process_run(s, b, "run1"); d1 = dump(b.dir.parent)
for n in range(4): process_run(s, b, "run1")
d5 = dump(b.dir.parent)
print("1.1 N=5 identical:", d1 == d5, "files:", len(d1)); 
for k,v in d1.items(): print("   ", k, v)
# 1.2 crash after bug 1 of 2
s0, c0, b0 = mk("clean"); process_run(s0, b0, "run1"); clean = dump(b0.dir.parent)
s, c, b = mk("crash")
orig = BugStore._write; calls = {"n":0}
def boom(self, ev):
    calls["n"] += 1
    if calls["n"] == 2: raise RuntimeError("injected crash")
    return orig(self, ev)
BugStore._write = boom
try:
    process_run(s, b, "run1")
except RuntimeError as e: print("1.2 crash raised:", e, "files after crash:", len(dump(b.dir.parent)))
BugStore._write = orig
process_run(s, b, "run1")
# names depend on case id -> compare by structure: count + fold
cr = dump(b.dir.parent); 
print("1.2 files after retry:", len(cr), "clean:", len(clean))
fj_clean = {k: json.loads(v) for k,v in foldjson(b0)[0].items()}
fj_crash = {k: json.loads(v) for k,v in foldjson(b)[0].items()}
print("1.2 counts clean:", sorted(v["count"] for v in fj_clean.values()), "crash:", sorted(v["count"] for v in fj_crash.values()))
# bytes: both projects have different case ids? case id content-hash -> same project name & same case -> same
print("1.2 bytes equal to clean:", cr == clean)
# 1.3 clock independence
s, c, b1 = mk("clk1"); b1.clock = lambda: datetime(2026,10,2,tzinfo=UTC)
s2, c2, b2 = mk("clk2"); b2.clock = lambda: datetime(2030,1,1,tzinfo=UTC)
r1 = process_run(s, b1, "run1"); r2 = process_run(s2, b2, "run1")
print("1.3 clocks differ bytes equal:", dump(b1.dir.parent) == dump(b2.dir.parent), r1.applied, r2.applied)
# clock behind
s3, c3, b3 = mk("behind"); b3.clock = lambda: T0  # run at T0+5min exactly -> now+5min == run time -> accepted boundary
r = process_run(s3, b3, "run1"); print("1.3 clock = run_time-5min exact: applied", r.applied, "refused", r.refused)
b3.clock = lambda: T0 - timedelta(minutes=1)
s4, c4, b4 = mk("behind2"); b4.clock = lambda: T0 - timedelta(minutes=1)
r = process_run(s4, b4, "run1"); print("1.3 clock 6min behind: applied", r.applied, "refused", r.refused, "files", len(dump(b4.dir.parent)))
b4.clock = lambda: NOW; r = process_run(s4, b4, "run1"); print("1.3 later: applied", r.applied, "refused", r.refused)

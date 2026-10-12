from common import *
import tempfile, subprocess, time, json, sys
from datetime import timedelta
BASE = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
PY = "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/venv/Scripts/python.exe"
NOW = T0 + timedelta(days=1)
def spawn(root, runs_per_proc):
    start = time.time() + 2.5
    ps = [subprocess.Popen([PY, "p1w.py", str(root), runs, str(start)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for runs in runs_per_proc]
    return [p.communicate(timeout=60)[0].strip() for p in ps]
def mkproj(name, spec):
    """spec: list of (run_id, minute, failing tuple)"""
    root = BASE/name
    store, case = build(root, 3)
    for rid, minute, failing in spec:
        finished_run(store, rid, minute, [verdict(case, rid, Result.FAIL, failing=failing, total=3)], [case])
    return root, store
def fold(root):
    b = BugStore(root/"bugs", clock=lambda: NOW); s = b.snapshot()
    return {k: (v.count, v.first_seen.isoformat(), v.last_seen.isoformat(), v.status.value) for k, v in sorted(s.bugs.items())}, [x.name for x in s.bad], len(s.events)
# serial reference
rr, st = mkproj("ref_same", [("run1", 5, ("C1","C2"))])
process_run(st, BugStore(rr/"bugs", clock=lambda: NOW), "run1"); ref = dump(rr)
bad = 0
for i in range(10):
    root, _ = mkproj(f"same{i}", [("run1", 5, ("C1","C2"))])
    outs = spawn(root, ["run1", "run1"])
    d = dump(root); f = fold(root)
    ok = d == ref and all(o.startswith("OK") for o in outs) and not f[1]
    if not ok: bad += 1; print("  iter", i, outs, d == ref, f)
print("1.4 same-run 2 procs x10: bad iterations =", bad, "last outs", outs, "counts", [v[0] for v in f[0].values()])
# different runs, same criterion & different criteria
spec = [("run1", 5, ("C1","C2")), ("run2", 6, ("C1","C3"))]
rr, st = mkproj("ref_diff", spec)
b = BugStore(rr/"bugs", clock=lambda: NOW)
process_run(st, b, "run1"); process_run(st, b, "run2"); fs = fold(rr); print("serial12:", fs); ds = dump(rr)
rr2, st2 = mkproj("ref_diff_rev", spec); b2 = BugStore(rr2/"bugs", clock=lambda: NOW)
process_run(st2, b2, "run2"); process_run(st2, b2, "run1"); print("serial21 == serial12 bytes:", dump(rr2) == ds, fold(rr2) == fs)
bad = 0
for i in range(10):
    root, _ = mkproj(f"diff{i}", spec)
    outs = spawn(root, ["run1", "run2"])
    d = dump(root); f = fold(root)
    if not (d == ds and f == fs and all(o.startswith("OK") for o in outs)): bad += 1; print("  iter", i, outs, f)
print("1.5 diff runs 2 procs x10: bad =", bad)

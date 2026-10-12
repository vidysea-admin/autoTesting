from common import *
import tempfile, subprocess, time, json, sys
from datetime import timedelta
if len(sys.argv) > 1 and sys.argv[1] == "W":
    from autotester.store.project_store import ProjectStore
    root, start, mode = Path(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    store = ProjectStore(PROJECT, root); b = BugStore(root/"bugs", clock=lambda: T0 + timedelta(days=1))
    while time.time() < start: pass
    t0 = time.time(); errs = []; n = 0
    runs = [f"run{i:02d}" for i in range(1, 13)]
    try:
        if mode == "R":
            for _ in range(40):
                s = b.snapshot(); n += len(s.bad)
        else:
            for r in runs: process_run(store, b, r)
    except BaseException as e: errs.append(f"{type(e).__name__}: {str(e)[:150]}")
    print(json.dumps({"mode": mode, "t0": t0, "t1": time.time(), "errs": errs, "bad_seen": n})); sys.exit(0)
BASE = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
PY = "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/venv/Scripts/python.exe"
def proj(name):
    root = BASE/name; store, case = build(root, 10)
    for i in range(1, 13):
        finished_run(store, f"run{i:02d}", i, [verdict(case, f"run{i:02d}", Result.FAIL, failing=tuple(f"C{j+1}" for j in range(10)), total=10)], [case])
    return root
def fold(root):
    s = BugStore(root/"bugs", clock=lambda: T0 + timedelta(days=1)).snapshot()
    return {k: (v.count, v.last_seen.isoformat()) for k, v in sorted(s.bugs.items())}, len(s.bad), len(s.events)
ref = proj("ref"); st = ProjectStoreRef = None
from autotester.store.project_store import ProjectStore
b = BugStore(ref/"bugs", clock=lambda: T0 + timedelta(days=1))
for i in range(1, 13): process_run(ProjectStore(PROJECT, ref), b, f"run{i:02d}")
rf = fold(ref); rd = dump(ref); print("serial:", len(rf[0]), "bugs, events", rf[2], "counts", sorted({v[0] for v in rf[0].values()}))
for it in range(3):
    root = proj(f"c{it}"); start = time.time() + 4
    ps = [subprocess.Popen([PY, "p1s.py", "W", str(root), str(start), m], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for m in ("P", "P", "R")]
    outs = [json.loads(p.communicate(timeout=120)[0].strip().splitlines()[-1]) for p in ps]
    ov = min(o["t1"] for o in outs[:2]) - max(o["t0"] for o in outs[:2])
    f = fold(root)
    print(f"iter {it}: overlap {ov:.2f}s durations {[round(o['t1']-o['t0'],2) for o in outs]} errs {[o['errs'] for o in outs]} reader_bad_seen {outs[2]['bad_seen']} fold==serial {f == rf} bytes==serial {dump(root) == rd} bad {f[1]}")

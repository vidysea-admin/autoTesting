import sys, threading, tempfile
from pathlib import Path
sys.path.insert(0, r"D:\autoTesting\.work\tmp\bi-chkB2\race\src")
import autotester
assert "bi-chkB2" in autotester.__file__, autotester.__file__
from autotester.stages import bench_marks as bm
from autotester.store.project_store import ProjectStore
# variant: 60 threads x 5 rounds, with mixed set/undo/overwrite on shared keys, barrier start
lost = errs = 0
for rnd in range(5):
    root = Path(tempfile.mkdtemp(dir=r"D:\autoTesting\.work\tmp\bi-chkB2"))
    store = ProjectStore("demo", root)
    n = 60
    keys = [f"{i:016x}" for i in range(n)]
    bar = threading.Barrier(n)
    bad, done = [], []
    def go(i):
        bar.wait()
        try:
            bm.set_mark(store, "c1", keys[i], "real" if i % 2 else "false_positive", "u"); done.append(i)
        except Exception as e:
            bad.append(repr(e)[:80])
    ts = [threading.Thread(target=go, args=(i,)) for i in range(n)]
    [t.start() for t in ts]; [t.join() for t in ts]
    stored = bm.load_marks(store, "c1").marks
    miss = [k for i, k in enumerate(keys) if k not in stored]
    wrong = [k for i, k in enumerate(keys) if k in stored and stored[k].verdict != ("real" if i % 2 else "false_positive")]
    # then simultaneous undo of the even keys while marking 20 new ones
    bar2 = threading.Barrier(40)
    def undo(i):
        bar2.wait()
        try: bm.set_mark(store, "c1", keys[i*2], None, "u")
        except Exception as e: bad.append(repr(e)[:80])
    def add(i):
        bar2.wait()
        try: bm.set_mark(store, "c1", f"{1000+i:016x}", "real", "u")
        except Exception as e: bad.append(repr(e)[:80])
    ts = [threading.Thread(target=undo, args=(i,)) for i in range(20)] + [threading.Thread(target=add, args=(i,)) for i in range(20)]
    [t.start() for t in ts]; [t.join() for t in ts]
    stored = bm.load_marks(store, "c1").marks
    exp = {keys[i] for i in range(n) if i % 2} | {f"{1000+i:016x}" for i in range(20)}
    # undone = keys[0,2,...,38]; keys[40..58 even] remain
    exp |= {keys[i] for i in range(40, n, 2)}
    print(f"round {rnd}: phase1 missing={len(miss)} wrong={len(wrong)} | phase2 stored={len(stored)} expected={len(exp)} diff={len(set(stored)^exp)} errors={bad[:2]}")
    lost += len(miss) + len(wrong) + len(set(stored) ^ exp); errs += len(bad)
print("TOTAL discrepancies:", lost, "errors:", errs)

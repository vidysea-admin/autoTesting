import sys, threading, tempfile
from pathlib import Path
sys.path.insert(0, r"D:\autoTesting\.work\tmp\bi-chkB\race\src")
import autotester
assert "bi-chkB" in autotester.__file__, autotester.__file__
from autotester.stages import bench_marks as bm
from autotester.store.project_store import ProjectStore
lost_runs = errs = 0
for rnd in range(10):
    root = Path(tempfile.mkdtemp(dir=r"D:\autoTesting\.work\tmp\bi-chkB"))
    store = ProjectStore("demo", root)
    keys = [f"{i:016x}" for i in range(20)]
    done, bad = [], []
    def go(k):
        try:
            bm.set_mark(store, "c1", k, "real", "u"); done.append(k)
        except Exception as e:
            bad.append(type(e).__name__)
    ts = [threading.Thread(target=go, args=(k,)) for k in keys]
    [t.start() for t in ts]; [t.join() for t in ts]
    stored = set(bm.load_marks(store, "c1").marks)
    lost = [k for k in done if k not in stored]
    lost_runs += bool(lost); errs += len(bad)
    print(f"round {rnd}: acknowledged={len(done)} stored={len(stored)} lost_acknowledged={len(lost)} errors={bad[:2]}")
print("rounds_with_lost_acknowledged_marks:", lost_runs, "total_errors:", errs)

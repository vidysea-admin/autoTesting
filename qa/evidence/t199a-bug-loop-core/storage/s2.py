import sys
sys.path.insert(0, "C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/ev/storage")
from common import *
import multiprocessing as mp
from pathlib import Path
from datetime import timedelta

def worker(args):
    root, idxs, start_at = args
    evs = multi_events(5, 130)[:640]
    chunk = [evs[i] for i in idxs]
    import time
    while time.time() < start_at: pass
    try:
        BugStore(Path(root)).apply_all(chunk)
        return None
    except BaseException as ex:
        return repr(ex)

def diffat_event(minutes, tag):
    sd = seed(case="case_ffffffffffff")
    return event(EventKind.FAIL, 1, seed_obj=sd, ref="same/ref", run=f"run_{tag}", minutes=minutes)

def diff_worker(args):
    root, minutes, tag, start_at = args
    import time
    while time.time() < start_at: pass
    try:
        BugStore(Path(root)).apply(diffat_event(minutes, tag)); return None
    except BaseException as ex:
        return repr(ex)

if __name__ == "__main__":
    import time
    mp.set_start_method("spawn")
    evs = multi_events(5, 130)[:640]
    exp = {k: v.model_dump_json() for k, v in fold(evs).items()}
    print("expected bugs", len(exp))
    n = 6
    bad = 0
    with mp.Pool(n) as pool:
        for rnd in range(10):
            root = fresh("s2")
            # overlap: each proc gets a disjoint slice + a shared slice 0..100
            jobs = []
            st = time.time() + 1.5
            disj = [list(range(i*100, (i+1)*100)) for i in range(6)]
            for i in range(n):
                shared = list(range(0, 100)) if rnd % 2 == 0 else disj[(i+1) % 6]
                idxs = disj[i] + shared
                jobs.append((root, idxs, st))
            res = pool.map(worker, jobs, chunksize=1)
            files = list((Path(root)/EVENTS_DIR).glob("*"))
            needed = sorted({i for j in jobs for i in j[1]})
            got = {k: v.model_dump_json() for k, v in BugStore(Path(root)).bugs().items()}
            expr = {k: v.model_dump_json() for k, v in fold([evs[i] for i in needed]).items()}
            ok = not any(res) and len(files) == len(needed) and got == expr
            bad += (not ok)
            print(rnd, "ok" if ok else "FAIL", len(files), len(needed), [r for r in res if r][:2])
    print("bad rounds", bad)
    # identical-payload same-instant same event
    bad = 0
    with mp.Pool(8) as pool:
        for rnd in range(10):
            root = fresh("s2same")
            st = time.time() + 1.0
            res = pool.map(diff_worker, [(root, 5, "x", st)]*8, chunksize=1)
            files = list((Path(root)/EVENTS_DIR).glob("*"))
            b = BugStore(Path(root)).bugs()
            ok = not any(res) and len(files) == 1 and list(b.values())[0].count == 1
            bad += (not ok)
            print("same", rnd, "ok" if ok else "FAIL", len(files), [r for r in res if r][:2])
    print("same bad", bad)
    # same (bug_key, ref, kind), different at/run_id
    outcomes = []
    with mp.Pool(2) as pool:
        for rnd in range(20):
            root = fresh("s2diff")
            st = time.time() + 1.0
            res = pool.map(diff_worker, [(root, 5, "A", st), (root, 50, "B", st)], chunksize=1)
            b = list(BugStore(Path(root)).bugs().values())[0]
            outcomes.append((b.first_seen.minute, b.evidence_run_id, tuple(r for r in res if r)))
    from collections import Counter
    print("diff-at outcomes", Counter(outcomes))

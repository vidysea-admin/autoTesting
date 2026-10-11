from common import *
import tempfile, itertools, json
from datetime import timedelta
import autotester.store.bug_store as bsm
from autotester.schema.tracked_bug import *
from bug_loop_fixture import event, CASE, seed
BASE = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
NOW = T0 + timedelta(days=1)
n = [0]
def store():
    n[0] += 1; return BugStore(BASE/f"s{n[0]}"/"bugs", clock=lambda: NOW)
def fl(minute): return event(EventKind.FAIL, 1, minutes=minute)   # same ref run1 -> same fact
def fold(b):
    return {k: (v.count, v.first_seen.isoformat(), v.last_seen.isoformat(), v.status.value, v.pass_streak) for k, v in b.bugs().items()}
res = {}
for perm in itertools.permutations([2, 4, 6]):
    b = store()
    for m in perm: b.apply(fl(m))
    res[perm] = (fold(b), len(list(b.dir.glob("*.json"))))
print("2e sequential, 3 copies at minutes 2,4,6, all 6 orders:")
for p, v in res.items(): print("  ", p, v)
print("   distinct folds:", len({json.dumps(v[0], sort_keys=True) for v in res.values()}))
# batch: all 3 in one apply_all
for perm in itertools.permutations([2,4,6]):
    b = store(); b.apply_all([fl(m) for m in perm]); 
    print("   batch", perm, fold(b), len(list(b.dir.glob('*.json'))))
    break
# interleaved with PASS (run2 at 5) -- PASS(run id) needs seed state
def ps(minute, n=2): return event(EventKind.PASS, n, minutes=minute)
res2 = {}
for perm in itertools.permutations([2, 4, 8]):
    b = store()
    b.apply(ps(6, 2)); b.apply(ps(7, 3))   # two passes at 6 and 7
    for m in perm: b.apply(fl(m))
    res2[perm] = (fold(b), len(list(b.dir.glob("*.json"))))
print("2e interleaved with PASS@6,PASS@7, FAIL copies at 2,4,8:")
for p, v in res2.items(): print("  ", p, v)
print("   distinct folds:", len({json.dumps(v[0], sort_keys=True) for v in res2.values()}))
# write-all-then-fold: write each in a fresh store separately using BOTH files present (race outcome) -> fold of set of files
b = store(); 
for m in (2,4,8): bsm.write_json(b.dir/bsm.file_name(fl(m)), fl(m))
b.apply(ps(6,2)); b.apply(ps(7,3))
print("   all three FAIL files present (race outcome):", fold(b))

# run with OLD code: write store
import sys, json
sys.path.insert(0, "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/copy/tests")
import autotester; print("autotester:", autotester.__file__)
from pathlib import Path
from bug_loop_fixture import event, seed, KEY, CASE, at
from autotester.schema.tracked_bug import *
from autotester.store.bug_store import BugStore
root = Path(sys.argv[1])
b = BugStore(root)
k2 = case_bug_key("demo", CASE, "C2")
from bug_loop_fixture import seed as sd
s2 = sd(crit="C2")
evs = [event(EventKind.FAIL, 1), event(EventKind.FAIL, 2), event(EventKind.PASS, 3), event(EventKind.PASS, 4),
       event(EventKind.FAIL, 5), event(EventKind.ASSIGN, 6, with_seed=False, assignee="bob", ref="req1"),
       event(EventKind.FAIL, 7, seed_obj=s2), event(EventKind.CASE_CHANGED, 8, key=k2, with_seed=False, ref="case/x/C2/removed")]
for e in evs: print(b.apply(e).effect.value, end=" ")
print()
print(json.dumps({k: json.loads(v.model_dump_json()) for k,v in b.bugs().items()}, sort_keys=True), file=open(sys.argv[2], "w"))
print(sorted(p.name for p in b.dir.glob("*.json")))

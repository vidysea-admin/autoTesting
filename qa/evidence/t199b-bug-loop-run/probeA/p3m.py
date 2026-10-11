import sys, json
sys.path.insert(0, "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/copy/tests")
from pathlib import Path
from datetime import timedelta
from bug_loop_fixture import event, seed, KEY, CASE, at, T0
from autotester.schema.tracked_bug import *
from autotester.store.bug_store import BugStore
root = Path(sys.argv[1]); NOW = T0 + timedelta(days=1)
b = BugStore(root, clock=lambda: NOW)
s2 = seed(crit="C2"); k2 = s2.bug_key
evs = [event(EventKind.FAIL, 1), event(EventKind.FAIL, 2), event(EventKind.PASS, 3), event(EventKind.PASS, 4),
       event(EventKind.FAIL, 5), event(EventKind.ASSIGN, 6, with_seed=False, assignee="bob", ref="req1"),
       event(EventKind.FAIL, 7, seed_obj=s2), event(EventKind.CASE_CHANGED, 8, key=k2, with_seed=False, ref="case/x/C2/removed")]
print([b.apply(e).effect.value for e in evs])
sn = b.snapshot()
new = {k: json.loads(v.model_dump_json()) for k,v in sn.bugs.items()}
old = json.loads(open(sys.argv[2]).read())
print("files:", len(list(b.dir.glob("*.json"))), "bad:", len(sn.bad), "events:", len(sn.events), "mixed fold == old fold:", new == old)
for k in new: print(k, new[k]["count"], new[k]["status"], "| old", old[k]["count"], old[k]["status"])

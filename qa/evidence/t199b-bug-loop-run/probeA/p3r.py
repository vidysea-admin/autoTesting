import sys, json
sys.path.insert(0, "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/copy/tests")
import autotester; print("autotester:", autotester.__file__)
from pathlib import Path
from autotester.store.bug_store import BugStore
root = Path(sys.argv[1])
sn = BugStore(root).snapshot()
print("bugs():", len(sn.bugs), "events:", len(sn.events), "bad:", len(sn.bad))
for x in sn.bad: print("  BAD", x.name, "|", x.why[:140])
new = {k: json.loads(v.model_dump_json()) for k,v in sn.bugs.items()}
old = json.loads(open(sys.argv[2]).read())
print("fold equals old fold:", new == old)

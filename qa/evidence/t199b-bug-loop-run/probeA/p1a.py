from common import *
import tempfile, shutil, sys
print("autotester:", autotester.__file__)
base = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
# clean single
def mk(name, ncrit=2):
    root = base/name
    store, case = build(root, ncrit)
    finished_run(store, "run1", 5, [verdict(case, "run1", Result.FAIL, failing=("C1","C2"), total=2)], [case])
    return store, case
s, c = mk("single"); bs = BugStore(s.paths.root if hasattr(s.paths,'root') else base/"single")
print("store paths:", [a for a in dir(s.paths) if not a.startswith('_')][:20])

# worker: argv root, runs(comma), start_epoch
import sys, time, json
from common import *
from datetime import timedelta
root, runs, start = Path(sys.argv[1]), sys.argv[2].split(","), float(sys.argv[3])
from autotester.store.project_store import ProjectStore
NOW = T0 + timedelta(days=1)
store = ProjectStore(PROJECT, root)
b = BugStore(root/"bugs", clock=lambda: NOW)
while time.time() < start: pass
try:
    for r in runs:
        rep = process_run(store, b, r)
    print("OK", rep.applied, rep.duplicate, len(rep.bad_files))
except BaseException as e:
    print("EXC", type(e).__name__, str(e)[:200])

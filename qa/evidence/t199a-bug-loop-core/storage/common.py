import sys, os
SRC = "C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/ck199a"
sys.path.insert(0, SRC + "/tests")
import autotester
from bug_loop_fixture import *   # noqa
from autotester.schema.tracked_bug import *   # noqa
from autotester.store.bug_store import BugStore, EVENTS_DIR
from autotester.stages.bug_loop import fold, trace
import tempfile
SCR = "C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad"
def fresh(tag):
    return tempfile.mkdtemp(prefix=tag + "_", dir=SCR + "/probe_store")
def multi_events(nbugs=5, per=130):
    evs = []
    for b in range(nbugs):
        sd = seed(case=f"case_{b:012d}", crit="C1")
        for n in range(per):
            k = [K_FAIL, K_PASS][n % 2] if False else None
        for n in range(1, per + 1):
            kind = EventKind.FAIL if n % 3 else EventKind.PASS
            if kind is EventKind.FAIL:
                evs.append(event(kind, n + 100*b, seed_obj=sd, ref=f"r{b}_{n}/c", run=f"run{b}_{n}", minutes=n))
            else:
                evs.append(event(kind, n + 100*b, key=sd.bug_key, ref=f"r{b}_{n}/c", run=f"run{b}_{n}", minutes=n))
    return evs

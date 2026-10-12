import sys, hashlib, os
sys.path.insert(0, "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/copy/tests")
from pathlib import Path
import autotester
from bug_loop_fixture import PROJECT, at, T0
from bug_run_fixture import make_store, add_case, verdict, finished_run, set_criteria
from autotester.schema.enums import Result
from autotester.store.bug_store import BugStore
from autotester.stages.bug_run import process_run

def dump(root):
    d = Path(root)/"bug_events"
    out = {}
    if d.exists():
        for p in sorted(d.iterdir()):
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else "<dir>"
    return out

def build(root, ncrit=2, runs=1):
    """project with one case with ncrit criteria; run1 fails all"""
    store = make_store(Path(root))
    crits = tuple((f"C{i+1}", f"criterion text {i+1}") for i in range(ncrit))
    case = add_case(store, "checkout", criteria=crits)
    return store, case

def foldjson(bs):
    s = bs.snapshot()
    return {k: v.model_dump_json() for k, v in sorted(s.bugs.items())}, [b.name for b in s.bad]

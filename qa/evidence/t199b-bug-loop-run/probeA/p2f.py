from common import *
from datetime import datetime, UTC
from autotester.schema.tracked_bug import *
from autotester.schema import sheet_plan
from bug_loop_fixture import seed, event
vals = {"empty": "", "a": "a", "a200": "a"*200, "a201": "a"*201, "nl": "a\nb", "nul": "a\x00b", "del": "a\x7fb", "tab": "a\tb", "u2028": "a\u2028b", "nel": "a\u0085b", "cr":"a\rb"}
def ev(k): return BugEvent(bug_key=k, kind=EventKind.PASS, ref="r", at=datetime(2026,10,1,tzinfo=UTC), actor="system:bug-loop", run_id="x")
def tb(k): return TrackedBug(bug_key=k, project="p", title="t", first_seen=datetime(2026,10,1,tzinfo=UTC), last_seen=datetime(2026,10,1,tzinfo=UTC))
def sd(k): return BugSeed(bug_key=k, project="p", title="t")   # video key regex
def sh(k): return sheet_plan.SheetRow(bug_key=k) if hasattr(sheet_plan,"SheetRow") else None
import inspect
print([n for n,o in inspect.getmembers(sheet_plan, inspect.isclass) if o.__module__==sheet_plan.__name__])
for name, f in (("BugEvent",ev),("TrackedBug",tb),("BugSeed",sd)):
    for lab, v in vals.items():
        try: f(v); ok="ACCEPTED"
        except Exception as e: ok="refused"
        print(f"{name:10} {lab:6} {ok}")

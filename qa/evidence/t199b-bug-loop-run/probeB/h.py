import sys, os
C = "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/copy"
sys.path.insert(0, C + "/tests")
from datetime import timedelta
import autotester
from bug_loop_fixture import T0, bug
from sheet_fake import FakeSheet
from autotester.core.redact import Redactor
from autotester.schema.sheet_plan import *
from autotester.schema.tracked_bug import BugStatus as S
from autotester.stages.sheet_plan import plan_sync, render_plan, PlanRefused
from autotester.stages.sheet_write import *
HEADER = ["Notes (human)", "Key", "Title", "Severity", "Status", "Assignee", "Owner's tag"]
COLS = SheetColumns(sheet_id="sheet_demo", tab="Bugs", columns={"bug_key":"Key","title":"Title","severity":"Severity","status":"Status","assignee":"Assignee"})
NOW = T0 + timedelta(days=1)
SECRET = "hunter2-sekret"
def scrub(t): return Redactor({"DEMO_PASSWORD": SECRET}).scrub(t)
def B(n, status=S.OPEN, **kw):
    return bug(status).model_copy(update={"bug_key": f"bug_{n:012d}", "title": f"Bug number {n}", "first_seen": T0+timedelta(minutes=n), **kw})
def conf(plan, who="umesh", h=None):
    return PlanConfirmation(plan_hash=h or plan.plan_hash, confirmed_by=who, confirmed_at=NOW)
def tryw(label, fn):
    try:
        r = fn(); print(f"  [{label}] OK ->", getattr(r,'plan_hash',r))
    except Exception as e:
        print(f"  [{label}] {type(e).__name__}: {str(e)[:110]!r}")
def banner(s): print("\n=== "+s)
print("autotester.__file__ =", autotester.__file__)

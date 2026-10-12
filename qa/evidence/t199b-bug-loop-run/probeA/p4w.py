import sys, json
sys.path.insert(0, "C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/copy/tests")
import autotester; print("autotester:", autotester.__file__)
from pathlib import Path
from bug_loop_fixture import event, seed, bug
from bug_run_fixture import add_case, verdict
from autotester.schema.verdict import Rubric, Criterion
from autotester.schema.tracked_bug import *
from autotester.schema.enums import Result
from autotester.schema.case import Case
from autotester.schema.enums import *
out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
rub = Rubric(id="rub_x", criteria=[Criterion(id="C1", text="Pay works"), Criterion(id="C2", text="Receipt shown", evidence_required=False)])
case = Case(project="demo", flow_id="checkout", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="t", rubric_ref="rub_x")
from autotester.schema.verdict import Failure, Verdict
v = Verdict(run_id="r1", case_id=case.id, result=Result.FAIL, criteria_met=1, criteria_total=2, failures=[Failure(criterion_id="C1", reason="x")])
for name, obj in (("rubric", rub), ("case", case), ("verdict", v), ("tracked", bug(BugStatus.FIXED)), ("event", event(EventKind.FAIL, 1)), ("seed", seed())):
    (out/f"{name}.json").write_text(obj.model_dump_json(indent=2, exclude_none=True))
print("written", sorted(p.name for p in out.iterdir()))

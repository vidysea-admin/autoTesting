from autotester.schema.case import Case
from autotester.schema.flowspec import ExpectedState
from autotester.store.project_store import ProjectStore
store = ProjectStore("pathlynks"); p = store.load_project()
c = store.get_case(p.login_case_id)
steps = [s.model_copy(update={"expected": ExpectedState(visible_text=["Zzz Absent Marker 9931"])}) if s.order == 4 else s for s in c.steps]
n = Case(project=c.project, flow_id=c.flow_id, kind=c.kind, case_class=c.case_class, title=c.title,
         rationale=c.rationale, steps=steps, severity=c.severity)
store.add_case(n); store.save_project(p.model_copy(update={"login_case_id": n.id}))
print("scratch falsify case", n.id)

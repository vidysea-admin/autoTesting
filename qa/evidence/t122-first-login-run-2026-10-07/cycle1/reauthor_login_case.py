"""Scratch: re-author step 4 of the pathlynks login case via the store code path (T-122, D-072 item 1)."""
import json
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import CaseStatus
from autotester.schema.flowspec import ExpectedState, Step
from autotester.store.project_store import ProjectStore

slug = "pathlynks"
store = ProjectStore(slug)
print("root:", store.paths.dir)
project = store.load_project()
old = store.get_case(project.login_case_id)
assert old is not None and old.id == "case_35b17ccece2d", old and old.id
new_steps = [
    s.model_copy(update={"expected": ExpectedState(visible_text=["Logout", "Dashboard"])}) if s.order == 4 else s
    for s in old.steps
]
new = Case(project=old.project, flow_id=old.flow_id, kind=old.kind, case_class=old.case_class,
           title=old.title, rationale=old.rationale, preconditions=old.preconditions,
           steps=new_steps, severity=old.severity, rubric_ref=old.rubric_ref,
           script_ref=old.script_ref, status=old.status)
print("old id", old.id, "new id", new.id)
assert new.id != old.id
assert not store.has_case(new.id)
store.add_case(new)
store.update_case(old.model_copy(update={"status": CaseStatus.RETIRED}))
store.save_project(project.model_copy(update={"login_case_id": new.id}))
print("done; login_case_id ->", store.load_project().login_case_id)

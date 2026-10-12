"""al3c-attack 2c: add a NEW member to the Action enum at runtime (simulating a future action such
as EVAL/SUBMIT/DRAG landing in enums.py without a guards.py change) and ask the guard."""
from __future__ import annotations

import os

os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "test-only-signing-key-never-a-real-secret")
import autotester  # noqa: E402
from autotester.agents import guards  # noqa: E402
from autotester.schema.case import Case  # noqa: E402
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy  # noqa: E402
from autotester.schema.flowspec import ExpectedState, Step  # noqa: E402
from autotester.schema.project import Project  # noqa: E402

print("autotester.__file__ =", autotester.__file__)
members = []
for name, val in (("EVAL", "eval"), ("SUBMIT", "submit"), ("DRAG", "drag")):
    m = str.__new__(Action, val)
    m._name_, m._value_ = name, val
    Action._member_map_[name] = m
    Action._value2member_map_[val] = m
    members.append(m)
print("Action now has", [a.value for a in Action._member_map_.values()])
for pol in (WritePolicy.READ_ONLY, WritePolicy.TEST_ACCOUNT):
    proj = Project(slug="demo", name="D", base_url="https://app.example.test",
                   allowed_domains=["app.example.test"], write_policy=pol)
    for m in members:
        st = Step.model_construct(order=1, action=m, target="Save", value=None, expected=ExpectedState(),
                                  source_ref=None, note=None, screen_id=None, narration=None,
                                  on_screen_text=None)
        case = Case.model_construct(id="c", project="demo", flow_id="f", kind=CaseKind.BEST,
                                    case_class=CaseClass.HAPPY, title="t", steps=[st])
        r = guards.write_policy_refusal(case, proj)
        print(pol.value, m.value, "->", (r[0].value, r[1]) if r else None)

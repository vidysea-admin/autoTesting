import autotester; print(autotester.__file__)
from autotester.core.paths import RepoDocs
from autotester.schema.enums import Action, CaseClass
from autotester.schema.flowspec import Flow, Step
from autotester.stages.expand import build_expand_prompt
f = Flow(id="flow_x", name="Sign in", entry_screen="scr", steps=[
    Step(order=1, action=Action.NAVIGATE, target="https://app.test/signin"),
    Step(order=2, action=Action.FILL, target="phone field", value="+91 98765 43210"),
    Step(order=3, action=Action.CLICK, target="Continue"),
    Step(order=4, action=Action.CLICK, target="Done")])
p = build_expand_prompt(f, CaseClass.HAPPY if False else list(CaseClass)[1], RepoDocs())
i = p.find("1. navigate"); print(p[i:i+260] if i>=0 else p[-600:])

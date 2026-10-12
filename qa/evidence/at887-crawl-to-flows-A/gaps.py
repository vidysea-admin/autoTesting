"""AT-890 gap 6 / gap 9 / misc probes. uv --directory <wt> run python gaps.py"""
import sys, tempfile
from pathlib import Path
import autotester
assert "check-at887-a" in autotester.__file__, autotester.__file__
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.portal_persona import FlowRunRef, PersonaScreen, PersonaTransition, PortalPersona, TaughtFlow
from autotester.schema.project import Project, SecretRef
from autotester.stages.eval_compiler import compile_evals
from autotester.stages.expand import expand, expand_flow, propose_cases
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore

SECRET = "Hunter2-Zebra-4411"
EMAIL = "ada.lovelace@example.org"

def flow(value):
    return Flow(id="flow_x", name="Sign in", entry_screen="scr_signin", steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://app.test/signin", screen_id="scr_signin"),
        Step(order=2, action=Action.FILL, target="email field", value=value, screen_id="scr_signin"),
        Step(order=3, action=Action.CLICK, target="Login button", screen_id="scr_signin")])

def setup(tmp, value, *, project=True, env="ST_PASS=%s\nOTHER=zzz-other-9082\n" % SECRET, secrets=("ST_PASS",)):
    fl = flow(value)
    store = ProjectStore("demo", tmp)
    if project:
        store.save_project(Project(slug="demo", name="Demo", base_url="https://app.test",
            allowed_domains=["app.test"], secrets=[SecretRef(key=k, domains=["app.test"]) for k in secrets]))
    (tmp / ".env").write_text(env, encoding="utf-8")
    spec = approve(FlowSpec(project="demo", flows=[fl]), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec); store.stage_case_proposals(rows)
    for r in rows: store.review_case_proposal(r.id, "umesh", approved=True)
    persona = PortalPersona(project="demo",
        screens=[PersonaScreen(id="scr_signin", name="Sign in", controls=["email field"])],
        transitions=[],
        taught_flows=[TaughtFlow(id="flow_x", name="Sign in", entry_screen="scr_signin",
            run_ref=FlowRunRef(project="demo", flow_id="flow_x", entry_screen="scr_signin"))])
    return fl, store, spec, persona

def spy(): return MockProvider(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 60})

def show(label, fn, tmp_value, needles, **kw):
    for entry in ("expand", "expand_flow", "compile_evals"):
        with tempfile.TemporaryDirectory() as d:
            fl, store, spec, persona = setup(Path(d), tmp_value, **kw)
            p = spy()
            try:
                if entry == "expand": expand(store.load_flowspec(), p, store=store)
                elif entry == "expand_flow": expand_flow(fl, "demo", p, store=store)
                else: compile_evals(spec, persona, [], p, store=store)
                st = f"sent({len(p.prompts)})"
            except Exception as e: st = f"refused:{type(e).__name__}:{e}"
            leaked = [n for n in needles if any(n in pr for _, pr in p.prompts)]
            print(f"{label:38} {entry:13} {st[:60]:60} LEAKED={leaked}")

print("== GAP 6: no project.json (store has flowspec+proposals, load_project() is None)")
show("noproj declared secret in value", None, SECRET, [SECRET], project=False)
show("noproj email in value", None, EMAIL, [EMAIL], project=False)
show("noproj undeclared-looking env value", None, "zzz-other-9082", ["zzz-other-9082"], project=False)
print("== project exists but declares NO secrets, .env has the value (shadow path)")
show("noDeclared, env value in value", None, SECRET, [SECRET], secrets=())
print("== project exists, .env file missing")
show("no .env file, secret-shaped value", None, SECRET, [SECRET], env="")
print("== project declares key but .env lacks it (strict=False)")
show("declared-but-missing value", None, SECRET, [SECRET], env="X=1\n")
print("== placeholder survives?")
with tempfile.TemporaryDirectory() as d:
    fl, store, spec, persona = setup(Path(d), "{{SECRET:ST_PASS}}"); p = spy()
    expand_flow(fl, "demo", p, store=store)
    print("placeholder in every prompt:", all("{{SECRET:ST_PASS}}" in x for _, x in p.prompts), "n=", len(p.prompts),
          "| secret raw anywhere:", any(SECRET in x for _, x in p.prompts))
print("== short declared secret that is a substring of template/placeholder text")
for sv in ("word", "SECRET", "ST_PASS", "step"):
    with tempfile.TemporaryDirectory() as d:
        fl, store, spec, persona = setup(Path(d), "{{SECRET:ST_PASS}}", env=f"ST_PASS={sv}\n"); p = spy()
        try:
            expand_flow(fl, "demo", p, store=store); st = "sent"
        except Exception as e: st = f"refused:{type(e).__name__}"
        ph = all("{{SECRET:ST_PASS}}" in x for _, x in p.prompts) if p.prompts else None
        print(f"secret value {sv!r:10}: {st} placeholder-intact={ph}")
print("== gap 9: compile_evals provider-spy, store-backed")
with tempfile.TemporaryDirectory() as d:
    fl, store, spec, persona = setup(Path(d), f"{EMAIL} {SECRET}"); p = spy()
    r = compile_evals(spec, persona, [], p, store=store)
    print("prompts:", len(p.prompts), "untraced:", r.untraced_flows,
          "raw secret/email in any:", any(SECRET in x or EMAIL in x for _, x in p.prompts))
    print("sample value line:", [l for l in p.prompts[0][1].splitlines() if "email field" in l])
with tempfile.TemporaryDirectory() as d:
    fl, store, spec, persona = setup(Path(d), SECRET, project=False); p = spy()
    r = compile_evals(spec, persona, [], p, store=store)
    print("compile_evals no-project: raw secret reached provider:", any(SECRET in x for _, x in p.prompts))

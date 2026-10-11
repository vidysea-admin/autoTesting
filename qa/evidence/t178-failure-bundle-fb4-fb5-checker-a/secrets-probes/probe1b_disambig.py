"""Disambiguate inputs: --by, flow id, flow name separately; end-to-end expand; baseline vs new; priority-row message."""
import html, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import S, mk_root, raw_in
import autotester
NEW = "base" in autotester.__file__ and "base0" not in autotester.__file__
print("autotester.__file__ =", autotester.__file__, "| NEW" if NEW else "| BASELINE")
def forms(text):
    f = {"raw": S, "html": html.escape(S), "py-repr": repr(S)[1:-1], "json-esc": json.dumps(S, ensure_ascii=False)[1:-1]}
    return [k for k, v in f.items() if v in text]
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from typer.testing import CliRunner
from autotester.cli import app as cli

def seed(root, name, fid):
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
    st.save_flowspec(FlowSpec(project="demo", review=Review(status=ReviewStatus.APPROVED, by="h", at="t"),
        flows=[Flow(id=fid, name=name, entry_screen="scr", steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/x"),
                                                                Step(order=2, action=Action.CLICK, target="Go")])]))
    return st
ans = ExpandedSteps(steps=[Step(order=1, action=Action.CLICK, target="Go")], rationale="r")
import autotester.cli as climod
prov = MockProvider(responses={"agent": [ans] * 80})
climod.providers.get = lambda _id, **_kw: prov
r = CliRunner()

# A: flow NAME = secret, end-to-end
root = mk_root("p1b_name"); st = seed(root, f"Login {S}", "flow-1")
if NEW:
    r.invoke(cli, ["expand", "demo", "--proposals"])
    for pr in st.list_case_proposals():
        if pr.case_class.value == "happy":
            o = r.invoke(cli, ["expand", "demo", "--approve", pr.id, "--by", "alice"])
    o = r.invoke(cli, ["expand", "demo"])
    print("[A] new e2e generate: exit", o.exit_code, "| out:", o.output.strip()[:90])
    print("[A] case_proposals.jsonl:", raw_in(st.paths.case_proposals))
else:
    o = r.invoke(cli, ["expand", "demo"]); print("[A] baseline e2e generate: exit", o.exit_code, o.output.strip()[:90])
print("[A] cases.jsonl:", raw_in(st.paths.cases), "| title raw in json.loads:", any(S in json.loads(l)["title"] for l in st.paths.cases.read_text(encoding="utf-8").splitlines() if l.strip()))

if NEW:
    # B: only --by is the secret (flow name clean)
    root = mk_root("p1b_by"); st = seed(root, "Login flow", "flow-1")
    r.invoke(cli, ["expand", "demo", "--proposals"])
    hp = next(p for p in st.list_case_proposals() if p.case_class.value == "happy")
    o = r.invoke(cli, ["expand", "demo", "--approve", hp.id, "--by", S])
    print("[B] --by=<secret> (clean flow name): exit", o.exit_code, "| stdout forms:", forms(o.output), "| case_proposals.jsonl:", raw_in(st.paths.case_proposals))
    print("    reviewed_by on disk == secret:", any(json.loads(l).get("reviewed_by") == S for l in st.paths.case_proposals.read_text(encoding="utf-8").splitlines()))
    # approved --by propagates into generated cases?
    o = r.invoke(cli, ["expand", "demo"]); print("    then generate: exit", o.exit_code, "| cases.jsonl:", raw_in(st.paths.cases))
    o = r.invoke(cli, ["expand", "demo", "--proposals", "--by", S]); print("    --proposals --by secret echoes:", forms(o.output))
    # C: only flow id is the secret
    root = mk_root("p1b_id"); st = seed(root, "Login flow", "flow-" + S)
    r.invoke(cli, ["expand", "demo", "--proposals"])
    print("[C] flow.id=secret: case_proposals.jsonl:", raw_in(st.paths.case_proposals))
    o = r.invoke(cli, ["expand", "demo", "--proposals"]); print("    CLI echoes:", forms(o.output))
else:
    root = mk_root("p1b_idb"); st = seed(root, "Login flow", "flow-" + S)
    o = r.invoke(cli, ["expand", "demo"]); print("[C] baseline flow.id=secret: generate exit", o.exit_code, "| cases.jsonl:", raw_in(st.paths.cases))

# D: Case.priority invalid in cases.jsonl (baseline: no priority field -> extra forbidden)
root = mk_root("p1b_prio"); st = seed(root, "Login flow", "flow-1")
st.paths.cases.write_text(json.dumps({"project": "demo", "flow_id": "f", "kind": "best", "case_class": "happy",
                                      "title": "t", "steps": [], "priority": S}) + "\n", encoding="utf-8")
try:
    st.list_cases(); print("[D] ACCEPTED")
except Exception as exc:
    print("[D] invalid priority row ->", type(exc).__name__, "| message forms:", forms(str(exc)))
    print("    ", str(exc).split("validation error for Case")[-1].replace("\n", " | ")[:300])

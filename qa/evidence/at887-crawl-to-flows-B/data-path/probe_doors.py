"""B coordinator probe: three doors from a crawl to case expansion without human approval."""
import sys, tempfile
from pathlib import Path
import autotester
print("autotester.__file__", autotester.__file__)
from fastapi.testclient import TestClient
from autotester.cli_crawl import _merge_into_flowspec
from autotester.core.paths import RepoDocs
from autotester.schema.case import ExpandedSteps
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.expand import expand, expand_flow, propose_cases
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_runners import make_discover_runner, make_model_runner
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore
from autotester.store.filestore import read_json
from autotester.ui.app import app

class Spy:
    id = "spy"
    def __init__(self): self.calls = []
    def act(self, prompt, model, **kw):
        self.calls.append(prompt); return ExpandedSteps(steps=[], rationale="n/a")

P = Project(slug="demo", name="Demo", base_url="https://app.test", allowed_domains=["app.test"])
CR = "crawl_door"

def seed(root):
    store = ProjectStore("demo", root); store.save_project(P)
    store.save_crawl(Crawl(project="demo", id=CR, login_case_id="case_login"))
    home = ScreenNode(crawl_id=CR, project="demo", url_template="app.test/home", url_example="https://app.test/home", signature="h", name="Home")
    e = ScreenEdge(crawl_id=CR, from_node=home.id, action=Action.NAVIGATE, target='role=link[name="Settings"]', outcome="navigated")
    s = ScreenNode(crawl_id=CR, project="demo", url_template="app.test/settings", url_example="https://app.test/settings", signature="s", name="Settings", discovered_by=e.id)
    store.add_node(home); store.add_node(s); store.add_edge(e)
    # prior APPROVED spec with one human flow and APPROVED case proposals
    old = Flow(id="flow_old", name="Old human flow", entry_screen="x", steps=[Step(order=1, action=Action.NAVIGATE, target="https://app.test/old")])
    spec = approve(FlowSpec(project="demo", flows=[old]), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec); store.stage_case_proposals(rows)
    for r in rows: store.review_case_proposal(r.id, "umesh", approved=True)
    return store, home, s

def attempt(label, store, stale_spec):
    spy = Spy(); out = {}
    cur = store.load_flowspec()
    out["status"] = cur.review.status.value; out["by"] = cur.review.by
    out["flows"] = [f.name for f in cur.flows]
    for nm, fn in (("expand(current)", lambda: expand(cur, spy, store=store)),
                   ("expand(stale approved spec)", lambda: expand(stale_spec, spy, store=store)),
                   ("expand_flow(crawl flow)", lambda: expand_flow([f for f in cur.flows if f.id != "flow_old"][0], "demo", spy, store=store)),
                   ("expand_flow(old flow)", lambda: expand_flow([f for f in cur.flows if f.id == "flow_old"][0], "demo", spy, store=store))):
        try: fn(); out[nm] = "NO ERROR"
        except Exception as ex: out[nm] = f"{type(ex).__name__}: {str(ex)[:110]}"
    print(f"== {label}: review={out['status']} by={out['by']} flows={out['flows']}")
    for k in list(out)[3:]: print("   ", k, "->", out[k])
    print("    provider.act calls:", len(spy.calls))

base = sys.argv[1]
# DOOR 1 CLI
with tempfile.TemporaryDirectory(dir=base) as td:
    store, _, _ = seed(Path(td)); stale = store.load_flowspec()
    _merge_into_flowspec(store, "demo", CR)
    attempt("CLI door", store, stale)
# DOOR 2 UI button
with tempfile.TemporaryDirectory(dir=base) as td:
    import os; os.environ["AUTOTESTER_ROOT"] = td
    store, _, _ = seed(Path(td)); stale = store.load_flowspec()
    r = TestClient(app).post(f"/projects/demo/crawls/{CR}/merge", follow_redirects=False)
    print("UI status", r.status_code)
    attempt("UI door", store, stale)
# DOOR 3 orchestrated DISCOVER -> MODEL
with tempfile.TemporaryDirectory(dir=base) as td:
    store, home, s = seed(Path(td)); stale = store.load_flowspec()
    crawl = store.load_crawl(CR); nodes = store.list_nodes(CR)
    ctx = StageContext(store=store, run_id="run1")
    ref = make_discover_runner(P, lambda: (crawl, nodes))(ctx, None)
    prop = read_json(Path(ref), FlowSpec)
    print("DISCOVER proposal review", prop.review.status.value, prop.review.by, "flows", len(prop.flows), "| saved spec still", store.load_flowspec().review.status.value)
    make_model_runner(source_id=CR)(ctx, ref)
    attempt("ORCHESTRATED door (DISCOVER+MODEL)", store, stale)
    # human approves the spec but NOT the case proposals for crawl flows
    cur = store.load_flowspec(); store.save_flowspec(approve(cur, by="umesh"))
    spy = Spy(); cur = store.load_flowspec()
    try: expand(cur, spy, store=store); print("after spec-only approval: expand NO ERROR calls", len(spy.calls))
    except Exception as ex: print("after spec-only approval expand ->", type(ex).__name__, str(ex)[:120], "calls", len(spy.calls))
    try: print("propose_cases for approved:", len(propose_cases(cur)))
    except Exception as ex: print(ex)
    # approve case proposals for one crawl flow only via human API, then expand all
    rows = propose_cases(cur); store.stage_case_proposals(rows)
    crawl_rows = [r for r in rows if r.flow_id != "flow_old"]
    for r in crawl_rows[:2]: store.review_case_proposal(r.id, "umesh", approved=True)
    spy = Spy(); cur = store.load_flowspec()
    try: res = expand(cur, spy, store=store); print("with 2 human-approved proposals: cases", len(res), "calls", len(spy.calls))
    except Exception as ex: print("expand(partial approvals) ->", type(ex).__name__, str(ex)[:140], "calls", len(spy.calls))

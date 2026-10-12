import os
import sys
import tempfile
from pathlib import Path

import autotester

print("autotester:", autotester.__file__)
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review, Screen
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_merge import merge_screens_and_flows
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_runners import make_discover_runner, make_model_runner
from autotester.stages.screen_identity import dangling_references
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore


def node(cid, path, sig, name, disc=None):
    return ScreenNode(crawl_id=cid, project="demo", url_template="demo.test" + path,
                      url_example="https://demo.test" + path, signature=sig, name=name,
                      discovered_by=disc)


def edge(cid, frm, tgt):
    return ScreenEdge(crawl_id=cid, from_node=frm, action=Action.NAVIGATE, target=tgt,
                      outcome="navigated")


def human(*pairs, status=ReviewStatus.APPROVED):
    return FlowSpec(project="demo", version=4, review=Review(status=status, by="umesh"),
                    screens=[Screen(id=i, name=n, url_pattern=p) for i, n, p in pairs])


def show(label, spec):
    print("==", label, "dangling=", dangling_references(spec), "version", spec.version,
          "review", spec.review.status.value, spec.review.by)
    for f in spec.flows:
        print("  flow", f.id, "entry", f.entry_screen, "exit", f.exit_screen, "steps",
              [(s.order, s.action.value, s.screen_id, s.target[:28]) for s in f.steps])


fails = []


def check(c, msg):
    print(("OK   " if c else "FAIL ") + msg)
    if not c:
        fails.append(msg)


C = "c1"
home = node(C, "/home", "s_h", "Home")
e1 = edge(C, home.id, 'link[name="Items"]')
itA = node(C, "/items", "s_a", "Items", e1.id)
e2 = edge(C, itA.id, 'button[name="Next tab"]')
itB = node(C, "/items", "s_b", "Items", e2.id)
nodes = [home, itA, itB]
edges = [e1, e2]
H = human(("scr_home", "Home", "/home"), ("scr_items", "Items", "/items"))
fresh = merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=C)
known = merge_screens_and_flows(H, nodes, edges, "demo", crawl_id=C)
show("A fresh", fresh)
show("A known (two nodes -> same screen)", known)
check(dangling_references(known) == [], "A: no dangling when two crawl nodes alias to the same existing screen")
check([f.id for f in fresh.flows] == [f.id for f in known.flows], "A: flow id unchanged by the rewrite")
kf = known.flows[0]
check(len(kf.steps) == len(fresh.flows[0].steps) == 3, "A: steps not collapsed or duplicated (3 steps)")
check([s.order for s in kf.steps] == [1, 2, 3]
      and [s.target for s in kf.steps] == [s.target for s in fresh.flows[0].steps],
      "A: step orders and targets identical to fresh")
print("A: entry/exit:", kf.entry_screen, kf.exit_screen)
again = merge_screens_and_flows(known, nodes, edges, "demo", crawl_id=C)
check(again == known, "A: re-merge is a no-op")
FlowSpec.model_validate(known.model_dump(mode="json"))
print("A: model_validate roundtrip ok")

solo = node("c2", "/home", "s_h", "Home")
Hs = human(("scr_home", "Home", "/home"))
b = merge_screens_and_flows(Hs, [solo], [], "demo", crawl_id="c2")
show("B entry==exit rediscovered", b)
check(dangling_references(b) == [] and bool(b.flows) and b.flows[0].entry_screen == "scr_home"
      and b.flows[0].exit_screen == "scr_home" and b.flows[0].steps[0].screen_id == "scr_home",
      "B: single-node flow cites existing screen as entry, exit and step")
check(b.version == 5 and b.review.status is ReviewStatus.DRAFT and b.review.by is None,
      "B: version bumped exactly once, DRAFT, by None")

H2 = human(("scr_home", "Home", "/home"))
m = merge_screens_and_flows(H2, nodes, edges, "demo", crawl_id=C)
show("C mixed (home rediscovered; items new)", m)
check(dangling_references(m) == [], "C: mixed no dangling")
h9 = node("c9", "/home", "s_h", "Home")
x1 = edge("c9", h9.id, 'link[name="Items"]')
a9 = node("c9", "/items", "s_a", "Items", x1.id)
x2 = edge("c9", a9.id, 'button[name="Next tab"]')
b9 = node("c9", "/items", "s_b", "Items", x2.id)
m2 = merge_screens_and_flows(m, [h9, a9, b9], [x1, x2], "demo", crawl_id="c9")
print("C: same node ids on re-crawl?", [n.id for n in nodes] == [h9.id, a9.id, b9.id],
      "flows", len(m.flows), "->", len(m2.flows), "version", m.version, "->", m2.version)
check(len(m2.flows) == len(m.flows) and m2.version == m.version,
      "C: re-crawl with a new crawl id adds no duplicate flow and no bump")
check(dangling_references(m2) == [], "C: re-crawl no dangling")

H3 = human(("scr_x", "Other", "/other"))
d = merge_screens_and_flows(H3, nodes, edges, "demo", crawl_id=C)
check([f.model_dump() for f in d.flows] == [f.model_dump() for f in fresh.flows],
      "D: flows with no rediscovery are identical to the fresh-spec flows")

H4 = human(("scr_items", "Item list", "/items"))
e = merge_screens_and_flows(H4, nodes, edges, "demo", crawl_id=C)
show("E same pattern, different name", e)
check(dangling_references(e) == [], "E: conflict path no dangling")

H5 = human(("node_zzz", "Items", "/items"))
f = merge_screens_and_flows(H5, nodes, edges, "demo", crawl_id=C)
check(dangling_references(f) == [], "F: structural-id clash no dangling")

with tempfile.TemporaryDirectory() as td:
    store = ProjectStore("demo", Path(td))
    proj = Project(slug="demo", name="Demo", base_url="https://demo.test",
                   allowed_domains=["demo.test"])
    store.save_project(proj)
    cr = Crawl(project="demo", id=C, login_case_id="case_login")
    store.save_crawl(cr)
    for n in nodes:
        store.add_node(n)
    for ed in edges:
        store.add_edge(ed)
    store.save_flowspec(H)
    ctx = StageContext(store=store, run_id="r1")
    ref = make_discover_runner(proj, lambda: (cr, nodes))(ctx, None)
    prop = read_json(Path(ref), FlowSpec)
    show("G proposal", prop)
    make_model_runner()(ctx, ref)
    folded = store.load_flowspec()
    show("G folded", folded)
    check(dangling_references(folded) == [], "G: orchestrated door fold has no dangling")
    print("G: screens in folded:", [(s.id, s.name, s.url_pattern) for s in folded.screens])
    ctx2 = StageContext(store=store, run_id="r2")
    ref2 = make_discover_runner(proj, lambda: (cr, nodes))(ctx2, None)
    make_model_runner()(ctx2, ref2)
    check(store.load_flowspec() == folded, "G: second orchestrated run is a no-op")
    store.save_flowspec(H)
    from autotester.cli_crawl import _merge_into_flowspec
    _merge_into_flowspec(store, "demo", C)
    cli = store.load_flowspec()
    show("CLI door", cli)
    check(dangling_references(cli) == [], "CLI door no dangling")
    store.save_flowspec(H)
    os.environ["AUTOTESTER_ROOT"] = td
    from fastapi.testclient import TestClient

    from autotester.ui.app import app
    r = TestClient(app).post(f"/projects/demo/crawls/{C}/merge", follow_redirects=False)
    ui = ProjectStore("demo", Path(td)).load_flowspec()
    show("UI door status %s" % r.status_code, ui)
    check(r.status_code == 303 and dangling_references(ui) == [], "UI door no dangling")
    check([x.model_dump() for x in ui.flows] == [x.model_dump() for x in cli.flows],
          "CLI and UI doors produce identical flows")
print("FAILS:", fails)
sys.exit(1 if fails else 0)

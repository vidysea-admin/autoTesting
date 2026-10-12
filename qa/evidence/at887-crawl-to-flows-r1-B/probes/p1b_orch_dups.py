"""Probe 1 (checker B, AT-887 r1): the data path through the three merge doors.
Synthetic crawl graphs only, tmp roots, no browser, no provider. Run with python -I."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AUTOTESTER_ALLOWED_HOSTS", "testserver")
os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "probe-only-key")
from fastapi.testclient import TestClient

from autotester.cli_crawl import _merge_into_flowspec
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Screen, Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_merge import screen_from
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_runners import make_discover_runner, make_model_runner
from autotester.stages.screen_identity import dangling_references
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

PROJECT = Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"])


def build(crawl_id, topo):
    """topo: list of (key, name, path, sig, parent_key|None, action, target)."""
    nodes, edges, by = {}, [], {}
    for key, name, path, sig, parent, action, target in topo:
        disc = None
        if parent:
            e = ScreenEdge(crawl_id=crawl_id, from_node=nodes[parent].id, action=action,
                           target=target, name=target, outcome="navigated")
            edges.append(e)
            disc = e.id
        n = ScreenNode(crawl_id=crawl_id, project="demo", url_template=f"demo.test{path}",
                       url_example=f"https://demo.test{path}", signature=sig, name=name,
                       title=name, discovered_by=disc)
        nodes[key] = n
    return nodes, edges


L = 'role=link[name="%s"] >> nth=0'
G1 = [("home", "Home", "/home", "s_home", None, None, None),
      ("courses", "Courses", "/courses", "s_courses", "home", Action.NAVIGATE, L % "Courses"),
      ("detail", "Course detail", "/courses/12", "s_detail", "courses", Action.CLICK, '[aria-label="Open course"]'),
      ("profile", "Profile", "/profile", "s_profile", "home", Action.NAVIGATE, L % "Profile")]
G2 = [("home", "Home", "/home", "s_home", None, None, None),
      ("dasha", "Dashboard", "/dash", "s_dash_a", "home", Action.NAVIGATE, L % "Dashboard"),
      ("dashb", "Dashboard", "/dash", "s_dash_b", "dasha", Action.CLICK, "text=Tab 2"),
      ("reports", "Reports", "/reports", "s_rep", "home", Action.NAVIGATE, L % "Reports")]
G1_PLUS = G1 + [("settings", "Settings", "/settings", "s_set", "home", Action.NAVIGATE, L % "Settings")]


def human_screen(node, sid):
    return screen_from(node).model_copy(update={"id": sid})


def seed(kind, nodes):
    human_flow = Flow(id="flow_human", name="Human flow", entry_screen="scr_other", exit_screen="scr_other",
                      steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/other",
                                  screen_id="scr_other")])
    screens = [Screen(id="scr_other", name="Other", url_pattern="/other")]
    if kind == "mid":
        screens.append(human_screen(nodes["courses"], "scr_courses"))
    elif kind == "entry_exit":
        screens += [human_screen(nodes["home"], "scr_home"), human_screen(nodes["detail"], "scr_detail")]
    elif kind == "same":
        screens.append(human_screen(nodes["dasha"], "scr_dash"))
    elif kind == "allscreens":  # every crawl node already a screen by node id (flows-only merge)
        screens += [screen_from(n) for n in nodes.values()]
    return FlowSpec(project="demo", version=4, screens=screens, flows=[human_flow],
                    review=Review(status=ReviewStatus.APPROVED, by="umesh", at="2026-10-01"))


def well_formed(spec):
    problems = []
    ids = [f.id for f in spec.flows]
    if len(ids) != len(set(ids)):
        problems.append("duplicate flow ids")
    sids = [s.id for s in spec.screens]
    if len(sids) != len(set(sids)):
        problems.append("duplicate screen ids")
    for f in spec.flows:
        orders = [s.order for s in f.steps]
        if orders != list(range(1, len(orders) + 1)):
            problems.append(f"{f.id} orders {orders}")
        if f.steps and f.entry_screen != f.steps[0].screen_id and f.id != "flow_human":
            problems.append(f"{f.id} entry != step1")
        if f.id != "flow_human" and f.exit_screen not in set(sids):
            problems.append(f"{f.id} exit {f.exit_screen} not a screen")
        if f.id != "flow_human" and f.steps and f.steps[0].action.value != "navigate":
            problems.append(f"{f.id} step1 not navigate")
    return problems


def preserved(before, after):
    return (all(s in after.screens for s in before.screens)
            and all(f in after.flows for f in before.flows))


def setup(root, crawl_id, nodes, edges, spec):
    store = ProjectStore("demo", root)
    store.save_project(PROJECT)
    crawl = Crawl(project="demo", id=crawl_id, login_case_id="case_login")
    store.save_crawl(crawl)
    for n in nodes.values():
        store.add_node(n)
    for e in edges:
        store.add_edge(e)
    if spec is not None:
        store.save_flowspec(spec)
    return store, crawl


def door(name, root, store, crawl, nodes):
    cid = crawl.id
    if name == "cli":
        _merge_into_flowspec(store, "demo", cid)
    elif name == "ui":
        os.environ["AUTOTESTER_ROOT"] = str(root)
        r = TestClient(app).post(f"/projects/demo/crawls/{cid}/merge", follow_redirects=False)
        assert r.status_code == 303, r.status_code
    elif name == "orch":
        ctx = StageContext(store=store, run_id="run_" + cid)
        ref = make_discover_runner(PROJECT, lambda: (crawl, list(nodes.values())))(ctx, None)
        make_model_runner()(ctx, ref)
    return ProjectStore("demo", root).load_flowspec()



tmp = Path(tempfile.mkdtemp(prefix="r1b_p1b_"))
for d in ("cli","orch"):
    root = tmp / d
    nodes, edges = build("crawl_a", G1)
    sp = seed("entry_exit", nodes)
    store, crawl = setup(root, "crawl_a", nodes, edges, sp)
    after = door(d, root, store, crawl, nodes)
    print(d, "screens:", [(x.id, x.name) for x in after.screens], "conflicts:", len(after.conflicts))
    print(d, "flow refs:", [(f.entry_screen, f.exit_screen) for f in after.flows if f.id != "flow_human"])

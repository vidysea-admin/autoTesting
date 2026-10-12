"""Three doors end to end + P6 expand gate, each in its own temp project dir."""
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
os.environ.setdefault("AUTOTESTER_ALLOWED_HOSTS", "testserver")

import autotester
from autotester.cli_crawl import _merge_into_flowspec
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, EdgeOutcome, ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review, Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages import review as review_stage
from autotester.stages.expand import expand, stage_and_review
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_runners import make_discover_runner, make_model_runner
from autotester.stages.review import FlowSpecNotReviewed
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

os.environ.setdefault("AUTOTESTER_ALLOWED_HOSTS", "testserver")
print("module:", autotester.__file__)
R = []


def check(name, ok, detail=""):
    R.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name, detail)


PROJECT = Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"])
CID = "crawl_h3"


def seed(root, with_flow_edges=True):
    store = ProjectStore("demo", root)
    store.save_project(PROJECT)
    store.save_crawl(Crawl(project="demo", id=CID, login_case_id="case_login"))
    home = ScreenNode(crawl_id=CID, project="demo", url_template="demo.test/home", url_example="https://demo.test/home", signature="h", name="Home")
    e1 = ScreenEdge(crawl_id=CID, from_node=home.id, action=Action.NAVIGATE, target='role=link[name="Settings"]', outcome=EdgeOutcome.NAVIGATED)
    st = ScreenNode(crawl_id=CID, project="demo", url_template="demo.test/settings", url_example="https://demo.test/settings", signature="s", name="Settings", discovered_by=e1.id)
    e2 = ScreenEdge(crawl_id=CID, from_node=st.id, action=Action.NAVIGATE, target='role=link[name="mail bob@corp.com"]', outcome=EdgeOutcome.NAVIGATED)
    pr = ScreenNode(crawl_id=CID, project="demo", url_template="demo.test/profile", url_example="https://demo.test/profile", signature="p", name="Profile", discovered_by=e2.id)
    ef = ScreenEdge(crawl_id=CID, from_node=home.id, action=Action.FILL, target="q", outcome=EdgeOutcome.NAVIGATED)
    fx = ScreenNode(crawl_id=CID, project="demo", url_template="demo.test/typed", url_example="https://demo.test/typed", signature="t", name="Typed", discovered_by=ef.id)
    for n in (home, st, pr, fx):
        store.add_node(n)
    for e in (e1, e2, ef):
        store.add_edge(e)
    return store, [home, st, pr, fx]


APPROVED = Review(status=ReviewStatus.APPROVED, by="umesh", at="2026-10-10T00:00:00Z", note="ok")

# ---- door (a) CLI
with tempfile.TemporaryDirectory() as td:
    store, nodes = seed(Path(td))
    store.save_flowspec(FlowSpec(project="demo", version=5, review=APPROVED))
    _merge_into_flowspec(store, "demo", CID)
    spec = store.load_flowspec()
    check("(a) CLI: 1 flow (deepest leaf Profile) + Typed skipped", len(spec.flows) == 1 and spec.flows[0].exit_screen == nodes[2].id, f"flows={[f.name for f in spec.flows]}")
    check("(a) CLI: v6 DRAFT by None", spec.version == 6 and spec.review.status is ReviewStatus.DRAFT and spec.review.by is None, repr(spec.review))
    # Note: Home and Settings are parents? Home has chain to Typed invalid -> Home is parent via Settings chain; fine
    b1 = store.paths.flowspec.read_bytes()
    _merge_into_flowspec(store, "demo", CID)
    check("(a) CLI re-merge byte-identical", store.paths.flowspec.read_bytes() == b1)
    check("(a) CLI flow carries requires_auth + login precondition", spec.flows[0].requires_auth and "case_login" in spec.flows[0].preconditions[0])

# ---- door (b) UI
with tempfile.TemporaryDirectory() as td:
    os.environ["AUTOTESTER_ROOT"] = td
    store, nodes = seed(Path(td))
    store.save_flowspec(FlowSpec(project="demo", version=5, review=APPROVED))
    c = TestClient(app)
    r = c.post(f"/projects/demo/crawls/{CID}/merge", follow_redirects=False)
    spec = ProjectStore("demo", Path(td)).load_flowspec()
    check("(b) UI POST merge 303", r.status_code == 303, str(r.status_code))
    check("(b) UI: 1 flow, v6, DRAFT, by None", len(spec.flows) == 1 and spec.version == 6 and spec.review.status is ReviewStatus.DRAFT and spec.review.by is None)
    b1 = store.paths.flowspec.read_bytes()
    r = c.post(f"/projects/demo/crawls/{CID}/merge", follow_redirects=False)
    check("(b) UI re-merge byte-identical", store.paths.flowspec.read_bytes() == b1 and r.status_code == 303)
    # approve then re-merge: stays approved
    store.save_flowspec(review_stage.approve(store.load_flowspec(), "umesh"))
    b2 = store.paths.flowspec.read_bytes()
    c.post(f"/projects/demo/crawls/{CID}/merge", follow_redirects=False)
    spec = store.load_flowspec()
    check("(b) UI re-merge of approved spec stays APPROVED & bytes unchanged", spec.review.status is ReviewStatus.APPROVED and store.paths.flowspec.read_bytes() == b2)
    # UI with NO prior flowspec
os.environ.pop("AUTOTESTER_ROOT", None)

# ---- door (c) DISCOVER + MODEL
with tempfile.TemporaryDirectory() as td:
    store, nodes = seed(Path(td))
    crawl = store.load_crawl(CID)
    runner = make_discover_runner(PROJECT, lambda: (crawl, nodes))
    ctx = StageContext(store=store, run_id="run_h3")
    ref = runner(ctx, None)
    prop = read_json(Path(ref), FlowSpec)
    check("(c) DISCOVER: proposal has the flow, DRAFT, reviewed truth untouched", len(prop.flows) == 1 and prop.review.status is ReviewStatus.DRAFT and store.load_flowspec() is None, f"flows={[f.name for f in prop.flows]}")
    # follow into the MODEL stage over an APPROVED reviewed spec
    store.save_flowspec(FlowSpec(project="demo", version=5, review=APPROVED))
    mref = make_model_runner(source_id=CID)(ctx, ref)
    spec = store.load_flowspec()
    check("(c) +MODEL: flow lands in reviewed spec as DRAFT, never APPROVED", len(spec.flows) == 1 and spec.review.status is ReviewStatus.DRAFT, f"v={spec.version} review={spec.review}")
    # MODEL re-run: idempotent?
    b1 = store.paths.flowspec.read_bytes()
    make_model_runner(source_id=CID)(ctx, ref)
    check("(c) +MODEL re-run: persisted bytes identical", store.paths.flowspec.read_bytes() == b1)
    # Approve then re-run DISCOVER+MODEL
    store.save_flowspec(review_stage.approve(store.load_flowspec(), "umesh"))
    b2 = store.paths.flowspec.read_bytes()
    make_model_runner(source_id=CID)(ctx, ref)
    print("   (c) approved + MODEL re-run: bytes equal =", store.paths.flowspec.read_bytes() == b2, "status=", store.load_flowspec().review.status.value)

# ---- P6 expand gate
with tempfile.TemporaryDirectory() as td:
    store, nodes = seed(Path(td))
    store.save_flowspec(FlowSpec(project="demo", version=5, review=APPROVED))
    _merge_into_flowspec(store, "demo", CID)
    spec = store.load_flowspec()
    class Spy(MockProvider):
        calls = 0
        def act(self, *a, **k):
            Spy.calls += 1
            return super().act(*a, **k)
    prov = Spy(responses={"agent": [ExpandedSteps(steps=[Step(order=1, action=Action.CLICK, target="x")], rationale="r") for _ in range(30)]})
    try:
        expand(spec, prov, store=store)
        check("P6 expand on crawl-merged DRAFT spec raises", False, "no raise")
    except FlowSpecNotReviewed as e:
        check("P6 expand raises FlowSpecNotReviewed BEFORE any provider call", Spy.calls == 0 and not prov.prompts, f"calls={Spy.calls}")
    from autotester.stages.expand import expand_flow, propose_cases
    for fn, args in ((propose_cases, (spec,)),):
        try:
            fn(*args); check("P6 propose_cases refuses DRAFT", False)
        except FlowSpecNotReviewed:
            check("P6 propose_cases refuses DRAFT", True)
    try:
        expand_flow(spec.flows[0], "demo", prov, store=store)
        check("P6 expand_flow refuses DRAFT", False)
    except FlowSpecNotReviewed:
        check("P6 expand_flow refuses DRAFT", Spy.calls == 0)
    # approve flowspec only, no proposal approval => still no cases
    approved = review_stage.approve(spec, "umesh")
    store.save_flowspec(approved)
    try:
        expand(approved, prov, store=store)
        print("   expand after approve (no proposals approved): returned without error; provider calls =", Spy.calls)
    except Exception as e:
        print("   expand after approve, proposals unreviewed ->", type(e).__name__, str(e)[:100], "| provider calls =", Spy.calls)
    # full human path
    rows = stage_and_review(store, approved, approve=[p.id for p in propose_cases(approved)], prune=[], by="umesh")
    cases = expand(approved, prov, store=store)
    check("P6 after human approve + proposal approval expand works", len(cases) >= 1, f"cases={len(cases)} provider calls={Spy.calls}")
    leak = [p for _, p in prov.prompts if "bob@corp.com" in p]
    check("expand prompt masks email from edge.target (AT-890)", not leak and Spy.calls > 0, f"prompts={len(prov.prompts)} leaks={len(leak)}")
    print("   a masked prompt excerpt:", [p for _, p in prov.prompts][0][-300:].replace("\n", " | ") if prov.prompts else None)
    # do the *cases* (happy) retain the raw email target?
    print("   happy case step targets (stored, not sent to provider):", [s.target for s in cases[0].steps])

print("\nSUMMARY:", sum(1 for r in R if r[1]), "pass", sum(1 for r in R if not r[1]), "fail")
for r in R:
    if not r[1]:
        print("FAILED:", r[0], r[2])

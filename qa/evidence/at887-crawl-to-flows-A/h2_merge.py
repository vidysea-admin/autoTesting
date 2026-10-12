"""Hostile P2/P3 + dangling-screen-id checks on merge_screens_and_flows."""
import hashlib
import sys

from autotester.schema.enums import Action, EdgeOutcome, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Screen, Step, SourceRef
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_flows import flows_from_crawl
from autotester.stages.explore_merge import merge_screens, merge_screens_and_flows

R = []


def check(name, ok, detail=""):
    R.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name, detail)


def node(cid, tpl, sig, name="", disc=None):
    return ScreenNode(crawl_id=cid, project="p", url_template=tpl, url_example=f"https://x.test{tpl}",
                      signature=sig, name=name, discovered_by=disc)


def graph(cid):
    h = node(cid, "/h", "h", "Home")
    e = ScreenEdge(crawl_id=cid, from_node=h.id, action=Action.NAVIGATE, target="go", outcome=EdgeOutcome.NAVIGATED)
    t = node(cid, "/t", "t", "T", disc=e.id)
    return [h, t], [e]


nodes, edges = graph("c1")
proposed = flows_from_crawl(nodes, edges, crawl_id="c1")[0]
fid = proposed.id

# P2: approved spec w/ a human-edited flow with the same id; screens already present -> nothing new
from autotester.stages.explore_merge import screen_from
human = Flow(id=fid, name="HUMAN EDITED", entry_screen=nodes[0].id, exit_screen=nodes[1].id,
             steps=[Step(order=1, action=Action.CLICK, target="human step", value="v", note="edited by human")])
appr = Review(status=ReviewStatus.APPROVED, by="umesh", at="2026-10-10T00:00:00Z", note="ok")
spec = FlowSpec(project="p", version=7, screens=[screen_from(n) for n in nodes], flows=[human],
                source_ids=["c1"], review=appr)
before = spec.model_dump_json()
out = merge_screens_and_flows(spec, nodes, edges, "p", crawl_id="c1")
check("P3 nothing new: SAME object returned", out is spec)
check("P3 nothing new: still APPROVED, version 7, bytes identical", out.review.status is ReviewStatus.APPROVED and out.version == 7 and out.model_dump_json() == before)
out = merge_screens_and_flows(spec, nodes, edges, "p", crawl_id="c9")  # different crawl id, same graph
check("P3 nothing new w/ different crawl id: same object", out is spec, f"source_ids={out.source_ids}")

# P2 + new flow elsewhere: add a second branch => new flow, human flow untouched, review DRAFT, version +1
b = node("c2", "/b", "b", "B");
eb = ScreenEdge(crawl_id="c2", from_node=nodes[0].id, action=Action.NAVIGATE, target="goB", outcome=EdgeOutcome.NAVIGATED)
b.discovered_by = eb.id
nodes2, edges2 = nodes + [b], edges + [eb]
before_human = human.model_dump_json()
out = merge_screens_and_flows(spec, nodes2, edges2, "p", crawl_id="c2")
check("P2 human flow byte-identical after adding other flow", out.flow(fid).model_dump_json() == before_human)
check("P3 adds screen+flow: version exactly +1 (8)", out.version == 8, f"v={out.version}")
check("P3 adds: review DRAFT, by/at empty", out.review.status is ReviewStatus.DRAFT and out.review.by is None and out.review.at is None, repr(out.review))
print("   note:", out.review.note)
check("input spec NOT mutated", spec.model_dump_json() == before)

# corner: only a SCREEN added, zero new flows (flows already present)
nodes_ro = nodes + [node("c1", "/orphanscreen", "o", "Orphan", disc="edge_missing")]  # orphan => no flow
out = merge_screens_and_flows(spec, nodes_ro, edges, "p", crawl_id="c1")
check("only-screen: version +1 (8) not +2", out.version == 8 and len(out.screens) == 3 and len(out.flows) == 1, f"v={out.version} screens={len(out.screens)} flows={len(out.flows)}")
check("only-screen: DRAFT", out.review.status is ReviewStatus.DRAFT, out.review.note)
# orphan root is not an orphan: discovered_by=None root would make a flow. Check 'edge_missing' orphan yields no flow
# corner: only flows added, zero screens
spec_s = FlowSpec(project="p", version=3, screens=[screen_from(n) for n in nodes], review=appr)
out = merge_screens_and_flows(spec_s, nodes, edges, "p", crawl_id="c1")
check("only-flows: version +1 (4)", out.version == 4 and len(out.flows) == 1 and len(out.screens) == 2, f"v={out.version}")
check("only-flows: DRAFT w/ sensible note", out.review.status is ReviewStatus.DRAFT, out.review.note)
# None spec, flows+screens both
out = merge_screens_and_flows(None, nodes, edges, "p", crawl_id="c1")
check("None spec: version 2, DRAFT", out.version == 2 and out.review.status is ReviewStatus.DRAFT, f"v={out.version} note={out.review.note}")
# None spec, no screens and no flows (empty crawl)
out = merge_screens_and_flows(None, [], [], "p", crawl_id="c1")
check("None spec + empty crawl: fresh spec v1 DRAFT", out.version == 1 and not out.flows)
# None spec, nodes but only unreplayable -> screens only
fe = ScreenEdge(crawl_id="c1", from_node="x", action=Action.FILL, target="t", outcome=EdgeOutcome.NAVIGATED)
o2 = node("c1", "/o2", "o2", "O2", disc=fe.id)
out = merge_screens_and_flows(None, [o2], [fe], "p", crawl_id="c1")
check("None + only orphan: v2 and zero flows", out.version == 2 and not out.flows)

# APPROVED spec must not stay APPROVED when new things added; NEEDS_EDIT -> DRAFT too
for st in (ReviewStatus.APPROVED, ReviewStatus.NEEDS_EDIT):
    sp = FlowSpec(project="p", version=1, review=Review(status=st, by="u", at="t", note="n"))
    out = merge_screens_and_flows(sp, nodes, edges, "p", crawl_id="c1")
    check(f"{st.value} + new flows -> DRAFT, by/at cleared", out.review.status is ReviewStatus.DRAFT and out.review.by is None and out.review.at is None)
# Idempotence second merge
out1 = merge_screens_and_flows(None, nodes, edges, "p", crawl_id="c1")
out2 = merge_screens_and_flows(out1, nodes, edges, "p", crawl_id="c1")
check("second merge same crawl: same obj, v unchanged", out2 is out1 and out2.version == 2)

# Rediscovery dangling: human screen same url_pattern & same name (non structural) => node screen not added
hs = Screen(id="human_home", name="Home", url_pattern="/h")
sp = FlowSpec(project="p", screens=[hs], review=appr)
out = merge_screens_and_flows(sp, nodes, edges, "p", crawl_id="c1")
sids = {s.id for s in out.screens}
dang = [(f.name, s.order, s.screen_id) for f in out.flows for s in f.steps if s.screen_id not in sids]
dang_e = [(f.name, f.entry_screen) for f in out.flows if f.entry_screen not in sids]
check("rediscovered human screen: flow screen_ids resolve to spec.screens", not dang and not dang_e, f"DANGLING steps={dang} entry={dang_e} screens={sorted(sids)}")

# Same url_pattern + different name (conflict path) still adds screen
hs2 = Screen(id="human_home", name="Landing", url_pattern="/h")
sp = FlowSpec(project="p", screens=[hs2], review=appr)
out = merge_screens_and_flows(sp, nodes, edges, "p", crawl_id="c1")
sids = {s.id for s in out.screens}
dang = [(f.name, s.screen_id) for f in out.flows for s in f.steps if s.screen_id not in sids]
check("conflicting-name path: screen_ids resolve", not dang and len(out.conflicts) in (0, 1), f"conflicts={len(out.conflicts)} dang={dang}")

# Flow id present but different crawl: login_case difference; existing wins
spec_a = merge_screens_and_flows(None, nodes, edges, "p", crawl_id="c1")
spec_b = merge_screens_and_flows(spec_a, nodes, edges, "p", crawl_id="c1", login_case_id="case_login")
check("same path now with login case: existing flow wins, nothing changes", spec_b is spec_a and not spec_a.flows[0].requires_auth,
      f"requires_auth={spec_a.flows[0].requires_auth}  (finding: login added later never reaches existing flow)")

# merge_screens unchanged: compare to old module behaviour on a battery
import importlib.util, pathlib
old_path = pathlib.Path(sys.argv[1])
spec_ = importlib.util.spec_from_file_location("old_merge", old_path)
old = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(old)
import random
rnd = random.Random(3)
same = True
for trial in range(30):
    ns = [node("cX", f"/p{i%4}", f"s{i}", rnd.choice(["A", "B", "C"])) for i in range(rnd.randint(0, 6))]
    base = rnd.choice([None, FlowSpec(project="p", screens=[Screen(id="h1", name="A", url_pattern="/p1")], review=appr, version=4)])
    a = merge_screens(base, ns, "p", crawl_id="cX"); b2 = old.merge_screens(base, ns, "p", crawl_id="cX")
    if a.model_dump_json(exclude={"created_at"}) != b2.model_dump_json(exclude={"created_at"}):
        same = False
check("P5 merge_screens == old(3748cb83) over 30 random trials", same)

print("\nSUMMARY:", sum(1 for r in R if r[1]), "pass", sum(1 for r in R if not r[1]), "fail")
for r in R:
    if not r[1]:
        print("FAILED:", r[0], r[2])

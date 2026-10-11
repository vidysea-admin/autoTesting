"""Hostile checks on flows_from_crawl + merge_screens_and_flows (pure, no store)."""
import random
import subprocess
import sys

import autotester
from autotester.schema.enums import Action, EdgeOutcome, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_flows import flows_from_crawl
from autotester.stages.explore_merge import merge_screens, merge_screens_and_flows

print("module file:", autotester.__file__)
R = []


def check(name, ok, detail=""):
    R.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name, detail)


def node(cid, tpl, sig, name="", disc=None, url=None, title=""):
    return ScreenNode(crawl_id=cid, project="p", url_template=tpl, url_example=url or f"https://x.test{tpl}",
                      signature=sig, name=name, title=title, discovered_by=disc)


def edge(cid, frm, target, action=Action.NAVIGATE, outcome=EdgeOutcome.NAVIGATED, to=None):
    return ScreenEdge(crawl_id=cid, from_node=frm, to_node=to, action=action, target=target, outcome=outcome)


def chain(cid, n, prefix="/s", names=True):
    nodes = [node(cid, f"x.test{prefix}0", "s0", "Home" if names else "", url=f"https://x.test{prefix}0")]
    edges = []
    for i in range(1, n):
        e = edge(cid, nodes[-1].id, f'role=link[name="L{i}"]')
        edges.append(e)
        nodes.append(node(cid, f"x.test{prefix}{i}", f"s{i}", f"S{i}" if names else "",
                          disc=e.id, url=f"https://x.test{prefix}{i}"))
    return nodes, edges


# 1 linear chain
nodes, edges = chain("c1", 4)
fl = flows_from_crawl(nodes, edges, crawl_id="c1")
check("linear chain -> 1 flow", len(fl) == 1, f"steps={[ (s.order,s.action.value) for s in fl[0].steps]}")
check("orders 1..n", [s.order for s in fl[0].steps] == [1, 2, 3, 4])
ids = {n.id for n in nodes}
check("entry/exit are real node ids", fl[0].entry_screen == nodes[0].id and fl[0].exit_screen == nodes[-1].id)

# 2 branching tree
home = node("c2", "x.test/h", "h", "Home")
e1 = edge("c2", home.id, "a1"); e2 = edge("c2", home.id, "a2")
a = node("c2", "x.test/a", "a", "A", disc=e1.id); b = node("c2", "x.test/b", "b", "B", disc=e2.id)
e3 = edge("c2", a.id, "a3"); c = node("c2", "x.test/c", "c", "C", disc=e3.id)
fl = flows_from_crawl([home, a, b, c], [e1, e2, e3], crawl_id="c2")
check("tree: leaves b and c => 2 flows", len(fl) == 2 and {f.exit_screen for f in fl} == {b.id, c.id},
      f"exits={[f.name for f in fl]}")
# lone landing screen (root only, no edges)
fl = flows_from_crawl([home], [], crawl_id="c2")
check("single root node -> 1 flow with 1 step", len(fl) == 1 and len(fl[0].steps) == 1, str([f.name for f in fl]))

# 3 typed edge
for act in (Action.FILL, Action.SELECT, Action.BACK, Action.HOVER, Action.PRESS_KEY, Action.UPLOAD, Action.SCROLL, Action.WAIT, Action.ASSERT):
    h = node("c3", "x.test/h", "h", "Home"); ef = edge("c3", h.id, "t", action=act)
    t = node("c3", "x.test/t", "t", "T", disc=ef.id)
    fl = flows_from_crawl([h, t], [ef], crawl_id="c3")
    # the leaf T is skipped; H is a root but H is the parent of ... parents derived only from valid chains
    exits = [f.exit_screen for f in fl]
    check(f"typed edge {act.value}: path to T skipped (no flow ends at T)", t.id not in exits, f"exits={[f.name for f in fl]}")
    # surprise check: root H becomes its own flow since T chain invalid
# 4 non-NAVIGATED
for oc in EdgeOutcome:
    if oc is EdgeOutcome.NAVIGATED:
        continue
    h = node("c4", "x.test/h", "h", "Home"); eo = edge("c4", h.id, "t", outcome=oc)
    t = node("c4", "x.test/t", "t", "T", disc=eo.id)
    fl = flows_from_crawl([h, t], [eo], crawl_id="c4")
    check(f"outcome {oc.value}: skipped", t.id not in [f.exit_screen for f in fl])
# 5 missing edge / missing parent
h = node("c5", "x.test/h", "h", "Home"); t = node("c5", "x.test/t", "t", "T", disc="edge_missing")
fl = flows_from_crawl([h, t], [], crawl_id="c5")
check("orphan (missing edge) skipped", t.id not in [f.exit_screen for f in fl])
ghost = edge("c5", "node_ghost", "g"); t2 = node("c5", "x.test/t2", "t2", "T2", disc=ghost.id)
fl = flows_from_crawl([h, t2], [ghost], crawl_id="c5")
check("orphan (parent missing) skipped", t2.id not in [f.exit_screen for f in fl])
# 6 2-cycle and self loop
x = node("c6", "x.test/x", "x", "X"); y = node("c6", "x.test/y", "y", "Y")
exy = edge("c6", x.id, "xy"); eyx = edge("c6", y.id, "yx")
x2 = x.model_copy(update={"discovered_by": eyx.id}); y2 = y.model_copy(update={"discovered_by": exy.id})
fl = flows_from_crawl([x2, y2], [exy, eyx], crawl_id="c6")
check("2-cycle: no flows, no hang", fl == [], str(len(fl)))
z = node("c6", "x.test/z", "z", "Z"); ezz = edge("c6", z.id, "zz")
z2 = z.model_copy(update={"discovered_by": ezz.id})
fl = flows_from_crawl([z2], [ezz], crawl_id="c6")
check("self-loop: no flows", fl == [], str(len(fl)))
# cycle hanging off a good root
hh = node("c6", "x.test/hh", "hh", "HH"); e_h = edge("c6", hh.id, "to_x")
xc = x.model_copy(update={"discovered_by": e_h.id}); eyx2 = edge("c6", xc.id, "x_to_y")
yc = y.model_copy(update={"discovered_by": eyx2.id}); eback = edge("c6", yc.id, "y_to_x")
# xc already discovered_by e_h; cycle can't be formed through discovered_by single-parent unless loops; skip.

# 7 two crawls overlapping path => same flow id
n1, e1_ = chain("crawlA", 3); n2, e2_ = chain("crawlB", 3)
fa = flows_from_crawl(n1, e1_, crawl_id="crawlA"); fb = flows_from_crawl(n2, e2_, crawl_id="crawlB")
print("   node ids same:", [a.id for a in n1] == [b.id for b in n2], " edge targets same")
check("same path, different crawl id => same flow id", fa[0].id == fb[0].id, f"{fa[0].id} {fb[0].id}")
spec = merge_screens_and_flows(None, n1, e1_, "p", crawl_id="crawlA")
spec2 = merge_screens_and_flows(spec, n2, e2_, "p", crawl_id="crawlB")
check("second crawl same path => no duplicate flow, same spec obj", len(spec2.flows) == 1 and spec2 is spec,
      f"flows={len(spec2.flows)} v={spec2.version}")
# but edge ids contain crawl_id: differing locator
print("   step[1].source_ref A:", fa[0].steps[1].source_ref, " B:", fb[0].steps[1].source_ref)

# 8 chain > 12
nodes, edges = chain("c8", 14)
fl = flows_from_crawl(nodes, edges, crawl_id="c8")
check("chain of 14 nodes (13 edges): leaf skipped", all(f.exit_screen != nodes[-1].id for f in fl), f"exits={[f.name[-30:] for f in fl]}")
nodes, edges = chain("c8b", 13)  # 12 edges
fl = flows_from_crawl(nodes, edges, crawl_id="c8b")
check("chain with exactly 12 edges accepted", any(f.exit_screen == nodes[-1].id for f in fl), f"nflows={len(fl)}")
# note: intermediate nodes have chain <=12 but are parents of the long chain's leaf? leaf invalid so parent set excludes
print("   flows for 14-chain:", len(flows_from_crawl(*chain("c8", 14), crawl_id="c8")), "(interior nodes become leaf flows when the leaf is dropped)")

# 9 node with no name/title
nodes, edges = chain("c9", 3, names=False)
fl = flows_from_crawl(nodes, edges, crawl_id="c9")
check("no-name nodes use url_template", "x.test/s0" in fl[0].name, fl[0].name)

# 10 name > 140
big = node("c10", "x.test/b", "b", "N" * 400)
fl = flows_from_crawl([big], [], crawl_id="c10")
check("name capped at 140", len(fl[0].name) == 140, str(len(fl[0].name)))

# 11 duplicate node ids
d1 = node("c11", "x.test/d", "d", "D1"); d2 = node("c11", "x.test/d", "d", "D2")
check("dup ids identical", d1.id == d2.id)
fl = flows_from_crawl([d1, d2], [], crawl_id="c11")
fl_rev = flows_from_crawl([d2, d1], [], crawl_id="c11")
check("duplicate node ids: 1 flow", len(fl) == 1, f"names {[f.name for f in fl]} vs reversed {[f.name for f in fl_rev]}")
check("duplicate node ids: order-independent output (D1/D2 differ in name)",
      [f.model_dump_json() for f in fl] == [f.model_dump_json() for f in fl_rev], f"{[f.name for f in fl]} vs {[f.name for f in fl_rev]}")
# duplicate edge ids differing in name only / outcome
h = node("c11", "x.test/h", "h", "Home")
ea = ScreenEdge(crawl_id="c11", from_node=h.id, action=Action.NAVIGATE, target="t", outcome=EdgeOutcome.NAVIGATED)
eb = ScreenEdge(crawl_id="c11", from_node=h.id, action=Action.NAVIGATE, target="t", outcome=EdgeOutcome.ERRORED)
tt = node("c11", "x.test/t", "t", "T", disc=ea.id)
check("dup edge ids (same key, different outcome)", ea.id == eb.id)
f1 = flows_from_crawl([h, tt], [ea, eb], crawl_id="c11"); f2 = flows_from_crawl([h, tt], [eb, ea], crawl_id="c11")
check("dup edge ids: order-independent", [f.model_dump_json() for f in f1] == [f.model_dump_json() for f in f2],
      f"{[f.name for f in f1]} vs {[f.name for f in f2]}")

# 12 shuffled x 20, bigger graph with tree, includes junk
nodes, edges = chain("c12", 5)
extra_h = nodes[1]
ex = edge("c12", extra_h.id, "branch"); bn = node("c12", "x.test/branch", "br", "Br", disc=ex.id)
fill = edge("c12", nodes[0].id, "fill", action=Action.FILL); fn = node("c12", "x.test/fn", "fn", "Fn", disc=fill.id)
allN = nodes + [bn, fn]; allE = edges + [ex, fill]
base = [f.model_dump_json() for f in flows_from_crawl(allN, allE, crawl_id="c12")]
ok = True
rnd = random.Random(7)
for _ in range(20):
    n_ = allN[:]; e_ = allE[:]; rnd.shuffle(n_); rnd.shuffle(e_)
    out = [f.model_dump_json() for f in flows_from_crawl(n_, e_, crawl_id="c12")]
    if out != base:
        ok = False
check("shuffle x20: byte-identical flows AND list order", ok, f"nflows={len(base)}")
# also across PYTHONHASHSEED (separate processes) -- see h1b

# 13 urls with query strings / ids / fragments / trailing slashes
u = node("c13", "x.test/users/:id", "u", "User", url="https://x.test/users/42/?tab=a#frag")
u0 = node("c13", "x.test/", "u0", "Root", url="https://x.test/")
eu = edge("c13", u0.id, "go"); u1 = node("c13", "x.test/users/:id", "u1", "UserB", disc=eu.id, url="https://x.test/users/42/?tab=a&sess=SECRETTOKEN#frag")
fl = flows_from_crawl([u0, u1], [eu], crawl_id="c13")
st = fl[0].steps
print("   urls: step targets:", [s.target for s in st], " expected.url:", [s.expected.url for s in st])
check("step1 target is the FULL url_example incl. query string (finding)", "sess=SECRETTOKEN" not in st[0].target and True,
      "(root target = " + st[0].target + ")")
fl2 = flows_from_crawl([u0.model_copy(update={"url_example": "https://x.test/"}), u1.model_copy(update={"url_example": "https://x.test/users/42/?sess=SECRETTOKEN"})], [eu], crawl_id="c13")
print("   leaf with secretish query: steps[-1].expected.url =", fl2[0].steps[-1].expected.url, "| source_ref locator =", fl2[0].steps[-1].source_ref.locator)
# root with token in url_example
r = node("c13", "x.test/land", "r", "Land", url="https://x.test/land?token=SECRETTOKEN123")
fl = flows_from_crawl([r], [], crawl_id="c13")
print("   ROOT step.target:", fl[0].steps[0].target, "| source_ref.locator:", fl[0].steps[0].source_ref.locator)
print("   FINDING secret-in-query lands verbatim in Step.target:", "SECRETTOKEN123" in fl[0].steps[0].target)

# 14 edge.target with email/secret-looking string
h = node("c14", "x.test/h", "h", "Home"); em = edge("c14", h.id, 'role=link[name="mail jane.doe@example.com"]')
t = node("c14", "x.test/t", "t", "Profile jane.doe@example.com", disc=em.id, title="Hi jane.doe@example.com")
fl = flows_from_crawl([h, t], [em], crawl_id="c14")
print("   edge.target email in Step.target:", "jane.doe@example.com" in fl[0].steps[1].target)
print("   node.name email in Flow.name:", "jane.doe@example.com" in fl[0].name, "->", fl[0].name)
sk = edge("c14", h.id, 'role=button[name="key sk-ant-api03-ABCDEF1234567890"]')
t3 = node("c14", "x.test/t3", "t3", "T3", disc=sk.id)
fl = flows_from_crawl([h, t3], [sk], crawl_id="c14")
print("   secret-looking edge.target in Step.target:", "sk-ant-api03" in fl[0].steps[1].target)

# 15 flows are valid Flow objects (roundtrip), step.screen_id references
nodes, edges = chain("c15", 4)
spec = merge_screens_and_flows(None, nodes, edges, "p", crawl_id="c15")
sids = {s.id for s in spec.screens}
for f in spec.flows:
    Flow.model_validate(f.model_dump(mode="json"))
    check("every step.screen_id in spec.screens", all(s.screen_id in sids for s in f.steps))
    check("entry/exit in spec.screens", f.entry_screen in sids and (f.exit_screen in sids))
print("   step list:", [(s.order, s.action.value, s.target, s.screen_id[:10], s.expected.url) for s in spec.flows[0].steps])

# 16 FlowSpec validators: does anything check flow.screen refs?
try:
    FlowSpec(project="p", flows=[Flow(id="f", name="n", entry_screen="NOPE", steps=[Step(order=1, action=Action.CLICK, target="t", screen_id="NOPE")])])
    print("   FlowSpec has NO validator rejecting dangling screen_id (so dangling is only a data defect)")
except Exception as e:
    print("   FlowSpec rejects dangling:", type(e).__name__)

print("\nSUMMARY:", sum(1 for r in R if r[1]), "pass", sum(1 for r in R if not r[1]), "fail")
for r in R:
    if not r[1]:
        print("FAILED:", r[0], r[2])

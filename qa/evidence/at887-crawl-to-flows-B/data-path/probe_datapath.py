"""B coordinator probe: AT-887 data path with an own fixture crawl. Run with b-copy venv."""
import hashlib, json, sys, tempfile
from pathlib import Path
import autotester
print("autotester.__file__", autotester.__file__)
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_merge import merge_stored_crawl
from autotester.store.project_store import ProjectStore

PROJECT = Project(slug="demo", name="Demo", base_url="https://app.test", allowed_domains=["app.test"])

def node(crawl, name, path, sig, by=None):
    return ScreenNode(crawl_id=crawl, project="demo", url_template=f"app.test{path}",
                      url_example=f"https://app.test{path}?id=7", signature=sig, name=name, discovered_by=by)

def edge(crawl, frm, target, action=Action.NAVIGATE, outcome="navigated"):
    return ScreenEdge(crawl_id=crawl, from_node=frm, target=target, action=action, outcome=outcome)

def build(root, crawl):
    store = ProjectStore("demo", root)
    store.save_project(PROJECT)
    store.save_crawl(Crawl(project="demo", id=crawl, login_case_id="case_login"))
    home = node(crawl, "Home", "/home", "s_home")
    e_course = edge(crawl, home.id, 'role=link[name="Courses"]')
    course = node(crawl, "Courses", "/courses", "s_course", e_course.id)
    e_detail = edge(crawl, course.id, 'role=link[name="Algebra"]')
    detail = node(crawl, "Algebra", "/courses/algebra", "s_alg", e_detail.id)
    # two paths to same leaf: home -> profile (first) ; course -> profile (second, rediscovered: not discovered_by)
    e_prof = edge(crawl, home.id, 'role=link[name="Profile"]')
    prof = node(crawl, "Profile", "/profile", "s_prof", e_prof.id)
    e_prof2 = edge(crawl, course.id, 'role=link[name="My profile"]')
    # typed FILL edge to search results
    e_fill = edge(crawl, home.id, 'role=searchbox', action=Action.FILL)
    results = node(crawl, "Results", "/search", "s_res", e_fill.id)
    # failed discovery
    e_fail = edge(crawl, home.id, 'role=link[name="Broken"]', outcome="errored")
    broken = node(crawl, "Broken", "/broken", "s_broken", e_fail.id)
    # orphan: points to an edge that does not exist
    orphan = node(crawl, "Orphan", "/orphan", "s_orphan", "edge_nonexistent")
    # cycle: a <-> b, neither root
    ca = node(crawl, "CycA", "/cyc-a", "s_ca"); cb = node(crawl, "CycB", "/cyc-b", "s_cb")
    e_ab = edge(crawl, ca.id, 'role=link[name="B"]'); e_ba = edge(crawl, cb.id, 'role=link[name="A"]')
    ca2 = ca.model_copy(update={"discovered_by": e_ba.id}); cb2 = cb.model_copy(update={"discovered_by": e_ab.id})
    nodes = [home, course, detail, prof, results, broken, orphan, ca2, cb2]
    for n in nodes: store.add_node(n)
    for e in (e_course, e_detail, e_prof, e_prof2, e_fill, e_fail, e_ab, e_ba): store.add_edge(e)
    return store

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]

with tempfile.TemporaryDirectory(dir=sys.argv[1]) as td:
    root = Path(td)
    s1 = build(root, "crawl_one")
    spec1 = merge_stored_crawl(s1, None, "demo", "crawl_one")
    s1.save_flowspec(spec1)
    print("FLOWS", len(spec1.flows), "review", spec1.review.status.value, spec1.review.by, "ver", spec1.version, "screens", len(spec1.screens))
    for f in spec1.flows:
        print(" -", f.name, "| auth", f.requires_auth, "| kind", f.kind, "| pre", f.preconditions)
        for st in f.steps:
            print("     ", st.order, st.action.value, st.target, "| url", st.expected.url, "| ref", st.source_ref.source_id, st.source_ref.locator)
    names = " ".join(f.name for f in spec1.flows)
    for bad in ("Results", "Broken", "Orphan", "CycA", "CycB"):
        print("name mentions", bad, bad in names)
    h1 = sha(s1.paths.flowspec)
    # second merge, same crawl
    spec1b = merge_stored_crawl(s1, s1.load_flowspec(), "demo", "crawl_one")
    s1.save_flowspec(spec1b)
    print("REMERGE same crawl: same object?", spec1b is not None, "bytes equal", sha(s1.paths.flowspec) == h1, "ver", spec1b.version)
    # re-crawl, different crawl id, different edge ids
    with tempfile.TemporaryDirectory(dir=sys.argv[1]) as td2:
        s2 = build(Path(td2), "crawl_two")
        ids1 = sorted(f.id for f in spec1.flows)
        ids2 = sorted(f.id for f in merge_stored_crawl(s2, None, "demo", "crawl_two").flows)
        print("IDS STABLE across crawl ids:", ids1 == ids2, len(ids1))
        # merge crawl two's nodes into spec from crawl one: copy crawl_two data into store 1
        for n in s2.list_nodes("crawl_two"): s1.add_node(n)
        for e in s2.list_edges("crawl_two"): s1.add_edge(e)
        s1.save_crawl(s2.load_crawl("crawl_two"))
        before = s1.paths.flowspec.read_bytes()
        spec_rc = merge_stored_crawl(s1, s1.load_flowspec(), "demo", "crawl_two")
        print("RECRAWL merge: flows", len(spec_rc.flows), "ver", spec_rc.version, "source_ids", spec_rc.source_ids,
              "is unchanged object content:", spec_rc.model_dump_json() == s1.load_flowspec().model_dump_json())
        s1.save_flowspec(spec_rc)
        print("RECRAWL persisted bytes identical:", s1.paths.flowspec.read_bytes() == before)
    # human-reviewed flow with the same path: approve spec, edit a flow, remerge, then add a new screen
    cur = s1.load_flowspec()
    edited_flow = cur.flows[0].model_copy(update={"name": "HUMAN RENAMED", "kind": "ideal"})
    approved = cur.model_copy(update={"flows": [edited_flow, *cur.flows[1:]],
                                      "review": Review(status=ReviewStatus.APPROVED, by="umesh")})
    s1.save_flowspec(approved); hb = sha(s1.paths.flowspec)
    again = merge_stored_crawl(s1, s1.load_flowspec(), "demo", "crawl_one")
    s1.save_flowspec(again)
    print("APPROVED + nothing new: still APPROVED", again.review.status.value, "by", again.review.by, "bytes identical", sha(s1.paths.flowspec) == hb)
    # add a new leaf in crawl one
    h = [n for n in s1.list_nodes("crawl_one") if n.name == "Home"][0]
    e_new = edge("crawl_one", h.id, 'role=link[name="Help"]')
    n_new = node("crawl_one", "Help", "/help", "s_help", e_new.id)
    s1.add_node(n_new); s1.add_edge(e_new)
    grown = merge_stored_crawl(s1, s1.load_flowspec(), "demo", "crawl_one")
    old_by_id = {f.id: f for f in approved.flows}
    kept = all(grown.flow(i) is not None and grown.flow(i).model_dump_json() == f.model_dump_json() for i, f in old_by_id.items())
    print("ADD one leaf: flows", len(approved.flows), "->", len(grown.flows), "| old flows byte-identical", kept,
          "| review", grown.review.status.value, "by", grown.review.by, "at", grown.review.at, "| ver", approved.version, "->", grown.version,
          "| human name kept", grown.flow(edited_flow.id).name)
    print("REVIEW NOTE:", grown.review.note)
    # existing Screens untouched
    ok = all(grown.screen(s.id).model_dump_json() == s.model_dump_json() for s in approved.screens)
    print("existing Screens untouched:", ok)

# --- referential integrity: do flow screen ids resolve to spec screens? (added after the main run)
with tempfile.TemporaryDirectory(dir=sys.argv[1]) as td3:
    s3 = build(Path(td3), "crawl_ri")
    sp = merge_stored_crawl(s3, None, "demo", "crawl_ri")
    ids = {s.id for s in sp.screens}
    for f in sp.flows:
        refs = [f.entry_screen, f.exit_screen] + [st.screen_id for st in f.steps]
        print("REFINT", f.name, "dangling:", [r for r in refs if r not in ids], "| of", len(refs))

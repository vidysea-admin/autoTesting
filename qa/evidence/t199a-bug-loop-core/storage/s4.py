from common import *
from pathlib import Path
import shutil, json, traceback
e1 = event(EventKind.FAIL, 1)
e2 = event(EventKind.FAIL, 2)
e3 = event(EventKind.FAIL, 3)
good_id = e1.event_id
def setup(tag):
    root = Path(fresh(tag))
    st = BugStore(root)
    st.apply_all([e1, e2])
    return root, st
def try_(label, fn):
    try:
        r = fn()
        print(f"  {label}: OK -> {r if not hasattr(r,'__len__') or len(str(r))<200 else str(r)[:200]}")
    except BaseException as ex:
        print(f"  {label}: RAISES {type(ex).__name__}: {str(ex)[:300]}")
def probe(name, mutate):
    print("==", name)
    root, st = setup("s4")
    d = root / EVENTS_DIR
    mutate(d)
    print("  files:", sorted(p.name for p in d.iterdir()))
    try_("events()", lambda: len(st.events()))
    try_("bugs()", lambda: {k: v.count for k, v in st.bugs().items()})
    try_("apply(new e3)", lambda: st.apply(e3).effect)
    try_("apply(existing e1)", lambda: st.apply(e1).effect)
    try_("apply_all([e1,e2,e3])", lambda: [a.effect.value for a in st.apply_all([e1, e2, e3])])
    try_("history", lambda: len(st.history(e1.bug_key)))
    print("  after files:", sorted(p.name for p in d.iterdir()))

def a(d):  # zero-length at a valid looking id (new id for e4 colliding)
    (d / f"{e3.event_id}.json").write_text("")
def b(d):  # truncated JSON for e3's id
    full = (d / f"{e1.event_id}.json").read_text()
    (d / f"{e3.event_id}.json").write_text(full[:len(full)//2])
def b2(d):  # truncate e1 itself
    p = d / f"{e1.event_id}.json"; full = p.read_text(); p.write_text(full[:len(full)//2])
def c(d):
    (d / f"{e3.event_id}.json").write_text('{"hello": 1}')
def dd(d):  # renamed copy
    shutil.copy(d / f"{e1.event_id}.json", d / "bev_aaaaaaaaaaaa.json")
def d2(d):  # rename e1's file to other name (content id != name)
    (d / f"{e1.event_id}.json").rename(d / "bev_bbbbbbbbbbbb.json")
def e(d):
    (d / "notes.txt").write_text("x"); (d / "bevx.json").write_text("not json"); (d / "bev_.tmp").write_text("x")
    (d / ".tmp-abc.json").write_text("{")
def f(d):
    (d / "bev_x.json").mkdir()
def g(d):  # valid json, valid schema, event_id mismatch to filename mismatch w/ different content
    p = d / f"{e1.event_id}.json"; j = json.loads(p.read_text()); j["event_id"] = "bev_000000000000"; p.write_text(json.dumps(j))
probe("a zero-length bev_<id>.json (new id)", a)
probe("b truncated JSON (new id)", b)
probe("b2 truncated JSON of an existing event", b2)
probe("c valid JSON wrong schema", c)
probe("d renamed duplicate copy (second name)", dd)
probe("d2 file renamed (name != content id)", d2)
probe("e junk names in dir", e)
probe("f directory named bev_x.json", f)
probe("g wrong event_id inside file", g)

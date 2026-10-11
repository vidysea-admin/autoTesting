from common import *
from pathlib import Path
import os, pydantic
root = Path(fresh("s5")) / "proj"
parent = root.parent
def tree(p):
    return sorted(str(x.relative_to(p)) for x in p.rglob("*"))
def snap():
    return set(tree(parent))
hostile = ["../../x", "a/b", "C:" + chr(92) + "x", ".." + chr(92) + ".." + chr(92) + "evil", "a\x00b", "x"*5000, "ünï\u202ecode\U0001F600", "CON", "aux.txt", "bev_..", "a:b"]
for h in hostile:
    for field in ("bug_key", "ref"):
        before = snap()
        try:
            kw = dict(kind=EventKind.ASSIGN, at=at(1), actor="user:u", assignee="u")
            if field == "bug_key":
                ev = BugEvent(bug_key=h, ref="r1", **kw)
            else:
                ev = BugEvent(bug_key=KEY, ref=h, **kw)
            r = BugStore(root).apply(ev)
            new = snap() - before
            print(f"{field}={h[:20]!r}: effect={r.effect.value}/{r.reason}; new={sorted(new)[:4]} id={ev.event_id}")
        except BaseException as ex:
            print(f"{field}={h[:20]!r}: {type(ex).__name__}: {str(ex)[:100]!r}")
# note: ASSIGN with no bug -> NO_BUG but stored (not unjudged)
print("tree:", tree(parent))
# outside root scan
print("files outside bug_events:", [t for t in tree(parent) if not t.replace(chr(92),'/').startswith("proj/bug_events/") and t != "proj" and t != "proj/bug_events"])
print("all names bev_<12hex>.json:", all(__import__('re').fullmatch(r"bev_[0-9a-f]{12}\.json", Path(t).name) for t in tree(parent) if t.endswith(".json")))
# hostile actor / assignee
for actor in ["../x", "user:.." + chr(92) + ".." + chr(92) + "x", "a\x00", "x"*81, "", " lead", "user:/etc/passwd", "user:a/../../b"]:
    try:
        BugEvent(bug_key=KEY, kind=EventKind.ASSIGN, ref="r", at=at(1), actor=actor, assignee="u"); print("actor ACCEPTED", repr(actor))
    except pydantic.ValidationError: print("actor refused", repr(actor)[:30])
for asg in ["../../x", "a\nb", "x"*121, "a\x00", "C:" + chr(92) + "x"]:
    try:
        BugEvent(bug_key=KEY, kind=EventKind.ASSIGN, ref="r", at=at(1), actor="user:u", assignee=asg); print("assignee ACCEPTED", repr(asg)[:30])
    except pydantic.ValidationError: print("assignee refused", repr(asg)[:30])
# BugSeed hostile
for k in ["../../x", "a/b", "iss_" + "0"*12 + "/../x", "iss_0123456789ab\n"]:
    try:
        BugSeed(bug_key=k, project="p", title="t"); print("seed ACCEPTED", repr(k))
    except pydantic.ValidationError as e: print("seed refused", repr(k))
try:
    BugSeed(bug_key="../../x", project="p", case_id="c", criterion_id="C1", title="t"); print("seed w/case ACCEPTED")
except pydantic.ValidationError: print("seed w/ case refused")
# event_id supplied hostile
try:
    BugEvent(event_id="../../evil", bug_key=KEY, kind=EventKind.ASSIGN, ref="r", at=at(1), actor="user:u"); print("event_id ACCEPTED")
except pydantic.ValidationError: print("hostile event_id refused")
# roots
os.chdir(SCR)
rel = Path("probe_store")/ "s5rel" / "sub" / ".." / ".." / "s5rel2"
st = BugStore(rel)
print("missing dir exists?", st.dir.exists())
for name, fn in [("events", st.events), ("bugs", st.bugs), ("history", lambda: st.history(KEY)), ("get", lambda: st.get(KEY))]:
    try: print(" missing-dir", name, "->", fn())
    except BaseException as ex: print(" missing-dir", name, "RAISES", type(ex).__name__, str(ex)[:120])
try:
    print(" missing-dir apply_all([]) ->", st.apply_all([]))
except BaseException as ex: print(" apply_all([]) RAISES", type(ex).__name__, str(ex)[:120])
try:
    r = st.apply(event(EventKind.FAIL, 1)); print(" apply creates dir:", st.dir.exists(), r.effect.value, "abs=", st.dir.resolve())
except BaseException as ex: print(" apply RAISES", type(ex).__name__, str(ex)[:150])

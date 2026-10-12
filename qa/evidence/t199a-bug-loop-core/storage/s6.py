from common import *
from pathlib import Path
evs = [event(EventKind.FAIL, n) for n in range(1, 7)]
# crash: first half written via _write only
root = Path(fresh("s6")); st = BugStore(root)
for e in evs[:3]: st._write(e)
r = st.apply_all(evs)
print("crash-resume effects:", [a.effect.value for a in r], "files", len(list(st.dir.glob('*'))), "count", st.get(KEY).count)
r = st.apply_all(evs)
print("again:", [a.effect.value for a in r], "files", len(list(st.dir.glob('*'))))
# same event twice in one list
root = Path(fresh("s6b")); st = BugStore(root)
r = st.apply_all([evs[0], evs[1], evs[0]])
print("dup in list:", [a.effect.value for a in r], "files", len(list(st.dir.glob('*'))), "count", st.get(KEY).count)
# refused actor in the middle
root = Path(fresh("s6c")); st = BugStore(root)
bad = event(EventKind.FAIL, 99, actor="user:umesh")   # human actor making a status event
bad2 = event(EventKind.ASSIGN, 98, actor="system:bug-loop")
r = st.apply_all([evs[0], bad, evs[1], bad2, evs[2]])
print("refused middle:", [(a.effect.value, a.reason.value if a.reason else None) for a in r], "files", len(list(st.dir.glob('*'))), "count", st.get(KEY).count)
r2 = st.apply_all([evs[0], bad, evs[1], bad2, evs[2]])
print("refused middle again:", [(a.effect.value) for a in r2], "files", len(list(st.dir.glob('*'))))
# refused event twice in one list: second marks duplicate?
r = st.apply_all([bad, bad])
print("refused twice:", [(a.effect.value, a.reason.value if a.reason else None) for a in r])
# same id valid event after refused of same id? (actor not part of id)
good_same = event(EventKind.FAIL, 99, actor="system:bug-loop")
print("same id as refused:", good_same.event_id == bad.event_id)
r = st.apply_all([bad, good_same])
print("refused then valid same id:", [(a.effect.value, a.reason.value if a.reason else None) for a in r], "files", len(list(st.dir.glob('*'))))
# unjudged kind storage
root = Path(fresh("s6d")); st = BugStore(root)
r = st.apply_all([evs[0], event(EventKind.INCONCLUSIVE, 5, with_seed=False)])
print("unjudged:", [(a.effect.value, a.reason.value if a.reason else None) for a in r], "files", len(list(st.dir.glob('*'))))
# exception mid-trace after write: poisoned file + new event -> stored but raised
root = Path(fresh("s6e")); st = BugStore(root); st.apply(evs[0])
(st.dir / "bev_000000000001.json").write_text("{")
e4 = evs[3]
try: st.apply(e4)
except Exception as ex: print("apply with poison: raised", type(ex).__name__)
print("e4 file written despite raise:", (st.dir / f"{e4.event_id}.json").exists())

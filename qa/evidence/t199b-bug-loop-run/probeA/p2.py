from common import *
import tempfile, json, os, stat, itertools
from datetime import timedelta, datetime, UTC
import autotester.store.bug_store as bsm
from autotester.schema.tracked_bug import *
from autotester.stages.bug_loop import Effect
from bug_loop_fixture import event, seed, KEY, CASE
print("autotester:", autotester.__file__)
BASE = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
NOW = T0 + timedelta(days=1)
def fresh(name, clock=lambda: NOW):
    return BugStore(BASE/name/"bugs", clock=clock)
# 2a read count
b = fresh("rc")
evs = []
for i in range(30):
    evs.append(event(EventKind.FAIL if i%2==0 else EventKind.PASS, i+1, ref=f"r{i}/{CASE}", run=f"r{i}"))
b.apply_all(evs)
print("2a files:", len(list(b.dir.glob("*.json"))))
cnt = {"n": 0}; orig = bsm.read_json
def counting(p, m): cnt["n"] += 1; return orig(p, m)
bsm.read_json = counting
# process_run with store of 30 events
s, c = build(BASE/"rcp", 2)
b2 = BugStore(BASE/"rcp"/"bugs", clock=lambda: NOW)
b2.apply_all(evs)
finished_run(s, "runX", 40, [verdict(c, "runX", Result.FAIL, failing=("C1","C2"), total=2)], [c])
cnt["n"] = 0; r = process_run(s, b2, "runX"); print("2a read_json calls for process_run on 30+ events store:", cnt["n"], "files now", len(list(b2.dir.glob("*.json"))), "applied", r.applied)
cnt["n"] = 0; b2.snapshot(); print("   snapshot alone:", cnt["n"])
cnt["n"] = 0; process_run(s, b2, "runX"); print("   second process_run (dup):", cnt["n"])
bsm.read_json = orig
# 2b corrupt kinds
b = fresh("bad")
e1 = event(EventKind.FAIL, 1); e2 = event(EventKind.PASS, 2); e3 = event(EventKind.PASS, 3)
b.apply_all([e1, e2, e3])
ref_fold = foldjson(b)[0]
d = b.dir
good_names = sorted(p.name for p in d.glob("*.json"))
(d/"bev_torn.json").write_text('{"schema_version": 1, "bug_k', encoding="utf-8")
(d/"bev_empty.json").write_bytes(b"")
(d/"bev_arr.json").write_text("[]")
(d/"bev_obj.json").write_text("{}")
# valid event content under wrong name
(d/"bev_wrongname@20261001T090100000000Z.json").write_text(d.joinpath(good_names[0]).read_text())
(d/"bev_x.txt").write_text("hi")
(d/"other.json").write_text("{}")
pass
(d/"bev_ro.json").write_text("x"); os.chmod(d/"bev_ro.json", stat.S_IREAD)
try:
    sn = b.snapshot()
    print("2b snapshot ok; bad:")
    for x in sn.bad: print("   ", x.name, "|", x.why[:90])
    print("   fold unchanged:", {k:v.model_dump_json() for k,v in sn.bugs.items()} == ref_fold, "events", len(sn.events))
except BaseException as ex:
    print("2b snapshot RAISED", type(ex).__name__, str(ex)[:200])
print("   names listed in dir:", sorted(p.name for p in d.iterdir()))
# the directory named bev_dir.json
# repair: apply e1 again after corrupting its own file
p1 = d/good_names[0]
orig_bytes = p1.read_bytes()
p1.write_text("garbage")
sn = b.snapshot(); print("2b own file corrupt -> bad count", len(sn.bad), "events", len(sn.events))
b.apply(e1); print("   after re-apply file restored:", p1.read_bytes() == orig_bytes)
# repair overwriting a file holding a DIFFERENT valid event? target name == e1's name, content = different valid event
other = event(EventKind.PASS, 9)  # different event
p1.write_text(other.model_dump_json(indent=2, exclude_none=True))
b.apply(e1)
print("   file at e1 name holding other valid event -> after apply(e1): content is e1?", BugEvent.model_validate_json(p1.read_text()).event_id == e1.event_id, "other.event_id", other.event_id, "e1", e1.event_id)
print("   snapshot bad after:", [x.name for x in b.snapshot().bad][:3])
# 2c boundaries
def try_at(label, at_dt, clock_now=NOW):
    bb = fresh("bd_"+label, clock=lambda: clock_now)
    ev = event(EventKind.FAIL, 1, minutes=0)
    ev = ev.model_copy(update={"at": at_dt}); ev = BugEvent.model_validate(ev.model_dump())
    r = bb.apply(ev)
    return r.effect.value, r.reason.value if r.reason else None, len(list(bb.dir.glob("*.json"))) if bb.dir.exists() else 0
us = timedelta(microseconds=1)
print("2c now+5min:", try_at("a", NOW+timedelta(minutes=5)))
print("2c now+5min+1us:", try_at("b", NOW+timedelta(minutes=5)+us))
print("2c 2020-01-01Z:", try_at("c", datetime(2020,1,1,tzinfo=UTC)))
print("2c 2020-01-01Z-1us:", try_at("d", datetime(2020,1,1,tzinfo=UTC)-us))
from datetime import timezone
ist = timezone(timedelta(hours=5, minutes=30))
print("2c +05:30 same instant as 2020-01-01Z:", try_at("e", datetime(2020,1,1,5,30,tzinfo=ist)))
print("2c +05:30 1us before:", try_at("f", datetime(2020,1,1,5,30,tzinfo=ist)-us))
try:
    print("2c naive:", try_at("g", datetime(2026,10,1,9,5)))
except Exception as ex: print("2c naive raises at model:", type(ex).__name__, str(ex).splitlines()[0][:80])
# later acceptance
bb = fresh("late", clock=lambda: NOW)
ev = BugEvent.model_validate({**event(EventKind.FAIL,1).model_dump(), "at": NOW+timedelta(minutes=6)})
print("2c refused first:", bb.apply(ev).effect.value, len(list(bb.dir.glob('*.json'))) if bb.dir.exists() else 0)
bb.clock = lambda: NOW+timedelta(minutes=2)
print("2c clock caught up:", bb.apply(ev).effect.value, len(list(bb.dir.glob('*.json'))))
# other-offset file name
evi = BugEvent.model_validate({**event(EventKind.FAIL,1).model_dump(), "at": datetime(2026,10,1,14,35,tzinfo=ist)})
evu = BugEvent.model_validate({**event(EventKind.FAIL,1).model_dump(), "at": datetime(2026,10,1,9,5,tzinfo=UTC)})
print("2c same instant +05:30 vs UTC filename equal:", bsm.file_name(evi) == bsm.file_name(evu), bsm.file_name(evi))

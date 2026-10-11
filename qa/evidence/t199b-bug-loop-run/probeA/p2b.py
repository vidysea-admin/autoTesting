from common import *
import tempfile, os, stat
from datetime import timedelta
import autotester.store.bug_store as bsm
from autotester.schema.tracked_bug import *
from bug_loop_fixture import event, CASE
BASE = Path(tempfile.mkdtemp(dir="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeA"))
NOW = T0 + timedelta(days=1)
b = BugStore(BASE/"bugs", clock=lambda: NOW)
e1 = event(EventKind.FAIL, 1); e2 = event(EventKind.PASS, 2)
b.apply_all([e1, e2])
p1 = b.dir/bsm.file_name(e1); orig = p1.read_bytes()
p1.write_text("garbage")
sn = b.snapshot(); print("own file corrupt: bad", [x.name for x in sn.bad], "events", len(sn.events))
r = b.apply(e1); print("re-apply effect", r.effect.value, "restored:", p1.read_bytes() == orig, "bad now", [x.name for x in b.snapshot().bad])
# file at e1's name holds a DIFFERENT valid event (e2's content)
p1.write_bytes(b.dir.joinpath(bsm.file_name(e2)).read_bytes())
sn = b.snapshot(); print("e1 name holds e2 content: bad", [x.name for x in sn.bad], "events", len(sn.events))
r = b.apply(e1); got = BugEvent.model_validate_json(p1.read_text()).event_id
print("apply(e1): effect", r.effect.value, "file now holds e1:", got == e1.event_id)
# zero length + read-only
p1.write_bytes(b""); os.chmod(p1, stat.S_IREAD)
try:
    r = b.apply(e1); print("readonly+empty own file: apply ->", r.effect.value, "restored", p1.read_bytes() == orig)
except BaseException as ex: print("readonly+empty own file: apply raised", type(ex).__name__, str(ex)[:120])
os.chmod(p1, stat.S_IWRITE|stat.S_IREAD)
# directory named like an event
(b.dir/"bev_dir.json").mkdir()
try: b.snapshot(); print("dir named bev_dir.json: snapshot ok")
except BaseException as ex: print("dir named bev_dir.json: snapshot RAISED", type(ex).__name__)
try: b.apply(e1); print("   apply ok")
except BaseException as ex: print("   apply RAISED", type(ex).__name__)
# locked file (open handle exclusive on Windows)
import msvcrt, ctypes
(b.dir/"bev_dir.json").rmdir()

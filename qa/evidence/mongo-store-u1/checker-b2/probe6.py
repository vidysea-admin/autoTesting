"""Checker B cycle 2: chains, frames, pickling/copy, introspection reach, repr leaks. Fake client only."""
import sys, traceback, copy, pickle, weakref, functools, gc, io, logging, contextlib
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
import autotester.store.mongo_guard as g
import fake_mongo as fm
from pymongo.errors import AutoReconnect

CAN = "CANARYpw9f3a"
URI = f"mongodb://umesh:{CAN}@h.example/"

def safe(v):
    try: return repr(v)
    except Exception as x: return 'REPR-RAISES ' + type(x).__name__

def chain(e):
    out = []
    while e is not None:
        out.append((type(e).__name__, str(e)[:80], CAN in str(e)))
        e = e.__cause__ or e.__context__
    return out

print("== 1. exception chain after the driver raised text carrying the URI")
def bad_factory(u): raise RuntimeError(f"cannot connect {u}")
try:
    with fm.seams(client_factory=bad_factory): g.GuardedStore(URI)
except Exception as e:
    print("ctor:", type(e).__name__, "cause", e.__cause__, "suppress", e.__suppress_context__, "context", repr(e.__context__)[:100])
    print("  chain:", chain(e), "| ctx text has canary:", CAN in str(e.__context__))
    print("  format_exception has canary:", CAN in "".join(traceback.format_exception(e)))
srv = fm.FakeMongoServer(down_message=f"down {URI}")
cl = srv.client()
with fm.seams(client_factory=lambda u: cl):
    st = g.GuardedStore(URI)
srv.down = True
try: st.ping()
except Exception as e:
    print("ping:", type(e).__name__, "suppress", e.__suppress_context__, "context canary:", CAN in str(e.__context__), "format canary:", CAN in "".join(traceback.format_exception(e)))

print("== 2. non-PyMongoError exception: traceback frame locals hold the driver object")
srv = fm.FakeMongoServer(); cl = srv.client()
with fm.seams(client_factory=lambda u: cl): st = g.GuardedStore(URI)
col = st.collection("projects")
try: col.find({}, limit="abc")
except Exception as e:
    tb = e.__traceback__; found = []
    while tb:
        for k, v in list(tb.tb_frame.f_locals.items()):
            if type(v).__module__ in ("fake_mongo", "pymongo.synchronous.collection") or "Fake" in type(getattr(v, "__self__", v)).__name__:
                found.append((tb.tb_frame.f_code.co_name, k, type(getattr(v, "__self__", v)).__name__))
        tb = tb.tb_next
    print("exc:", type(e).__name__, "| driver-object locals in traceback frames:", found)
    # reach db handle and a foreign database through it
    tb = e.__traceback__
    while tb:
        c = tb.tb_frame.f_locals.get("call")
        if c is not None:
            raw = c.__self__
            print("  raw collection:", type(raw).__name__, "-> db:", raw._db.name, "server:", type(raw._db.server).__name__)
            break
        tb = tb.tb_next

print("== 3. introspection reach (expected accepted residuals)")
print("method __globals__ has _REGISTRY:", "_REGISTRY" in g.GuardedCollection.find.__globals__)
print("store.__dict__ keys:", sorted(st.__dict__), "| col.__dict__:", sorted(col.__dict__), "| bucket.__dict__:", sorted(st.bucket().__dict__))
print("col._store is st:", col._store is st)

print("== 4. copy / pickle / weakref / repr")
for label, fn in [("copy.copy(col)", lambda: copy.copy(col)), ("deepcopy(col)", lambda: copy.deepcopy(col)),
                  ("copy(st)", lambda: copy.copy(st)), ("deepcopy(st)", lambda: copy.deepcopy(st)),
                  ("pickle col", lambda: pickle.loads(pickle.dumps(col))), ("pickle st", lambda: pickle.loads(pickle.dumps(st)))]:
    try:
        o = fn()
        try:
            o.find({}) if hasattr(o, "find") else o.collection("projects")
            print(label, "-> usable?! ", type(o).__name__)
        except Exception as e:
            print(label, "-> copy exists, unusable:", type(e).__name__)
    except Exception as e:
        print(label, "->", type(e).__name__, str(e)[:60])
print("weakref.ref(col)() is col:", weakref.ref(col)() is col, "| getweakrefs:", len(weakref.getweakrefs(col)))
txt = repr(st) + repr(col) + str(st.bucket()) + repr(vars(st)) + repr(vars(col))
print("repr/vars contain canary:", CAN in txt, "| uri host:", "h.example" in txt)
print("store has URI anywhere in __dict__ values:", any(CAN in repr(v) for v in st.__dict__.values()))
print("== 5. frame locals of ctor failure hold uri (inherent)")
try:
    with fm.seams(client_factory=bad_factory): g.GuardedStore(URI)
except Exception as e:
    tb = e.__traceback__; seen = []
    while tb:
        if any(CAN in safe(v) for v in list(tb.tb_frame.f_locals.values())): seen.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    print("frames holding the URI in locals:", seen)
try: g.GuardedStore("mongodb://umesh:%s@[h/" % CAN)
except Exception as e:
    tb = e.__traceback__; seen = []
    while tb:
        if any(CAN in safe(v) for v in list(tb.tb_frame.f_locals.values())): seen.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    print("parse failure:", type(e).__name__, "frames holding URI:", seen, "chain:", chain(e))

from h import *
class Rec:
    """real-looking client, live=False (lies)"""
    def __init__(s, live=False):
        if not isinstance(type(s).__dict__.get('live'),property): s.live=live
        s.calls=[]; s.inner=FakeSheet(HEADER)
    def read(s,a,b): s.calls.append("read"); return s.inner.read(a,b)
    def append_row(s,a,b,c): s.calls.append("append"); s.inner.append_row(a,b,c)
    def update_cells(s,a,b,c,d): s.calls.append("update"); s.inner.update_cells(a,b,c,d)
class NoLive(Rec):
    def __init__(s): super().__init__(); del s.live
class PropLive(Rec):
    def __init__(s,v): super().__init__(); s._v=v
    @property
    def live(s): return s._v
class Flip(FakeSheet):
    def read(s,a,b):
        r=super().read(a,b); s.live=True; return r   # flips to live after planning read
bugs=[B(1)]
def go(label,c):
    p,_=dry_run(c,bugs,COLS,SyncMemory(),scrub) if not isinstance(c,Flip) else (plan_sync(bugs,SheetState(header=HEADER),COLS,SyncMemory(),scrub),None)
    cf=conf(p)
    try:
        write_confirmed_plan(c,bugs,COLS,SyncMemory(),scrub,cf); print(f"  [{label}] WROTE. calls={getattr(c,'calls',None)}")
    except Exception as e: print(f"  [{label}] {type(e).__name__}: {str(e)[:80]!r} calls={getattr(c,'calls',None)}")
banner("2 liar clients")
go("lying live=False class (not fake)", Rec())
go("honest live=True", Rec(True))
try: go("no live attr", NoLive())
except Exception as e: print("  [no live attr] outer", type(e).__name__, e)
for v in (1,"yes","False","",0,None): go(f"live property {v!r}", PropLive(v))
f=Flip(HEADER); 
p=plan_sync(bugs,SheetState(header=HEADER),COLS,SyncMemory(),scrub)
try: write_confirmed_plan(f,bugs,COLS,SyncMemory(),scrub,conf(p)); print("  [flip live during read] WROTE", f.write_calls)
except Exception as e: print("  [flip] ",type(e).__name__)
import inspect
print("isinstance Protocol runtime_checkable?", getattr(SheetClient,"_is_runtime_protocol",False))
src=inspect.getsource(write_confirmed_plan); print("structural checks (isinstance/registry) in write_confirmed_plan:", any(w in src for w in ("isinstance","registry","allow")))

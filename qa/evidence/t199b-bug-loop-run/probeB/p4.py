from h import *
banner("4a twice")
sh=FakeSheet(HEADER); mem=SyncMemory(); bs=[B(n) for n in range(1,6)]
p=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub); write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(p))
p2=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub); print("  second plan rows",len(p2.rows),"unchanged",p2.unchanged)
banner("4b crash after k appends (fail_after_writes=k means (k+1)th write call raises AFTER logging, BEFORE mutating)")
clean=FakeSheet(HEADER); m0=SyncMemory(); write_confirmed_plan(clean,bs,COLS,m0,scrub,conf(plan_sync(bs,clean.read("s","t"),COLS,m0,scrub)))
for k in range(0,6):
    sh=FakeSheet(HEADER,fail_after_writes=k); mem=SyncMemory()
    p=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub)
    try: write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(p))
    except ConnectionError: pass
    sh.fail_after_writes=None
    p2=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub); write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(p2))
    keys=[r[1] for r in sh.rows]
    p3=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub)
    print(f"  k={k}: rows after crash={k if k<5 else 5} final rows={len(sh.rows)} unique={len(set(keys))} equal clean={sh.rows==clean.rows} replan rows={len(p3.rows)} memory keys={len(mem.written)}")
banner("4c crash between write and memory update (simulate: client succeeds, memory dict lost)")
# emulate: write succeeded in sheet but memory not updated: use fresh SyncMemory on retry
for k in (1,3,5):
    sh=FakeSheet(HEADER); mem=SyncMemory()
    p=plan_sync(bs[:k],sh.read("s","t"),COLS,mem,scrub); write_confirmed_plan(sh,bs[:k],COLS,SyncMemory(),scrub,conf(p))  # memory discarded
    p2=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub)
    print(f"  k={k} memory lost: replan actions {[r.action for r in p2.rows]} unchanged {p2.unchanged}")
    write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(p2))
    # later change on a bug whose memory was lost
    bs2=[B(1,title="v2")]+bs[1:]
    p3=plan_sync(bs2,sh.read("s","t"),COLS,mem,scrub); print("    later change to bug1:",[(r.action,[c.column for c in r.conflicts]) for r in p3.rows], "rows total",len(sh.rows))
banner("4d crash in an UPDATE mid-plan; memory = what was written")
sh=FakeSheet(HEADER); mem=SyncMemory(); write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(plan_sync(bs,sh.read("s","t"),COLS,mem,scrub)))
bs2=[B(n,S.FIXED) for n in range(1,6)]
sh.fail_after_writes=len(sh.write_calls)+2
p=plan_sync(bs2,sh.read("s","t"),COLS,mem,scrub)
try: write_confirmed_plan(sh,bs2,COLS,mem,scrub,conf(p))
except ConnectionError: print("  crashed")
sh.fail_after_writes=None
p2=plan_sync(bs2,sh.read("s","t"),COLS,mem,scrub); print("  retry plan rows",len(p2.rows),[r.action for r in p2.rows])
write_confirmed_plan(sh,bs2,COLS,mem,scrub,conf(p2)); print("  statuses",[r[4] for r in sh.rows])
p3=plan_sync(bs2,sh.read("s","t"),COLS,mem,scrub); print("  replan empty:",p3.rows==[])
# crash on the mutating side: failing client that APPLIES write then raises (ack lost)
class Ack(FakeSheet):
    def append_row(s,a,b,c):
        super().append_row(a,b,c); raise TimeoutError("ack lost")
banner("4e ack lost: sheet row written but client raised -> memory not updated")
sh=Ack(HEADER); mem=SyncMemory()
p=plan_sync(bs[:2],sh.read("s","t"),COLS,mem,scrub)
try: write_confirmed_plan(sh,bs[:2],COLS,mem,scrub,conf(p))
except TimeoutError: pass
print("  rows",len(sh.rows),"mem",list(mem.written))
sh.__class__=FakeSheet
p2=plan_sync(bs[:2],sh.read("s","t"),COLS,mem,scrub); print("  retry plan:",[(r.action,r.bug_key[-2:]) for r in p2.rows],"unchanged",p2.unchanged)
write_confirmed_plan(sh,bs[:2],COLS,mem,scrub,conf(p2)); print("  keys",[r[1][-2:] for r in sh.rows])
bs2=[B(1,title="v2"),B(2)]; p3=plan_sync(bs2,sh.read("s","t"),COLS,mem,scrub); print("  later change to ack-lost bug1:",[(r.action,[c.column for c in r.conflicts]) for r in p3.rows])

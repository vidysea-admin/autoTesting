from h import *
import typing
banner("3a protocol attributes")
names=set()
for k in SheetClient.__mro__:
    names|={n for n in vars(k) if not n.startswith("__")}|set(getattr(k,"__annotations__",{}))
names={n for n in names if not n.startswith("_")}
print("  protocol names:", sorted(names)); print("  fake public:", sorted(n for n in dir(FakeSheet) if not n.startswith("_")))
def key(n): return B(n).bug_key
def rd(sh): return sh.rows
banner("3b duplicate bug-key rows")
sh=FakeSheet(HEADER,[["",key(1)],["",key(1)]]); p=plan_sync([B(1)],sh.read("s","t"),COLS,SyncMemory(),scrub); print("  ",[(r.action,r.note) for r in p.rows])
banner("3c key variants: trailing space / case / apostrophe / blank")
for lab,cell in [("trailing space",key(1)+"  "),("leading space"," "+key(1)),("upper",key(1).upper()),("leading apostrophe","'"+key(1)),("nbsp",key(1)+"\u00a0")]:
    sh=FakeSheet(HEADER,[["",cell]]); mem=SyncMemory(); p=plan_sync([B(1)],sh.read("s","t"),COLS,mem,scrub)
    print(f"  {lab!r}: actions {[ (r.action,r.row_number) for r in p.rows]}")
sh=FakeSheet(HEADER,[["",""],["","other_key"]]); p=plan_sync([B(1)],sh.read("s","t"),COLS,SyncMemory(),scrub); print("  blank key row + foreign key row: ",[(r.action,r.row_number) for r in p.rows])
banner("3d foreign key row is never touched")
sh=FakeSheet(HEADER,[["n","manual-row","Hand title","P0","open","ann","t"]]); snap=sh.snapshot()
_p=plan_sync([B(1)],sh.read("s","t"),COLS,SyncMemory(),scrub); write_confirmed_plan(sh,[B(1)],COLS,SyncMemory(),scrub,conf(_p)); print("  row0 unchanged:", sh.rows[0]==list(snap[1][0]), "n rows", len(sh.rows))
banner("3e unmapped bug_key column")
try: SheetColumns(sheet_id="s",tab="t",columns={"title":"Title"})
except Exception as e: print("  SheetColumns refuses:", str(e).splitlines()[1][:80])
banner("3f human edit between two syncs / never-written cell / deleted row / header reorder")
sh=FakeSheet(HEADER); mem=SyncMemory(); b1=[B(1)]
p=plan_sync(b1,sh.read("s","t"),COLS,mem,scrub); write_confirmed_plan(sh,b1,COLS,mem,scrub,conf(p))
sh.human_edit(2,"Severity","P0"); sh.human_edit(2,"Notes (human)","note"); sh.human_edit(2,"Assignee","carol")  # assignee mapped, we wrote ''
b2=[B(1,S.FIXED,assignee="dave")]
p=plan_sync(b2,sh.read("s","t"),COLS,mem,scrub); print(render_plan(p))
write_confirmed_plan(sh,b2,COLS,mem,scrub,conf(p)); print("  row now", sh.rows[0])
# repeated: conflict persistent
p=plan_sync(b2,sh.read("s","t"),COLS,mem,scrub); print("  next plan:",[(r.action,[c.column for c in r.conflicts]) for r in p.rows])
banner("3g row deleted by human")
sh=FakeSheet(HEADER); mem=SyncMemory(); bs=[B(1),B(2)]
p=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub); write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(p))
del sh.rows[0]; p=plan_sync(bs,sh.read("s","t"),COLS,mem,scrub); print("  actions after human deletes row of bug1:",[(r.action,r.bug_key[-2:]) for r in p.rows])
write_confirmed_plan(sh,bs,COLS,mem,scrub,conf(p)); print("  keys:",[r[1][-2:] for r in sh.rows], "(re-appended; memory-> would it conflict?)")
# After re-append with stale memory: append row cells vs memory; then change bug 1
sh.calls.clear(); p=plan_sync([B(1,title="t2"),B(2)],sh.read("s","t"),COLS,mem,scrub); print("  later change:",[(r.action,[c.column for c in r.conflicts]) for r in p.rows])
banner("3h header/column reorder between plan and write")
sh=FakeSheet(HEADER); p,_=dry_run(sh,bs,COLS,SyncMemory(),scrub); c=conf(p)
sh.header=["Key","Title","Severity","Status","Assignee","Owner's tag","Notes (human)"]
r=write_confirmed_plan(sh,bs,COLS,SyncMemory(),scrub,c); print("  wrote rows (by header name):", sh.rows)
banner("3i existing row but memory missing and sheet cell empty vs non-empty (fresh install)")
sh=FakeSheet(HEADER,[["",key(1),"Bug number 1","S2","open",""]]); p=plan_sync([B(1)],sh.read("s","t"),COLS,SyncMemory(),scrub); print("  matching row, no memory:",p.rows,"unchanged",p.unchanged)
banner("3j short rows (ragged) padded")
sh=FakeSheet(HEADER,[["",key(1)]]); p=plan_sync([B(1)],sh.read("s","t"),COLS,SyncMemory(),scrub); write_confirmed_plan(sh,[B(1)],COLS,SyncMemory(),scrub,conf(p)); print("  ",sh.rows)
banner("3k header with duplicate/blank/ no unmapped issue; header dup non-mapped")
sh=FakeSheet(["A","A","Key","Title"],[]); 
c2=SheetColumns(sheet_id="s",tab="t",columns={"bug_key":"Key","title":"Title"})
try: plan_sync([B(1)],sh.read("s","t"),c2,SyncMemory(),scrub)
except PlanRefused as e: print("  dup header refused (even unmapped dup):",e)
banner("3l closed bug not in sheet; closed bug in sheet gets status update")
sh=FakeSheet(HEADER); p=plan_sync([B(1,S.FIXED)],sh.read("s","t"),COLS,SyncMemory(),scrub); print("  ",p.rows,p.unchanged)

from h import *
banner("1a no confirmation")
sh = FakeSheet(HEADER); bugs=[B(1),B(2)]
tryw("None", lambda: write_confirmed_plan(sh,bugs,COLS,SyncMemory(),scrub,None)); print("  calls",sh.calls)
banner("1b one-cell sheet change since planning")
sh = FakeSheet(HEADER,[["", B(1).bug_key,"","","",""," "]]); plan,_ = dry_run(sh,bugs,COLS,SyncMemory(),scrub); c=conf(plan)
sh.human_edit(2,"Notes (human)","x")  # unmapped col: plan unaffected -> expected still valid
tryw("unmapped edit", lambda: write_confirmed_plan(sh,bugs,COLS,SyncMemory(),scrub,c)); print("  writes",sh.write_calls)
sh = FakeSheet(HEADER,[["", B(1).bug_key,"","","",""," "]]); plan,_ = dry_run(sh,bugs,COLS,SyncMemory(),scrub); c=conf(plan)
sh.human_edit(2,"Title","human"); 
tryw("mapped edit", lambda: write_confirmed_plan(sh,bugs,COLS,SyncMemory(),scrub,c)); print("  writes",sh.write_calls)
banner("1c P1 confirmation vs P2 (bug data one cell)")
sh = FakeSheet(HEADER); p1,_=dry_run(sh,[B(1)],COLS,SyncMemory(),scrub); c=conf(p1)
for lab,bs in [("title",[B(1,title="Bug number 1!")]),("severity",[B(1,severity=__import__('autotester.schema.enums',fromlist=['x']).Severity.S1)]),("extra bug",[B(1),B(2)]),("assignee",[B(1,assignee="bob")])]:
    tryw(lab, lambda: write_confirmed_plan(sh,bs,COLS,SyncMemory(),scrub,c))
print("  writes",sh.write_calls)
# fields not in mapping (screen, count) -> same plan hash legitimately
tryw("unmapped field (screen) changed", lambda: write_confirmed_plan(FakeSheet(HEADER),[B(1,screen="Z")],COLS,SyncMemory(),scrub,c))
banner("1d confirmer names")
for who in ["system:bug-loop","system-bug-loop","System","bug-loop","autotester","machine","bot"," ","   ","\t","umesh ","u","SYSTEM_actor","Systemic Jones","a\nb","user:umesh","service-account"]:
    try: PlanConfirmation(plan_hash="plan_x",confirmed_by=who,confirmed_at=NOW); print(f"  {who!r}: ACCEPTED")
    except Exception as e: print(f"  {who!r}: refused")
banner("1e forged/stale hash variants")
sh = FakeSheet(HEADER); p,_=dry_run(sh,bugs,COLS,SyncMemory(),scrub); print("  hash",p.plan_hash)
for lab,h in [("prefix",p.plan_hash[:8]),("upper",p.plan_hash.upper()),("lower",p.plan_hash.lower()),("trailing space",p.plan_hash+" "),("empty","")]:
    try:
        cc=PlanConfirmation(plan_hash=h,confirmed_by="umesh",confirmed_at=NOW)
    except Exception as e: print(f"  [{lab}] confirmation refused at construct"); continue
    tryw(lab, lambda: write_confirmed_plan(FakeSheet(HEADER),bugs,COLS,SyncMemory(),scrub,cc))
banner("1f self-hash")
d=p.model_dump(mode="json"); d["plan_hash"]="plan_deadbeef0000"
tryw("wrong hash", lambda: SheetPlan.model_validate(d))
d2=p.model_dump(mode="json"); d2["rows"][0]["changes"][0]["after"]="evil"
tryw("edited content stale hash", lambda: SheetPlan.model_validate(d2))
d3=dict(d2); d3["plan_hash"]=""
q=SheetPlan.model_validate(d3); print("  empty hash => recomputed", q.plan_hash!=p.plan_hash)
# mutate after construct
p.rows[0].changes[0].after="mutated"; print("  post-construct mutation keeps old hash:", p.plan_hash)
tryw("assign_hash attr", lambda: setattr(p,"plan_hash","plan_x"))
banner("1g re-use of confirmation after sync")
sh=FakeSheet(HEADER); mem=SyncMemory(); p,_=dry_run(sh,bugs,COLS,mem,scrub); c=conf(p)
write_confirmed_plan(sh,bugs,COLS,mem,scrub,c); n=len(sh.write_calls); print("  writes first",n)
tryw("reuse", lambda: write_confirmed_plan(sh,bugs,COLS,mem,scrub,c)); print("  writes after reuse",len(sh.write_calls), "rows",len(sh.rows))
# empty plan confirmation
p2,_=dry_run(sh,bugs,COLS,mem,scrub); print("  empty plan hash",p2.plan_hash,"rows",p2.rows)
tryw("confirm empty plan", lambda: write_confirmed_plan(sh,bugs,COLS,mem,scrub,conf(p2))); print("  writes",len(sh.write_calls))
# reuse with fresh memory (memory lost): sheet has rows, memory empty
sh=FakeSheet(HEADER); p,_=dry_run(sh,bugs,COLS,SyncMemory(),scrub); write_confirmed_plan(sh,bugs,COLS,SyncMemory(),scrub,conf(p))
n=len(sh.write_calls); p3,_=dry_run(sh,bugs,COLS,SyncMemory(),scrub); print("  memory lost: replan rows",len(p3.rows), "unchanged",p3.unchanged)
banner("1h changed sheet id / tab")
sh=FakeSheet(HEADER); p,_=dry_run(sh,bugs,COLS,SyncMemory(),scrub); c=conf(p)
cols2=SheetColumns(sheet_id="sheet_other",tab="Bugs",columns=COLS.columns)
tryw("sheet id", lambda: write_confirmed_plan(sh,bugs,cols2,SyncMemory(),scrub,c)); print("  writes",sh.write_calls)
cols3=SheetColumns(sheet_id="sheet_demo",tab="Other",columns=COLS.columns)
tryw("tab", lambda: write_confirmed_plan(sh,bugs,cols3,SyncMemory(),scrub,c)); print("  writes",sh.write_calls)
# column mapping changed to different header, same sheet/tab: hash covers column header names in changes
cols4=SheetColumns(sheet_id="sheet_demo",tab="Bugs",columns={**COLS.columns,"title":"Owner's tag"})
tryw("mapping change", lambda: write_confirmed_plan(sh,bugs,cols4,SyncMemory(),scrub,c)); print("  writes",sh.write_calls)
banner("1i written content vs confirmed plan, cell for cell")
sh=FakeSheet(HEADER,[["n",B(1).bug_key,"old","S2","open","", "t"]]); mem=SyncMemory(); mem.written[B(1).bug_key]={"Title":"old","Severity":"S2","Status":"open"}
bs=[B(1,title="new title"),B(2),B(3,S.FIXED)]
p,_=dry_run(sh,bs,COLS,mem,scrub); c=conf(p); sh.calls.clear()
w=write_confirmed_plan(sh,bs,COLS,mem,scrub,c)
exp=[("append_row","sheet_demo","Bugs",r.cells) if r.row_number is None else ("update_cells","sheet_demo","Bugs",r.row_number,r.cells) for r in p.writes]
got=[c_ for c_ in sh.calls if c_[0]!="read"]
print("  identical:", exp==got); print("  calls:",sh.calls)

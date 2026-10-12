import sys, tempfile
from pathlib import Path
W = Path(sys.argv[1]); sys.path.insert(0, str(W/"copy"/"tests"))
import autotester; print("autotester:", autotester.__file__)
from bug_run_fixture import make_store, add_case, verdict, finished_run, set_criteria
from bug_loop_fixture import at, PROJECT
from autotester.schema.enums import Result
from autotester.store.bug_store import BugStore
from autotester.stages.bug_run import process_run

def state(b): return {k[-4:]:(v.status.value, v.count, v.pass_streak, v.last_seen.minute) for k,v in b.bugs().items()}
def mk():
    d = Path(tempfile.mkdtemp(dir=W/"probeM")); return d, make_store(d/"p"), BugStore(d/"bugs", clock=lambda: at(10_000))
def run(st,bs,rid,m,vs,cases):
    finished_run(st,rid,m,vs,cases); return process_run(st,bs,rid)
R={}
CR2=(("C1","Pay button submits the order"),("C2","Receipt is shown"))
# A deleted case -> stale (two cases so list nonempty)
d,st,bs=mk(); a=add_case(st,"flowA"); b=add_case(st,"flowB")
run(st,bs,"r1",1,[verdict(a,"r1",Result.FAIL),verdict(b,"r1",Result.PASS)],[a,b])
assert st.delete_case(a.id) is True or True
run(st,bs,"r2",2,[verdict(b,"r2",Result.PASS)],[b]); R["A deleted case"]=state(bs)
# only the deleted case's bug is stale; B has no bug. Add bug on B untouched:
# B untouched stays open
d,st,bs=mk(); a=add_case(st,"flowA"); b=add_case(st,"flowB")
run(st,bs,"r1",1,[verdict(a,"r1",Result.FAIL),verdict(b,"r1",Result.FAIL)],[a,b])
st.delete_case(a.id); run(st,bs,"r2",2,[verdict(b,"r2",Result.FAIL)],[b])
R["A2 untouched case stays open, deleted stale"]={("A" if k.endswith(bs.bugs()[k].bug_key[-4:]) and bs.bugs()[k].case_id==a.id else "B"):(v.status.value,v.count) for k,v in bs.bugs().items()}
# B removed criterion
d,st,bs=mk(); c=add_case(st,criteria=CR2)
run(st,bs,"r1",1,[verdict(c,"r1",Result.FAIL,failing=("C1","C2"),total=2)],[c])
set_criteria(st,c,(("C2","Receipt is shown"),)); run(st,bs,"r2",2,[verdict(c,"r2",Result.PASS,total=1)],[c])
R["B removed C1 (C2 untouched)"]={ (v.criterion_id):(v.status.value,v.count) for v in bs.bugs().values()}
# C edited text
d,st,bs=mk(); c=add_case(st,criteria=CR2)
run(st,bs,"r1",1,[verdict(c,"r1",Result.FAIL,failing=("C1","C2"),total=2)],[c])
set_criteria(st,c,(("C1","Pay button submits the order quickly"),("C2","Receipt is shown"))); 
run(st,bs,"r2",2,[verdict(c,"r2",Result.PASS,total=2)],[c]); run(st,bs,"r3",3,[verdict(c,"r3",Result.PASS,total=2)],[c])
R["C edited C1 text; 2 PASS after"]={v.criterion_id:(v.status.value,v.count,v.pass_streak) for v in bs.bugs().values()}
# D reordered
d,st,bs=mk(); c=add_case(st,criteria=CR2)
run(st,bs,"r1",1,[verdict(c,"r1",Result.FAIL,failing=("C1","C2"),total=2)],[c])
set_criteria(st,c,tuple(reversed(CR2))); r=run(st,bs,"r2",2,[verdict(c,"r2",Result.PASS,total=2)],[c]); run(st,bs,"r3",3,[verdict(c,"r3",Result.PASS,total=2)],[c])
R["D reordered"]={v.criterion_id:(v.status.value,v.count) for v in bs.bugs().values()}
# E renamed title (same id) vs steps change
d,st,bs=mk(); c=add_case(st)
run(st,bs,"r1",1,[verdict(c,"r1",Result.FAIL)],[c])
c2=c.model_copy(update={"title":"renamed"}); st.update_case(c2); run(st,bs,"r2",2,[verdict(c2,"r2",Result.PASS)],[c2])
R["E title renamed, id same"]={v.criterion_id:(v.status.value,v.count,v.pass_streak) for v in bs.bugs().values()}
# F fixed bug not swept; case deleted
d,st,bs=mk(); a=add_case(st,"flowA"); b=add_case(st,"flowB")
run(st,bs,"r1",1,[verdict(a,"r1",Result.FAIL),verdict(b,"r1",Result.PASS)],[a,b])
run(st,bs,"r2",2,[verdict(a,"r2",Result.PASS)],[a]); run(st,bs,"r3",3,[verdict(a,"r3",Result.PASS)],[a])
before=state(bs); st.delete_case(a.id); rep=run(st,bs,"r4",4,[verdict(b,"r4",Result.PASS)],[b])
R["F fixed bug, case deleted"]=(before,state(bs),rep.case_changed)
# G empty case list not mass deletion
d,st,bs=mk(); a=add_case(st,"flowA"); 
run(st,bs,"r1",1,[verdict(a,"r1",Result.FAIL)],[a])
st.delete_case(a.id); assert st.list_cases()==[]
from autotester.schema.run import Run
st.save_run(Run(id="r2",project=PROJECT,case_ids=[],finished_at=at(2))); rep=process_run(st,bs,"r2")
R["G empty case list"]=(state(bs),rep.unverifiable,rep.case_changed)
# H pinned case: close bug; case still exists and delete refuses
d,st,bs=mk(); p=add_case(st,"flowP",pinned=True)
run(st,bs,"r1",1,[verdict(p,"r1",Result.FAIL)],[p]); run(st,bs,"r2",2,[verdict(p,"r2",Result.PASS)],[p]); run(st,bs,"r3",3,[verdict(p,"r3",Result.PASS)],[p])
try: ok=st.delete_case(p.id)
except Exception as e: ok="raised "+type(e).__name__
R["H pinned: fixed, delete_case"]=(state(bs), ok, st.has_case(p.id))
# I same-instant: PASS streak 1 then edit then PASS (would close) -> stale not fixed
d,st,bs=mk(); c=add_case(st)
run(st,bs,"r1",1,[verdict(c,"r1",Result.FAIL)],[c]); run(st,bs,"r2",2,[verdict(c,"r2",Result.PASS)],[c])
set_criteria(st,c,(("C1","Pay button submits the order, always"),)); rep=run(st,bs,"r3",3,[verdict(c,"r3",Result.PASS)],[c])
R["I edit between PASS 1 and PASS 2"]=(state(bs),rep.refused)
# J new FAIL on stale key
rep=run(st,bs,"r4",4,[verdict(c,"r4",Result.FAIL)],[c]); R["J new FAIL on stale key"]=(state(bs),rep.refused)
# K replay older run after the case change
d,st,bs=mk(); c=add_case(st)
run(st,bs,"r1",1,[verdict(c,"r1",Result.FAIL)],[c]); run(st,bs,"r2",2,[verdict(c,"r2",Result.FAIL)],[c])
set_criteria(st,c,(("C1","Pay button submits the order, always"),)); run(st,bs,"r3",3,[verdict(c,"r3",Result.PASS)],[c])
s1=state(bs); rep=process_run(st,bs,"r1"); s2=state(bs); rep2=process_run(st,bs,"r2"); s3=state(bs)
R["K replay r1 after case change"]=(s1,s2,s3,rep.case_changed,rep.duplicate)
for k,v in R.items(): print(k,"=>",v)

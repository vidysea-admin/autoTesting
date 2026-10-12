import sys, tempfile, json, shutil
from pathlib import Path
W = Path(sys.argv[1]); sys.path.insert(0, str(W/"copy"/"tests"))
import autotester; print("autotester:", autotester.__file__)
from bug_run_fixture import make_store, add_case, verdict, finished_run, set_criteria
from bug_loop_fixture import at, PROJECT
from autotester.schema.enums import Result, Outcome
from autotester.schema.run import RawResult, Run
from autotester.store.bug_store import BugStore
from autotester.stages.bug_run import process_run
import hashlib

def state(b): return {k:(v.status.value, v.count, v.pass_streak, v.closed_by_runs, v.closed_by_verdicts) for k,v in b.bugs().items()}
def mk():
    d = Path(tempfile.mkdtemp(dir=W/"probeM")); st = make_store(d/"p"); bs = BugStore(d/"bugs", clock=lambda: at(10_000)); return d, st, bs
res = {}

# S1 raw only
d, st, bs = mk(); c = add_case(st)
st.save_result("r1", RawResult(case_id=c.id, outcome=Outcome.ASSERTION_FAILED, error="boom"))
st.save_run(Run(id="r1", project=PROJECT, case_ids=[c.id], finished_at=at(1)))
rep = process_run(st, bs, "r1"); res["S1 raw-only"] = (state(bs), rep.no_verdict_cases, rep.events_built)
# S2 replayed with verdict FAIL (same dir shape)
finished_run(st, "r2", 2, [verdict(c, "r2", Result.FAIL)], [c])
rep = process_run(st, bs, "r2"); res["S2 FAIL verdict"] = (state(bs), rep.applied)
# S3 PASS without evidence x3: images_requested>seen ; met<total ; total 0
for i,(nm,v) in enumerate([("partial-img", verdict(c,"r3",Result.PASS,images=(2,0))),
                           ("met<total", verdict(c,"r4",Result.PASS,met=0,total=1)),
                           ("total=0", verdict(c,"r5",Result.PASS,met=0,total=0))]):
    rid=f"r{3+i}"; v=v.model_copy(update={"run_id":rid}); finished_run(st, rid, 3+i, [v], [c]); rep=process_run(st,bs,rid)
    res[f"S3 unevidenced PASS {nm}"] = (state(bs), rep.unjudged_cases)
# one proven PASS then second proven PASS -> fixed (N=2)
finished_run(st,"r6",6,[verdict(c,"r6",Result.PASS)],[c]); process_run(st,bs,"r6"); res["S3b one proven PASS"]=state(bs)
finished_run(st,"r7",7,[verdict(c,"r7",Result.PASS)],[c]); process_run(st,bs,"r7"); res["S3c two proven PASS"]=state(bs)
# S4 FAIL citing none
d, st, bs = mk(); c = add_case(st)
v = verdict(c,"r1",Result.FAIL).model_copy(update={"failures":[]}); finished_run(st,"r1",1,[v],[c]); rep=process_run(st,bs,"r1")
res["S4 FAIL citing none"]=(state(bs), rep.unjudged_cases, rep.events_built)
# S5 FAIL naming missing criterion / missing case
v = verdict(c,"r2",Result.FAIL,failing=("C9",)); finished_run(st,"r2",2,[v],[c]); rep=process_run(st,bs,"r2")
res["S5a FAIL missing criterion"]=(state(bs), rep.unresolved_failures)
v = verdict(c,"r3",Result.FAIL).model_copy(update={"case_id":"case_zzzzzzzzzzzz"}); 
st.save_verdict("r3", v); st.save_run(Run(id="r3", project=PROJECT, case_ids=[c.id], finished_at=at(3))); rep=process_run(st,bs,"r3")
res["S5b FAIL missing case"]=(state(bs), rep.unresolved_failures)
# S6 mixed
d, st, bs = mk(); a=add_case(st,"flowA"); b=add_case(st,"flowB"); cc=add_case(st,"flowC"); dd=add_case(st,"flowD")
vs=[verdict(a,"r1",Result.FAIL), verdict(b,"r1",Result.PASS), verdict(cc,"r1",Result.INCONCLUSIVE), verdict(dd,"r1",Result.BLOCKED)]
finished_run(st,"r1",1,vs,[a,b,cc,dd]); rep=process_run(st,bs,"r1")
res["S6 mixed"]=(state(bs), rep.applied, rep.unjudged_cases, rep.verdicts)
# S7 empty case list
d, st, bs = mk(); st.save_run(Run(id="r1", project=PROJECT, case_ids=[], finished_at=at(1))); rep=process_run(st,bs,"r1")
res["S7a empty run"]=(rep.outcome.value, state(bs), rep.events_built)
# S8 corrupt rubric
d, st, bs = mk(); c=add_case(st); finished_run(st,"r1",1,[verdict(c,"r1",Result.FAIL)],[c]); process_run(st,bs,"r1")
(st.paths.rubrics_dir/f"{c.rubric_ref}.json").write_text("{not json",encoding="utf-8")
finished_run(st,"r2",2,[verdict(c,"r2",Result.FAIL)],[c])
try:
    rep=process_run(st,bs,"r2"); res["S8 corrupt rubric"]=(state(bs), rep.unverifiable, rep.unresolved_failures, rep.case_changed)
except Exception as e: res["S8 corrupt rubric"]="RAISED "+repr(e)[:150]
# S9 run dir problems
d, st, bs = mk(); c=add_case(st)
res["S9a no run dir"]=process_run(st,bs,"nope").outcome.value
rd=st.paths.run_dir("r1"); rd.mkdir(parents=True,exist_ok=True); (rd/"x.verdict.json").write_text(verdict(c,"r1",Result.FAIL).model_dump_json())
res["S9b verdicts but no run.json"]=(process_run(st,bs,"r1").outcome.value, state(bs))
st.save_run(Run(id="r1", project=PROJECT, case_ids=[c.id], finished_at=at(1)))
(rd/"y.verdict.json").write_text("{torn")
try: rep=process_run(st,bs,"r1"); res["S9c corrupt verdict file"]=(rep.outcome.value,state(bs))
except Exception as e: res["S9c corrupt verdict file"]="RAISED "+type(e).__name__+": "+str(e)[:120]
(rd/"y.verdict.json").unlink()
(rd/"run.json").write_text("{torn")
try: rep=process_run(st,bs,"r1"); res["S9d corrupt run.json"]=rep.outcome.value
except Exception as e: res["S9d corrupt run.json"]="RAISED "+type(e).__name__+": "+str(e)[:120]
# wrong project
st.save_run(Run(id="r1", project="other", case_ids=[c.id], finished_at=at(1))); res["S9e wrong project"]=process_run(st,bs,"r1").outcome.value
# run with no finished_at -> created_at
st.save_run(Run(id="r2", project=PROJECT, case_ids=[c.id])); st.save_verdict("r2", verdict(c,"r2",Result.FAIL)); 
rp=st.load_run("r2"); bs2=BugStore(d/"bugs2", clock=lambda: rp.created_at); process_run(st,bs2,"r2"); res["S9f no finished_at uses created_at"]=[e.at.isoformat() for e in bs2.events()]==[rp.created_at.isoformat()]
for k,v in res.items(): print(k,"=>",v)

import sys, tempfile
from pathlib import Path
W = Path(sys.argv[1]); sys.path.insert(0, str(W/"copy"/"tests"))
from bug_run_fixture import make_store, add_case, verdict, finished_run, set_criteria
from bug_loop_fixture import at
from autotester.schema.enums import Result
from autotester.store.bug_store import BugStore
from autotester.stages.bug_run import process_run
d=Path(tempfile.mkdtemp(dir=W/"probeM")); st=make_store(d/"p"); bs=BugStore(d/"bugs", clock=lambda: at(10_000)); c=add_case(st)
def st_(): return [(v.status.value,v.count,v.last_seen.minute) for v in bs.bugs().values()]
for i in (1,2): finished_run(st,f"r{i}",i,[verdict(c,f"r{i}",Result.FAIL)],[c]); process_run(st,bs,f"r{i}")
print("before edit:", st_())
set_criteria(st,c,(("C1","Pay button submits the order, always"),))
rep=process_run(st,bs,"r1")      # a retry / replay of the OLD run r1 after the criterion moved
print("after replaying r1:", st_(), "case_changed:", rep.case_changed)
print([ (e.kind.value,e.at.minute,e.ref[:30]) for e in bs.events()])
rep=process_run(st,bs,"r2"); print("after replaying r2 too:", st_(), rep.refused)

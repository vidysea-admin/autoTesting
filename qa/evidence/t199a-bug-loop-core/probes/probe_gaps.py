import sys
sys.path.insert(0, r"C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/ck199a/tests")
from bug_loop_fixture import KEY, event, seed, CASE, at
from autotester.schema.enums import Result
from autotester.schema.tracked_bug import EventKind as K, BugEvent, SYSTEM_ACTOR
from autotester.schema.verdict import Verdict
from autotester.stages.bug_loop import fold, kind_of_verdict
# G6: graded FAIL with no cited failure -> inconclusive, so it does not break a pass streak
v = Verdict(run_id="r3", case_id=CASE, result=Result.FAIL, criteria_met=1, criteria_total=3)
k = kind_of_verdict(v); print("graded FAIL, no cited failure ->", k.value)
evs = [event(K.FAIL, 1), event(K.PASS, 2)]
if k is not K.INCONCLUSIVE: evs.append(event(k, 3))
evs.append(event(K.PASS, 4))
print("F, P, (FAIL-uncited between), P ->", fold(evs)[KEY].status.value, "<- contract: consecutive only if no FAIL falls between")
# G2: stale then real FAIL
evs = [event(K.FAIL, 1), event(K.CASE_CHANGED, 2, with_seed=False), event(K.FAIL, 3)]
b = fold(evs)[KEY]; print("stale then FAIL ->", b.status.value, "count", b.count, "(FAIL not tracked)")
from autotester.stages.bug_loop import trace
_, ap = trace(evs); print({e.kind.value: ap[e.event_id].effect.value + ":" + str(ap[e.event_id].reason) for e in evs})
# G8: N changed moves a reported fixed
evs = [event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)]
print("N=2 ->", fold(evs, close_passes=2)[KEY].status.value, "| N=3 ->", fold(evs, close_passes=3)[KEY].status.value)
# G10: same ref, different kind = two events, both counted
a = event(K.FAIL, 1); b2 = event(K.FAIL, 1, ref=a.ref); c = event(K.PASS, 1, ref=a.ref)
print("same ref FAIL then PASS: ids differ", a.event_id != c.event_id)
# G9: actor is a free string - anyone may claim the machine actor
e = BugEvent(bug_key=KEY, kind=K.FAIL, ref="x", at=at(1), actor="system:bug-loop", seed=seed())
print("any caller can set actor=system:bug-loop ->", e.actor)
e = BugEvent(bug_key=KEY, kind=K.ASSIGN, ref="a", at=at(1), actor="system:other", assignee="x")
from autotester.stages.bug_loop import storable
print("assign by system:other ->", storable(e))

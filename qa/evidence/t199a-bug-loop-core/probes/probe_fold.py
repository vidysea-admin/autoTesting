"""Checker probe (not part of the repo): attacks the fold, written independently of the builder tests."""
import itertools
import random
import sys
from datetime import timedelta, timezone

sys.path.insert(0, r"C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/ck199a/tests")
import autotester

print("autotester at", autotester.__file__)
from bug_loop_fixture import KEY, at, bug, event

from autotester.schema.enums import Result
from autotester.schema.tracked_bug import BugEvent
from autotester.schema.tracked_bug import BugStatus as S
from autotester.schema.tracked_bug import EventKind as K
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.bug_loop import Effect, fold, judge, kind_of_verdict, trace


def dump(bugs):
    return {k: v.model_dump_json() for k, v in sorted(bugs.items())}


bad = 0


def check(name, cond, extra=""):
    global bad
    print(("OK   " if cond else "FAIL ") + name, extra)
    bad += (not cond)


UNJ = (K.PASS_UNEVIDENCED, K.INCONCLUSIVE, K.BLOCKED, K.NOT_RUN, K.NO_VERDICT)
LIVE = (S.OPEN, S.REOPENED)
cells = 0
for st in [None, S.OPEN, S.REOPENED, S.FIXED, S.STALE]:
    for k in K:
        b = None if st is None else bug(st, streak=1 if st in LIVE else 0)
        ev = event(k, 20, minutes=20, assignee="Priya" if k is K.ASSIGN else None)
        r = judge(b, ev, close_passes=2)
        cells += 1
        tag = f"{st.value if st else 'none'}/{k.value}"
        if k in UNJ:
            check(f"unjudged {tag} unchanged", r.effect is Effect.UNCHANGED and r.bug == b)
        elif k is K.FAIL and st is None:
            check("none/fail opens", r.bug.status is S.OPEN and r.bug.count == 1 and r.bug.first_seen == at(20))
        elif k is K.FAIL and st in LIVE:
            check(f"{tag} count+1 last_seen first_seen kept streak reset",
                  r.bug.count == 3 and r.bug.last_seen == at(20) and r.bug.first_seen == at(0)
                  and r.bug.pass_streak == 0 and r.bug.status is st)
        elif k is K.FAIL and st is S.FIXED:
            check(f"{tag} reopened count kept+1", r.bug.status is S.REOPENED and r.bug.count == 3)
        elif k is K.PASS and st in LIVE:
            check(f"{tag} streak1->fixed(N=2), lists", r.bug.status is S.FIXED
                  and r.bug.closed_by_runs == ["s0", "run20"] and len(r.bug.closed_by_verdicts) == 2)
        elif k is K.PASS and st is S.FIXED:
            check(f"{tag} unchanged", r.effect is Effect.UNCHANGED)
        elif k is K.CASE_CHANGED and st in LIVE:
            check(f"{tag} stale", r.bug.status is S.STALE)
        elif k is K.ASSIGN and st is not None:
            check(f"{tag} assign", r.bug.assignee == "Priya" and r.bug.status is st)
        else:
            check(f"{tag} refused", r.effect is Effect.REFUSED, str(r.reason))
print("cells", cells)

f = fold([event(K.FAIL, 1), event(K.PASS, 2)])
check("one PASS keeps open", f[KEY].status is S.OPEN and f[KEY].pass_streak == 1)
check("two PASS fixed", fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)])[KEY].status is S.FIXED)
for n in (1, 3, 5):
    evs = [event(K.FAIL, 1)] + [event(K.PASS, 1 + i) for i in range(1, n + 1)]
    if n > 1:
        check(f"N={n} not closed at N-1", fold(evs[:-1], close_passes=n)[KEY].status is not S.FIXED)
    check(f"N={n} closes at N", fold(evs, close_passes=n)[KEY].status is S.FIXED)
f = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.FAIL, 3), event(K.PASS, 4)])
check("FAIL between passes: not fixed", f[KEY].status is S.OPEN and f[KEY].count == 2)
f = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.INCONCLUSIVE, 3, with_seed=False),
          event(K.BLOCKED, 3), event(K.NOT_RUN, 4), event(K.PASS, 5)])
check("unjudged between passes neither breaks nor closes alone", f[KEY].status is S.FIXED)
f = fold([event(K.FAIL, 1)] + [event(K.PASS_UNEVIDENCED, n) for n in range(2, 12)]
         + [event(K.INCONCLUSIVE, 20), event(K.BLOCKED, 21), event(K.NOT_RUN, 22), event(K.NO_VERDICT, 23)])
check("unevidenced/inconclusive/blocked/not_run never close", f[KEY].status is S.OPEN and f[KEY].pass_streak == 0)
f = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3)] + [event(K.INCONCLUSIVE, n) for n in range(4, 9)]
         + [event(K.BLOCKED, 9), event(K.NOT_RUN, 10)])
check("unjudged never reopens a fixed bug", f[KEY].status is S.FIXED)
evs = [event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.FAIL, 4), event(K.PASS, 5), event(K.PASS, 6)]
f = fold(evs[:4])[KEY]
check("fixed->fail reopened count 2 lists cleared", f.status is S.REOPENED and f.count == 2 and f.closed_by_runs == [])
f = fold(evs)[KEY]
check("re-closed with the new run lists", f.status is S.FIXED and f.closed_by_runs == ["run5", "run6"] and f.count == 2)

hist = [event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 3), event(K.FAIL, 4), event(K.PASS, 5),
        event(K.PASS, 6), event(K.ASSIGN, 7, assignee="Priya")]
seen = set()
for p in itertools.permutations(hist):
    seen.add(tuple(sorted(dump(fold(list(p))).items())))
check("7 events, all 5040 permutations -> 1 result", len(seen) == 1, fold(hist)[KEY].status.value)
hist2 = hist + [event(K.INCONCLUSIVE, 8, with_seed=False), event(K.CASE_CHANGED, 9, with_seed=False)]
seen = set()
rnd = random.Random(7)
for _ in range(800):
    p = hist2[:]
    rnd.shuffle(p)
    seen.add(tuple(sorted(dump(fold(p)).items())))
check("9 events, 800 shuffles -> 1 result", len(seen) == 1, fold(hist2)[KEY].status.value)

tied = [event(K.FAIL, 1, minutes=5), event(K.PASS, 2, minutes=5), event(K.PASS, 3, minutes=5),
        event(K.FAIL, 4, minutes=5), event(K.PASS, 5, minutes=6), event(K.ASSIGN, 6, minutes=5, assignee="A"),
        event(K.CASE_CHANGED, 7, minutes=6, with_seed=False)]
seen = set()
for p in itertools.permutations(tied):
    seen.add(tuple(sorted(dump(fold(list(p))).items())))
ft = fold(tied)[KEY]
check("equal timestamps, 5040 perms -> 1 result", len(seen) == 1, f"{ft.status.value} count={ft.count}")
a = event(K.FAIL, 1, minutes=0)
b = event(K.PASS, 2, minutes=0)
b2 = b.model_copy(update={"at": b.at.astimezone(timezone(timedelta(hours=5, minutes=30)))})
check("same instant in another tz offset, order independent", dump(fold([a, b2])) == dump(fold([b2, a])))

fut = event(K.FAIL, 1, minutes=60 * 24 * 365 * 70)
f = fold([event(K.FAIL, 1, minutes=0), event(K.PASS, 2, minutes=1), event(K.PASS, 3, minutes=2), fut])[KEY]
print("INFO future-dated FAIL (year ~2096) after a close ->", f.status.value, "count", f.count)
f = fold([event(K.FAIL, 1, minutes=0), fut, event(K.PASS, 2, minutes=1), event(K.PASS, 3, minutes=2)])[KEY]
print("INFO same set, future FAIL blocks close ->", f.status.value)
pre = fold([event(K.PASS, 1, minutes=-10), event(K.PASS, 2, minutes=-9), event(K.FAIL, 3, minutes=0)])[KEY]
check("PASS dated before the bug opened cannot close it", pre.status is S.OPEN and pre.pass_streak == 0)
lof = fold([event(K.FAIL, 1, minutes=10), event(K.PASS, 2, minutes=11), event(K.PASS, 3, minutes=12),
            event(K.FAIL, 9, minutes=5)])[KEY]
check("an OLD fail arriving late does not reopen a later close", lof.status is S.FIXED and lof.count == 2,
      f"first_seen={lof.first_seen}")

d = [event(K.FAIL, 1), event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 2), event(K.PASS, 3), event(K.PASS, 3)]
f = fold(d)[KEY]
check("duplicate events counted once", f.count == 1 and f.status is S.FIXED)
f = fold([event(K.FAIL, 1), event(K.PASS, 2), event(K.PASS, 2)])[KEY]
check("same PASS twice does not close", f.status is S.OPEN and f.pass_streak == 1)
e1 = event(K.PASS, 2)
e2 = e1.model_copy(update={"at": at(50), "run_id": "other"})
print("INFO same event_id for same (bug,ref,kind) but different at/run:", e1.event_id == e2.event_id)


def V(result, met, total, req=0, seen_=0, fails=()):
    return Verdict(run_id="r", case_id="c", result=result, criteria_met=met, criteria_total=total,
                   images_requested=req, images_seen=seen_, failures=list(fails))


check("None -> no_verdict", kind_of_verdict(None) is K.NO_VERDICT)
check("PASS all met -> pass", kind_of_verdict(V(Result.PASS, 3, 3)) is K.PASS)
check("PASS total 0 -> unevidenced", kind_of_verdict(V(Result.PASS, 0, 0)) is K.PASS_UNEVIDENCED)
check("PASS 2/3 -> unevidenced", kind_of_verdict(V(Result.PASS, 2, 3)) is K.PASS_UNEVIDENCED)
check("PASS 3 imgs asked 1 seen -> unevidenced", kind_of_verdict(V(Result.PASS, 3, 3, 3, 1)) is K.PASS_UNEVIDENCED)
check("INCONCLUSIVE -> inconclusive", kind_of_verdict(V(Result.INCONCLUSIVE, 0, 0)) is K.INCONCLUSIVE)
check("BLOCKED -> blocked", kind_of_verdict(V(Result.BLOCKED, 0, 0)) is K.BLOCKED)
check("FAIL with no cited failure -> inconclusive", kind_of_verdict(V(Result.FAIL, 1, 3)) is K.INCONCLUSIVE)
print("BAD", bad)

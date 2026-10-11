import sys
sys.path.insert(0, r"C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/ck199a/tests")
from bug_loop_fixture import KEY, event
from autotester.schema.tracked_bug import EventKind as K
from autotester.stages.bug_loop import fold
fut = event(K.FAIL, 9, minutes=60*24*365*70)
base = [event(K.FAIL, 1, minutes=0), event(K.PASS, 2, minutes=1), event(K.PASS, 3, minutes=2)]
f = fold(base + [fut])[KEY]; print("future FAIL after close ->", f.status.value, f.count, f.last_seen.year)
futp = [event(K.PASS, 7, minutes=60*24*365*70), event(K.PASS, 8, minutes=60*24*365*70+1)]
f = fold([event(K.FAIL, 1, minutes=0)] + futp)[KEY]; print("two future PASS close ->", f.status.value)
f = fold(base + futp + [event(K.FAIL, 5, minutes=10)])[KEY]; print("close,then real FAIL today, future PASSes ->", f.status.value, f.count)

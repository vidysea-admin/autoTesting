import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from atk2 import mk
from autotester.stages import schedule_store as ss
base = Path(sys.argv[1]); mode = sys.argv[2]; k = int(sys.argv[3])
claims = base/"claims"; rec = base/"records"/"victim.jsonl"
for i in range(2):
    key,c,r = mk("victim", i); ss.claim(claims, key, c)
ss.append_record(rec, mk("victim",0)[2])
real = os.replace; calls = {"n": 0}
def die(): os._exit(7)
def wrapper(src, dst):
    calls["n"] += 1; n = calls["n"]
    if mode == "crash" and n == k: die()
    if mode == "interrupt" and n == k: raise KeyboardInterrupt()
    if mode == "sysexit" and n == k: raise SystemExit(3)
    if mode == "fail3_crash_rollback" and n == 3: raise PermissionError("held")
    if mode == "fail3_crash_rollback" and n == k: die()
    if mode == "fail3_rollbackfail" and n == 3: raise PermissionError("held")
    if mode == "fail3_rollbackfail" and n == k: raise PermissionError("rollback held")
    if mode == "fail2_rollbackfail" and n == 2: raise PermissionError("held")
    if mode == "fail2_rollbackfail" and n == k: raise PermissionError("rollback held")
    return real(src, dst)
ss.os.replace = wrapper
if mode in ("crash_rmtree", "fail3_crash_rmtree"):
    def rm(*a, **kw): die()
    ss.shutil.rmtree = rm
    if mode == "fail3_crash_rmtree":
        def w2(src, dst):
            calls["n"] += 1
            if calls["n"] == 3: raise PermissionError("held")
            return real(src, dst)
        ss.os.replace = w2
try:
    ss.purge_project(claims, rec, "victim")
    print("child: purge returned normally")
except BaseException as e:
    print("child: escaped", type(e).__name__, isinstance(e, OSError))

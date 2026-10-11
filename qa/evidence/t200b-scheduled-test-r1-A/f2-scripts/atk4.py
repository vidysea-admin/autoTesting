import sys, subprocess, tempfile, shutil, os
from pathlib import Path
from autotester.stages.schedule_store import purge_project, list_claims
def tree(base):
    return sorted(str(p.relative_to(base)).replace("\\","/") for p in Path(base).rglob("*") if p.is_file())
def stage_state(base):
    return {d.name[:10]+"..": sorted(x.name for x in d.iterdir()) for d in base.glob(".purge-*")}
scen = [("crash",1,"crash before 1st move"),("crash",2,"crash before 2nd move"),("crash",3,"crash before LAST (3rd) move"),
        ("crash_rmtree",0,"crash just before rmtree (all moved)"),
        ("interrupt",2,"KeyboardInterrupt at 2nd move (no hard crash)"),("sysexit",2,"SystemExit at 2nd move"),
        ("fail3_crash_rollback",4,"3rd move fails, crash at 1st rollback move"),("fail3_crash_rollback",5,"3rd move fails, crash at 2nd rollback move"),
        ("fail3_crash_rmtree",0,"3rd move fails, rollback done, crash before rmtree"),
        ("fail3_rollbackfail",4,"3rd move fails, 1st rollback move fails (OSError)"),("fail3_rollbackfail",5,"3rd move fails, 2nd rollback move fails"),
        ("fail2_rollbackfail",3,"2nd move fails, rollback (of 1) fails")]
root = Path(sys.argv[1]); child = str(Path(__file__).parent/"atk4_child.py")
for mode,k,label in [s for s in scen if s[0] in ("interrupt","sysexit","fail3_rollbackfail","fail2_rollbackfail")]:
    b = Path(tempfile.mkdtemp(prefix="atk4-", dir=root))
    r = subprocess.run([sys.executable, child, str(b), mode, str(k)], capture_output=True, text=True, timeout=200)
    exp = "exit=%d %s" % (r.returncode, r.stdout.strip() or (r.stderr.strip().splitlines() or [""])[-1])
    print(f"--- {label}: {exp}")
    print("   files after:", tree(b))
    try:
        purge_project(b/"claims", b/"records"/"victim.jsonl", "victim"); rr = "ok"
    except Exception as e: rr = repr(e)
    print("   re-run purge:", rr, "| files after re-run:", tree(b))
    shutil.rmtree(b, ignore_errors=True)

import sys, os, subprocess, tempfile, shutil, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from atk2 import mk
from autotester.stages.schedule_store import claim, append_record, purge_project, list_claims, project_records_path, read_records
HOLD = str(Path(__file__).parent/"holder.py")
def seed(b):
    for i in range(2):
        k,c,r = mk("victim", i); claim(b/"claims", k, c)
    p = project_records_path(b/"records", "victim"); append_record(p, mk("victim",0)[2]); return p
def tree(b): return sorted(str(p.relative_to(b)).replace("\\","/") for p in Path(b).rglob("*"))
def hold(mode, target, b, tag):
    ready, stop = b/f"{tag}.ready", b/f"{tag}.stop"
    pr = subprocess.Popen([sys.executable, HOLD, mode, str(target), str(ready), str(stop)], env=os.environ)
    for _ in range(300):
        if ready.exists(): break
        time.sleep(0.1)
    return pr, stop
def release(pr, stop):
    stop.write_text("1"); pr.wait(timeout=60)
def attempt(label, mode, pick, root):
    b = Path(tempfile.mkdtemp(prefix="atk5-", dir=root)); p = seed(b)
    target = pick(b, p)
    before = tree(b)
    pr, stop = hold(mode, target, b, "h")
    b_before = [x for x in tree(b) if not x.startswith("h.")]
    try: purge_project(b/"claims", p, "victim"); res = "purge returned (no error)"
    except BaseException as e: res = f"{type(e).__name__} (OSError={isinstance(e,OSError)}) {str(e)[:70]}"
    after = [x for x in tree(b) if not x.startswith("h.")]
    stage = [x for x in after if ".purge-" in x]
    print(f"{label}: {res}\n    state restored == before: {after == b_before} | stage entries left: {stage} | after: {after}")
    release(pr, stop)
    after2 = [x for x in tree(b) if not x.startswith("h.")]
    if res.startswith("purge returned"):
        print("    after holder released:", after2)
    else:
        try: purge_project(b/"claims", p, "victim"); print("    retry after release: ok ->", [x for x in tree(b) if not x.startswith("h.")])
        except Exception as e: print("    retry failed", repr(e))
    shutil.rmtree(b, ignore_errors=True)
def reader_test(root):
    b = Path(tempfile.mkdtemp(prefix="atk5r-", dir=root)); p = project_records_path(b/"records","victim")
    seed(b)
    pr, stop = hold("reader", p, b, "r")
    ok = fail = bad = 0; leaked = 0
    for n in range(80):
        if not p.exists() and not list(list_claims(b/"claims")): seed(b)
        full = tree(b); full = [x for x in full if not x.startswith("r.")]
        try: purge_project(b/"claims", p, "victim"); ok += 1; st = [x for x in tree(b) if not x.startswith("r.")]; bad += (st != ["claims","records"])
        except OSError: fail += 1; st = [x for x in tree(b) if not x.startswith("r.")]; bad += (st != full)
        leaked += len([x for x in tree(b) if ".purge-" in x])
    release(pr, stop)
    print("5ii reader process:", (b/"r.ready.errs").read_text())
    print(f"5ii reader loop on victim file: attempts=80 success={ok} PermissionError/OSError={fail} inconsistent_states={bad} stage_entries_seen_after={leaked}")
    shutil.rmtree(b, ignore_errors=True)
if __name__ == "__main__":
    import autotester; print("autotester.__file__ =", autotester.__file__)
    root = sys.argv[1]
    reader_test(root); sys.exit(0)
    attempt("5i  open('rb') handle on victim records (other process)", "default", lambda b,p: p, root)
    attempt("5i' os.open(O_RDONLY) handle on victim records", "osopen", lambda b,p: p, root)
    attempt("5i'' os.open(O_APPEND) writer handle on victim records", "append", lambda b,p: p, root)
    reader_test(root)
    claims = lambda b,p: sorted((b/"claims").iterdir())
    attempt("5iii handle on FIRST claim marker", "default", lambda b,p: claims(b,p)[0], root)
    attempt("5iii handle on SECOND claim marker", "default", lambda b,p: claims(b,p)[1], root)
    attempt("5vi FILE_SHARE_DELETE handle on records (move succeeds, rmtree?)", "sharedelete", lambda b,p: p, root)
    attempt("5vi' FILE_SHARE_DELETE handle on a claim marker", "sharedelete", lambda b,p: claims(b,p)[0], root)
    for names in (["a b","a:b","Ab","ab","x%y"],):
        b = Path(tempfile.mkdtemp(prefix="atk5n-", dir=root))
        for n in names: print("5v name", repr(n), "->", project_records_path(b, n).name)
        ap = project_records_path(b,"Ab"); ap.parent.mkdir(exist_ok=True); append_record(ap, mk("Ab",0)[2])
        print("5v 'ab' file exists after writing 'Ab'?:", project_records_path(b,"ab").exists(), "| listing:", [x.name for x in b.iterdir()])
        shutil.rmtree(b, ignore_errors=True)

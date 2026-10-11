import sys, os, json, time, tempfile, shutil, traceback
import multiprocessing as mp
from pathlib import Path
from datetime import datetime, timezone, timedelta

def mk(project, i):
    from autotester.schema.schedule import SlotClaim, SlotRecord, ScheduleMode, SlotOutcome
    inst = datetime(2026,10,8,tzinfo=timezone.utc)+timedelta(minutes=i)
    key = f"{project}:custom:{inst.strftime('%Y-%m-%dT%H:%MZ')}"
    c = SlotClaim(slot_key=key, mode=ScheduleMode.CUSTOM, instant=inst, claimed_at=inst, intended=SlotOutcome.ENQUEUED)
    r = SlotRecord(slot_key=key, project=project, mode=ScheduleMode.CUSTOM, instant=inst, recorded_at=inst, outcome=SlotOutcome.ENQUEUED)
    return key, c, r

def neighbour(name, claim_dir, records_dir, n, out):
    try:
        from autotester.stages.schedule_store import claim, append_record, project_records_path
        path = project_records_path(Path(records_dir), name)
        acked = []; err = []
        for i in range(n):
            key, c, r = mk(name, i)
            try:
                claim(Path(claim_dir), key, c)
                if append_record(path, r): acked.append(key)
            except Exception as e:
                err.append(repr(e))
        Path(out).write_text(json.dumps({"acked": acked, "err": err}))
    except Exception:
        Path(out).write_text(json.dumps({"fatal": traceback.format_exc()}))

def run(variant, base, N=300, P=200):
    from autotester.stages.schedule_store import claim, append_record, project_records_path, purge_project, read_records, list_claims
    base = Path(base); claim_dir = base/"claims"
    records_dir = {"separate": base/"records", "same_as_stage_parent": base, "shared_claims_separate_rec": base/"records"}[variant]
    records_dir.mkdir(parents=True, exist_ok=True)
    ctx = mp.get_context("spawn")
    names = ["n1","n2","n3"]; outs = {n: base/f"out-{n}.json" for n in names}
    procs = [ctx.Process(target=neighbour, args=(n, str(claim_dir), str(records_dir), N, str(outs[n]))) for n in names]
    for p in procs: p.start()
    vpath = project_records_path(records_dir, "victim")
    purges = 0; perr = []
    t0=time.time()
    while purges < P or any(p.is_alive() for p in procs) and purges < P*50:
        for i in range(3):
            k, c, r = mk("victim", i)
            claim(claim_dir, k, c)
        append_record(vpath, mk("victim",0)[2])
        try:
            purge_project(claim_dir, vpath, "victim"); purges += 1
        except Exception as e:
            perr.append(repr(e)); purges += 1
        if purges >= P and not any(p.is_alive() for p in procs): break
        if purges >= P*50: break
    for p in procs: p.join(timeout=300)
    res = {"variant": variant, "purges": purges, "purge_errors": perr[:3], "n_purge_err": len(perr), "secs": round(time.time()-t0,1), "exit": [p.exitcode for p in procs]}
    cl = list_claims(claim_dir)
    lost_rec = lost_claim = dup = 0; nerr = 0
    for n in names:
        d = json.loads(outs[n].read_text())
        if "fatal" in d: res.setdefault("fatal",[]).append(d["fatal"]); continue
        nerr += len(d["err"])
        recs = [r.slot_key for r in read_records(project_records_path(records_dir, n))]
        lines = project_records_path(records_dir, n).read_text().splitlines()
        if len(lines) != len(set(json.loads(l)["slot_key"] for l in lines)): dup += 1
        lost_rec += len(set(d["acked"]) - set(recs))
        lost_claim += sum(1 for i in range(N) if mk(n,i)[0] not in cl)
        res[f"{n}_acked"] = len(d["acked"]); res[f"{n}_present"] = len(recs)
    res.update(neighbour_exceptions=nerr, lost_records=lost_rec, lost_claims=lost_claim, dup_files=dup,
               victim_leftover_claims=[k for k in cl if k.startswith("victim:")], victim_file_exists=vpath.exists(),
               stage_dirs=[p.name for p in base.rglob(".purge-*")])
    print(json.dumps(res))

if __name__ == "__main__":
    import autotester; print("autotester.__file__ =", autotester.__file__)
    for v in ["separate","same_as_stage_parent","shared_claims_separate_rec"]:
        d = tempfile.mkdtemp(prefix="atk2-", dir=sys.argv[1])
        run(v, d)
        shutil.rmtree(d, ignore_errors=True)

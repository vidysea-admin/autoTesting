import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import table as T  # noqa: E402

SP = T.SP
out = {}
T.make_video()

# 1. redaction: provider only receives stills of the redacted copy, none inside 60-70 s
root, src = T.setup("x-redact-ok")
p = subprocess.run([T.PY, str(T.HERE / "drv.py"), "ingest", "review", "demo", src,
                    "--output", "json", "--redact", "1:00-1:10"],
                   env=T.env_for(root, src, "ok"), capture_output=True, text=True,
                   encoding="utf-8", timeout=180)
calls = [json.loads(x) for x in (root / "_calls.jsonl").read_text().splitlines()]
names = sorted(n for c in calls for n in c["names"])
times = sorted(int(Path(n).stem) / 1000 for n in names)
inside = [t for t in times if 60 <= t <= 70]
dirs = sorted({d for c in calls for d in c["dirs"]})
out["redact"] = {"exit": p.returncode, "provider_calls": len(calls), "stills": len(times),
                 "times_first_last": [times[0], times[-1]] if times else None,
                 "stills_inside_window": inside, "stills_dirs": dirs,
                 "orig_in_dirs": any(str(root / "rec.mp4") in d or "sources" in d for d in dirs),
                 "left_after": T.leftovers(root),
                 "stdout_docs": len(T.docs_of(p.stdout)[0])}
# brightness of stills near the window edges (bright test pattern expected outside)
def yavg(png):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf",
                        "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                       capture_output=True, text=True)
    for ln in (r.stdout + r.stderr).splitlines():
        if "YAVG=" in ln:
            return float(ln.split("YAVG=")[1])
    return None
recv = sorted((root / "_recv").glob("*.png"))
out["redact"]["still_yavg_min_max"] = [min(filter(None, map(yavg, recv[:60])), default=None),
                                       max(filter(None, map(yavg, recv[:60])), default=None)]
live = list((SP / "r2b-cases").glob("sig-*/_recv/live_redacted_t65.png"))
out["redact"]["live_redacted_t65_yavg"] = {str(p.parent.parent.name): yavg(p) for p in live}

# 2. review stored by repair-base code still loads at head
old = SP / "r2b-base"
if not old.exists():
    old.mkdir()
    subprocess.run(f'git -C D:/autoTesting archive 0dcbbfa5 src | tar -x -C "{old}"', shell=True,
                   check=True)
root, src = T.setup("x-old-store")
env = T.env_for(root, src, "ok")
env["PYTHONPATH"] = str(old / "src")
chk = subprocess.run([T.PY, "-c", "import autotester,sys;print(autotester.__file__)"], env=env,
                     capture_output=True, text=True).stdout.strip()
a = subprocess.run([T.PY, str(T.HERE / "drv.py"), "ingest", "review", "demo", src, "--output",
                    "json"], env=env, capture_output=True, text=True, encoding="utf-8", timeout=180)
docs_old = T.docs_of(a.stdout)[0]
stored = list((root / "projects" / "demo" / "reviews").glob("rv_*.json"))
env2 = T.env_for(root, src, "runtime")           # head code; a provider call would explode
env2.pop("PYTHONPATH", None)
b = subprocess.run([T.PY, str(T.HERE / "drv.py"), "ingest", "review", "demo", src, "--output",
                    "json"], env=env2, capture_output=True, text=True, encoding="utf-8",
                   timeout=180)
docs_new = T.docs_of(b.stdout)[0]
b2 = subprocess.run([T.PY, str(T.HERE / "drv.py"), "ingest", "review", "demo", src],
                    env=env2, capture_output=True, text=True, encoding="utf-8", timeout=180)
out["old_store"] = {
    "base_autotester_file": chk, "base_exit": a.returncode,
    "base_doc_has_exit_code": "exit_code" in (docs_old[0] if docs_old else {}),
    "stored_files": [s.name for s in stored],
    "stored_has_exit_code": ["exit_code" in json.loads(s.read_text(encoding="utf-8")) for s in stored],
    "head_exit": b.returncode, "head_docs": len(docs_new),
    "head_status": docs_new[0].get("status") if docs_new else None,
    "head_exit_code_key": docs_new[0].get("exit_code") if docs_new else None,
    "same_id": bool(docs_old and docs_new and docs_old[0].get("id") == docs_new[0].get("id")),
    "head_provider_calls_on_replay": len((root / "_calls.jsonl").read_text().splitlines()) - 1,
    "head_text_exit": b2.returncode,
}
# stored review (head-written) has no exit_code either
root, src = T.setup("x-head-store")
c = subprocess.run([T.PY, str(T.HERE / "drv.py"), "ingest", "review", "demo", src, "--output",
                    "json"], env=T.env_for(root, src, "ok"), capture_output=True, text=True,
                   encoding="utf-8", timeout=180)
stored = list((root / "projects" / "demo" / "reviews").glob("rv_*.json"))
out["head_store"] = {"exit": c.returncode, "files": [s.name for s in stored],
                     "has_exit_code": ["exit_code" in json.loads(s.read_text(encoding="utf-8")) for s in stored]}
T.OUT.mkdir(exist_ok=True)
(T.OUT / "extra.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))

# 3. partial by cost cap needs >1 batch: a long pointer window
pw = T.CASES_ROOT / "ptr_window.txt"
pw.write_text("0:10-2:00 | long window\n", encoding="utf-8")
rowp = T.run("x-partial-multibatch", ["demo", "{SRC}", "--output", "json", "--max-cost", "1e-9",
                                      "--pointers", str(pw)])
rowq = T.run("x-ok-multibatch", ["demo", "{SRC}", "--output", "json", "--pointers", str(pw)])
(T.OUT / "extra-partial.json").write_text(json.dumps([rowp, rowq], indent=1), encoding="utf-8")
print(json.dumps({k: rowp[k] for k in ("exit", "stdout_docs", "status", "doc_exit_code", "exit_matches", "provider_calls", "left")}))
print(json.dumps({k: rowq[k] for k in ("exit", "stdout_docs", "status", "doc_exit_code", "exit_matches", "provider_calls", "left")}))

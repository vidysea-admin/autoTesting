"""One of 5 parallel processes. argv: <i> <syncdir>"""
import json, shutil, sys, tempfile, time, urllib.request
from pathlib import Path
import h
from autotester.browser import launch as L
i, sync = int(sys.argv[1]), Path(sys.argv[2])
tmp = Path(tempfile.mkdtemp(prefix="r2b-proc-"))
s = h.mk(tmp)
t = time.monotonic(); s.start(); dur = time.monotonic() - t
lines = (s.paths.profile_dir / "DevToolsActivePort").read_text().splitlines()
me = {"i": i, "port": int(lines[0]), "guid": lines[1].strip(), "start_s": round(dur, 2)}
(sync / f"{i}.json").write_text(json.dumps(me))
while len(list(sync.glob("*.json"))) < 5: time.sleep(0.1)
others = [json.loads(p.read_text()) for p in sorted(sync.glob("*.json"))]
cross = [{"mine": i, "port_of": o["i"], "accepted": L._answers_as(o["port"], me["guid"]), "expect": o["i"] == i} for o in others]
time.sleep(0.5)
pids = list(h.tree_pids())
(sync / f"done{i}").write_text("1")
while len(list(sync.glob("done*"))) < 5: time.sleep(0.1)
s.close(); time.sleep(1)
left = h.alive(pids)
for _ in range(40):
    if not left: break
    time.sleep(0.2); left = h.alive(left)
print(json.dumps({**me, "cross_ok": all(c["accepted"] == c["expect"] for c in cross), "procs_left": left,
                  "port_accepts_after": h.accepts("127.0.0.1", me["port"], 1),
                  "portfile_after": (s.paths.profile_dir / "DevToolsActivePort").exists(), "timers": h.timers()}))
shutil.rmtree(tmp, ignore_errors=True)

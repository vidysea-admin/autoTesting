"""N start/close rounds through the public seam. usage: rounds.py <label> <N> -> JSON on stdout."""
from __future__ import annotations

import json
import shutil
import statistics
import sys
import tempfile
import time
import threading
from pathlib import Path

import h

label, n = sys.argv[1], int(sys.argv[2])
h.install_timers()
base_threads = {t.name for t in threading.enumerate()}
base_children = h.tree_pids()
temp0 = h.tempdirs()
rows = []
for i in range(n):
    tmp = Path(tempfile.mkdtemp(prefix="r2b-round-"))
    s = h.mk(tmp)
    pre_probe = len(h.PROBE["dur"])
    t0 = time.monotonic()
    s.start()
    st = time.monotonic() - t0
    url = s.cdp_url
    port = int(url.rsplit(":", 1)[1])
    pids = h.tree_pids()
    portfile = s.paths.profile_dir / "DevToolsActivePort"
    row = {"round": i + 1, "start_s": round(st, 3),
           "probe_s": round(h.PROBE["dur"][-1], 3), "answers_as_s": round(h.PROBE["ans_dur"][-1], 3),
           "answers_as": h.PROBE["ok"][-1], "port": port, "portfile_before_close": portfile.exists(),
           "n_pids": len(pids)}
    t1 = time.monotonic()
    s.close()
    row["close_s"] = round(time.monotonic() - t1, 3)
    time.sleep(0.5)
    left = h.alive([p for p in pids])
    for _ in range(40):  # allow the OS up to ~8 s to reap
        if not left:
            break
        time.sleep(0.2)
        left = h.alive(left)
    row["procs_left"] = left
    row["port_accepts_after"] = h.accepts("127.0.0.1", port, 1)
    row["portfile_after"] = portfile.exists()
    row["timers_alive"] = h.timers()
    row["new_threads"] = sorted({t.name for t in threading.enumerate()} - base_threads)
    row["children_left"] = sorted(set(h.tree_pids()) - set(base_children))
    try:
        shutil.rmtree(tmp)
        row["profile_rm"] = "ok"
    except OSError as e:
        row["profile_rm"] = f"FAIL {e!r}"
    rows.append(row)
    print(json.dumps(row), flush=True)
starts = [r["start_s"] for r in rows]
probes = [r["probe_s"] for r in rows]
summ = {"label": label, "n": n, "start_median": statistics.median(starts), "start_worst": max(starts),
        "start_min": min(starts), "probe_median": statistics.median(probes), "probe_worst": max(probes),
        "all_answers_as": all(r["answers_as"] for r in rows),
        "all_clean": all(not r["procs_left"] and not r["port_accepts_after"] and not r["portfile_after"]
                         and not r["timers_alive"] and not r["children_left"] and r["profile_rm"] == "ok"
                         for r in rows),
        "temp_playwright_dirs_before_after": [temp0, h.tempdirs()]}
print("SUMMARY " + json.dumps(summ), flush=True)

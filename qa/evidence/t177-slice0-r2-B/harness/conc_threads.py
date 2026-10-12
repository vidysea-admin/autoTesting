"""5 sessions started in parallel threads of one process."""
import json, shutil, tempfile, threading, time, urllib.request
from pathlib import Path
import h
from autotester.browser import launch as L

N = 5
res, errs = {}, {}
calls = []
real_ans = L._answers_as
def ans(port, path):
    r = real_ans(port, path); calls.append((threading.current_thread().name, port, path[-8:], r)); return r
L._answers_as = ans
bar_start, bar_up = threading.Barrier(N), threading.Barrier(N + 1)
go_close = threading.Event(); cerr = {}; close_t = {}
sessions = {}
tmps = {}
def work(i):
    tmp = Path(tempfile.mkdtemp(prefix="r2b-thr-")); tmps[i] = tmp
    s = h.mk(tmp); sessions[i] = s
    bar_start.wait()
    try:
        t = time.monotonic(); s.start(); dur = time.monotonic() - t
        lines = (s.paths.profile_dir / "DevToolsActivePort").read_text().splitlines()
        port, guid = int(lines[0]), lines[1].strip()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        ws = json.load(opener.open(f"{s.cdp_url}/json/version", timeout=5))["webSocketDebuggerUrl"]
        res[i] = {"start_s": round(dur, 2), "url": s.cdp_url, "port": port, "guid": guid, "own_ws_matches": ws.endswith(guid)}
    except BaseException as e:
        errs[i] = repr(e)
    try:
        bar_up.wait(timeout=120)
        go_close.wait(timeout=120)
        t = time.monotonic(); s.close(); close_t[i] = round(time.monotonic() - t, 2)
    except BaseException as e:
        cerr[i] = repr(e)
threads = [threading.Thread(target=work, args=(i,), name=f"S{i}") for i in range(N)]
t0 = time.monotonic()
[t.start() for t in threads]
bar_up.wait(timeout=120)
out = {"wall_s": round(time.monotonic() - t0, 1), "errors": errs, "sessions": res,
       "distinct_ports": len({r["port"] for r in res.values()}), "timers_alive_after_all_started": h.timers()}
# cross: no probe accepts another session's browser
cross = []
for i, ri in res.items():
    for j, rj in res.items():
        r = real_ans(rj["port"], ri["guid"])
        cross.append({"guid_of": i, "port_of": j, "accepted": r, "expect": i == j})
out["cross_ok"] = all(c["accepted"] == c["expect"] for c in cross)
out["probe_calls_own_port_true"] = all(c[3] for c in calls)
out["n_probe_calls"] = len(calls)
pids = h.tree_pids()
out["n_proc_in_tree_with_5_up"] = len(pids)
ports = [r["port"] for r in res.values()]
t1 = time.monotonic(); go_close.set(); [t.join() for t in threads]
out["close_s"] = round(time.monotonic() - t1, 1); out["close_each_s"] = close_t; out["close_errors"] = cerr
time.sleep(1)
left = h.alive(list(pids))
for _ in range(40):
    if not left: break
    time.sleep(0.2); left = h.alive(left)
out["procs_left"] = left
out["ports_accept_after"] = [p for p in ports if h.accepts("127.0.0.1", p, 1)]
out["portfiles_after"] = [i for i, s in sessions.items() if (s.paths.profile_dir / "DevToolsActivePort").exists()]
out["timers_alive_after_close"] = h.timers()
out["threads_left"] = sorted(t.name for t in __import__("threading").enumerate())
for t in tmps.values(): shutil.rmtree(t, ignore_errors=True)
print(json.dumps(out, indent=1))

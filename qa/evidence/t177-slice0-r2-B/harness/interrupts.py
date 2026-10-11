"""KeyboardInterrupt injected during the probe through the real start()."""
import _thread, json, shutil, tempfile, threading, time
from pathlib import Path
import h
import attacks as A
from autotester.browser import launch as L
from autotester.browser import session as S

out = {}
# 1) KI raised at the start of the fetch (inside _answers_as, which must not swallow it)
tmp = Path(tempfile.mkdtemp(prefix="r2b-int-")); s = h.mk(tmp)
real_fetch = L._fetch_version
holder = {}
def ki_fetch(port):
    holder["pids"] = h.tree_pids(); holder["port"] = port
    raise KeyboardInterrupt()
L._fetch_version = ki_fetch
try:
    s.start(); out["i1"] = "RETURNED"
except KeyboardInterrupt:
    out["i1"] = "KeyboardInterrupt propagated"
except BaseException as e:
    out["i1"] = repr(e)
L._fetch_version = real_fetch
time.sleep(1.5)
left = h.alive(list(holder["pids"]))
for _ in range(40):
    if not left: break
    time.sleep(0.2); left = h.alive(left)
out["i1_procs_left"] = left; out["i1_port_accepts_after"] = h.accepts("127.0.0.1", holder["port"], 1)
out["i1_portfile_after"] = (s.paths.profile_dir / "DevToolsActivePort").exists(); out["i1_timers"] = h.timers()
out["i1_session_state"] = [s._context, s._playwright, s._cdp_url]
shutil.rmtree(tmp, ignore_errors=True)

# 2) KI delivered (interrupt_main) 0.5 s into a trickling probe: real blocking read in flight
tmp = Path(tempfile.mkdtemp(prefix="r2b-int-")); s = h.mk(tmp)
holder2 = {}
real_url = S.verified_cdp_url
def attacked(profile_dir):
    lines = (profile_dir / "DevToolsActivePort").read_text().splitlines()
    rp, guid = int(lines[0]), lines[1].strip()
    holder2["pids"] = h.tree_pids(); holder2["port"] = rp
    lst = A.Listener(A.trickle_headers, {"guid": guid, "real_port": rp, "other": None}); holder2["lst"] = lst
    (profile_dir / "DevToolsActivePort").write_text(f"{lst.port}\n{guid}\n")
    holder2["t0"] = time.monotonic()
    threading.Timer(0.5, _thread.interrupt_main).start()
    try:
        return real_url(profile_dir)
    finally:
        holder2["t1"] = time.monotonic()
S.verified_cdp_url = attacked
try:
    s.start(); out["i2"] = "RETURNED"
except KeyboardInterrupt:
    out["i2"] = "KeyboardInterrupt propagated"
except BaseException as e:
    out["i2"] = repr(e)
S.verified_cdp_url = real_url
out["i2_interrupt_to_raise_s"] = round(holder2["t1"] - holder2["t0"], 2)
time.sleep(1.5)
left = h.alive(list(holder2["pids"]))
for _ in range(40):
    if not left: break
    time.sleep(0.2); left = h.alive(left)
out["i2_procs_left"] = left; out["i2_port_accepts_after"] = h.accepts("127.0.0.1", holder2["port"], 1)
out["i2_portfile_after"] = (s.paths.profile_dir / "DevToolsActivePort").exists(); out["i2_timers"] = h.timers()
out["i2_session_state"] = [s._context, s._playwright, s._cdp_url]
holder2["lst"].close(); shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(out, indent=1))

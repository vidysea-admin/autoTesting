"""R1-B item 1: real headless Chromium through BrowserSession, hostile identity probe + failure between launch and publish."""
import json, socket, subprocess, sys, threading, time, os, tempfile
from pathlib import Path
SRC = os.environ["R1B_SRC"]            # copy root
sys.path.insert(0, SRC + "/src"); sys.path.insert(0, SRC + "/tests")
import autotester
assert autotester.__file__.startswith(SRC.replace("/", os.sep)) or autotester.__file__.replace("\\","/").startswith(SRC), autotester.__file__
from test_browser import make_project, make_store
from autotester.browser import launch
from autotester.browser.launch import CdpEndpointError
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.stages.run_budget import RunBudgetExceeded

WORK = Path(os.environ["R1B_WORK"]); WORK.mkdir(parents=True, exist_ok=True)

def procs_for(profile: Path):
    needle = str(profile).lower()
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.ToLower().Contains('%s') } "
          "| Where-Object { $_.Name -notlike 'powershell*' } | ForEach-Object { '{0}:{1}' -f $_.ProcessId,$_.Name }" % needle.replace("'", "''"))
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout
    # exclude the powershell query itself (its command line contains the needle)
    return [x for x in out.split() if ':' in x]

def accepts(host, port):
    try:
        socket.create_connection((host, port), timeout=3).close(); return True
    except OSError:
        return False

class Hostile:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.srv = socket.socket(); self.srv.bind(("127.0.0.1", 0)); self.srv.listen(8)
        self.port = self.srv.getsockname()[1]; self.hits = 0
        threading.Thread(target=self.loop, daemon=True).start()
    def loop(self):
        while True:
            try: c, _ = self.srv.accept()
            except OSError: return
            threading.Thread(target=self.serve, args=(c,), daemon=True).start()
    def serve(self, c):
        try:
            self.hits += 1; c.settimeout(3); buf = b""
            while b"\r\n\r\n" not in buf: 
                d = c.recv(4096)
                if not d: break
                buf += d
            c.sendall(self.payload)
        except OSError: pass
        finally:
            try: c.close()
            except OSError: pass
    def stop(self): self.srv.close()

def http(body: bytes, ctype=b"application/json"):
    return b"HTTP/1.0 200 OK\r\nContent-Type: " + ctype + b"\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body

def fresh_session(root: Path, budget=None):
    s = BrowserSession(make_project(headed=False), make_store(root), root / "run",
                       ProjectPaths("pathlynks", root), expose_cdp=True)
    if budget is not None: s.budget = budget
    return s

class StubBudget:
    """check_start ok; remaining_ms raises on the Nth call (start(): 1 before check_start, 2 after, 3 inside the try = between launch and publish)."""
    def __init__(self, exc, nth=3): self.exc, self.n, self.nth = exc, 0, nth
    def check_start(self): pass
    def remaining_ms(self, requested): 
        self.n += 1
        if self.n >= self.nth: raise self.exc
        return int(requested)

def second_start_ok(root: Path):
    s = fresh_session(root)
    try:
        s.start(); u = s.cdp_url
        ok = bool(u and u.startswith("http://127.0.0.1:"))
    except BaseException as e:
        return f"FAIL {type(e).__name__}: {e}"
    finally:
        try: s.close()
        except BaseException: pass
    return "ok" if ok else "no cdp_url"

def run_case(name, setup, expect_exc, hostile_payload=None, mode="probe"):
    root = WORK / name; root.mkdir(parents=True, exist_ok=True)
    profile = root / "profiles" / "pathlynks"
    rec = {"case": name, "src": SRC.split("/")[-1]}
    host = Hostile(hostile_payload) if hostile_payload is not None else None
    state = {}
    orig = launch._published
    if mode == "probe":
        def patched(profile_dir, deadline):
            port, path = orig(profile_dir, deadline)
            state["real_port"] = port; state["real_path"] = path
            state["procs_during"] = len(procs_for(profile))
            return host.port, path
        launch._published = patched
        s = fresh_session(root)
    else:
        # failure between launch and publish: record the real port from the file after the fact
        s = fresh_session(root, budget=setup)
    t0 = time.monotonic(); exc = None
    try:
        s.start()
    except BaseException as e:   # incl. KeyboardInterrupt
        exc = e
    finally:
        launch._published = orig
    rec["raised"] = None if exc is None else f"{type(exc).__module__}.{type(exc).__name__}: {str(exc)[:120]}"
    rec["raised_expected"] = (type(exc).__name__ == expect_exc)
    rec["start_s"] = round(time.monotonic() - t0, 1)
    time.sleep(1.0)
    rec["cdp_url"] = s.cdp_url
    rec["port_file_exists"] = (profile / "DevToolsActivePort").exists()
    rec["procs_alive_after"] = procs_for(profile)
    if "real_port" in state:
        rec["real_port"] = state["real_port"]; rec["procs_during(positive control)"] = state["procs_during"]
        rec["real_port_accepts_after"] = accepts("127.0.0.1", state["real_port"])
    if host: rec["hostile_hits"] = host.hits; host.stop()
    rec["second_start"] = second_start_ok(root)
    time.sleep(1.0)
    rec["procs_alive_after_second"] = procs_for(profile)
    print(json.dumps(rec), flush=True)

if __name__ == "__main__":
    only = sys.argv[1:] 
    G = "/devtools/browser/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    cases = [
      ("nonhttp",  None, "CdpEndpointError", b"garbage, not http\r\n", "probe"),
      ("json_list", None, "CdpEndpointError", http(b"[]"), "probe"),
      ("json_str",  None, "CdpEndpointError", http(b'"x"'), "probe"),
      ("json_null", None, "CdpEndpointError", http(b"null"), "probe"),
      ("other_browser", None, "CdpEndpointError", http(json.dumps({"webSocketDebuggerUrl": "ws://127.0.0.1:1"+G}).encode()), "probe"),
      ("deep_nest", None, "CdpEndpointError", http(b"[" * 200000), "probe"),
      ("redirect", None, "CdpEndpointError", b"HTTP/1.0 302 Found\r\nLocation: http://127.0.0.1:9/x\r\nContent-Length: 0\r\n\r\n", "probe"),
      ("trunc_body", None, "CdpEndpointError", b"HTTP/1.0 200 OK\r\nContent-Length: 500\r\n\r\n{\"web", "probe"),
      ("budget", StubBudget(RunBudgetExceeded("run budget spent")), "RunBudgetExceeded", None, "budget"),
      ("kbint",  StubBudget(KeyboardInterrupt()), "KeyboardInterrupt", None, "budget"),
    ]
    for name, setup, exp, payload, mode in cases:
        if only and name not in only: continue
        try: run_case(name, setup, exp, payload, mode)
        except BaseException as e: print(json.dumps({"case": name, "HARNESS_ERROR": repr(e)}), flush=True)

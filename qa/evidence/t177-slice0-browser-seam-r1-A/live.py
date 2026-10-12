import os, sys, json, socket, subprocess, time, tempfile, types, pathlib
sys.path.insert(0, os.environ["COPY"] + "/tests")
from test_browser import make_project, make_store
from autotester.browser import launch, session as sess_mod
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.stages.run_budget import RunBudgetExceeded

def descendants():
    out = subprocess.run(["powershell","-NoProfile","-Command",
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"],
        capture_output=True, text=True).stdout
    procs = json.loads(out); kids = {}
    for p in procs: kids.setdefault(p["ParentProcessId"], []).append(p)
    seen, stack, res = set(), [os.getpid()], []
    while stack:
        for c in kids.get(stack.pop(), []):
            if c["ProcessId"] not in seen:
                seen.add(c["ProcessId"]); res.append((c["ProcessId"], c["Name"])); stack.append(c["ProcessId"])
    return res
def accepts(port):
    try: socket.create_connection(("127.0.0.1", port), timeout=2).close(); return True
    except OSError: return False
def mk(tag):
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"cdpprobe-{tag}-"))
    return root, BrowserSession(make_project(headed=False), make_store(root), root/"run", ProjectPaths("pathlynks", root), expose_cdp=True)
def port_of(s):
    f = s.paths.profile_dir / "DevToolsActivePort"
    return int(f.read_text().splitlines()[0]) if f.exists() else None
def after(label, s, port):
    time.sleep(1.5)
    chrome = [d for d in descendants() if "chrome" in d[1].lower() or "headless" in d[1].lower()]
    print(f"  [{label}] cdp_url={s.cdp_url} port_open={accepts(port) if port else 'n/a'} portfile={(s.paths.profile_dir/'DevToolsActivePort').exists()} chromium_descendants={len(chrome)}")

class Obs:
    def __init__(self, exc, sabotage_close=False): self.exc, self.sab = exc, sabotage_close
    def attach(self, page):
        if self.sab:
            def bad(*a, **k): raise RuntimeError("context.close failed")
            self.s._context.close = bad
        raise self.exc

def scen_recursion():
    print("S1 RecursionError from probe (json.load) in a real exposed browser")
    root, s = mk("rec")
    orig = launch.json
    launch.json = types.SimpleNamespace(load=lambda r: (_ for _ in ()).throw(RecursionError("deep")), dumps=orig.dumps, loads=orig.loads)
    try:
        s.start()
    except BaseException as e:
        print("  raised", type(e).__name__)
        port = None
    finally:
        launch.json = orig
    # port captured before close is gone, so re-read via check of any listener: use descendants
    after("post", s, None)
    s.close(); s.close(); print("  double close ok")
    return s

def scen_exc(kind, exc, sab=False):
    print(f"S {kind}")
    root, s = mk(kind[:5].replace(' ','_'))
    s.observer = Obs(exc, sab); s.observer.s = s
    holder = {}
    orig_pub = s._publish_cdp
    def pub(): orig_pub(); holder["port"] = int(s._cdp_url.rsplit(":",1)[1])
    s._publish_cdp = pub
    try: s.start(); print("  start returned?!")
    except BaseException as e: print("  raised", type(e).__name__, str(e)[:50])
    after("post", s, holder.get("port"))
    s.close()
    return s, holder

def scen_reuse():
    print("S reuse after failed start")
    root, s = mk("reuse")
    s.observer = Obs(RuntimeError("boom")); s.observer.s = s
    try: s.start()
    except RuntimeError: pass
    s.observer = None
    s.start(); print("  restart ok cdp_url=", s.cdp_url); port = int(s.cdp_url.rsplit(":",1)[1])
    s.close(); after("closed", s, port)

def scen_launch_timeout():
    print("S launch_persistent_context times out (budget 1ms) with expose_cdp")
    root, s = mk("lt")
    class B:
        def check_start(self): pass
        def remaining_ms(self, r=30000): return 1
    s.budget = B()
    try: s.start(); print("  returned?!")
    except BaseException as e: print("  raised", type(e).__name__, str(e)[:60])
    pf = s.paths.profile_dir/"DevToolsActivePort"
    port = int(pf.read_text().splitlines()[0]) if pf.exists() else None
    time.sleep(2)
    print("  portfile", pf.exists(), "port", port, "open", accepts(port) if port else 'n/a', "playwright_still_set", s._playwright is not None, "context", s._context)
    chrome = [d for d in descendants() if "chrome" in d[1].lower()]
    print("  chromium descendants", len(chrome), "total descendants", len(descendants()))
    s.close(); time.sleep(1.5); print("  after close(): descendants", len(descendants()))

if __name__ == "__main__":
    for name in sys.argv[1:]:
        {"rec": scen_recursion,
         "kbd": lambda: scen_exc("KeyboardInterrupt after publish", KeyboardInterrupt()),
         "exit": lambda: scen_exc("SystemExit after publish", SystemExit(3)),
         "closefail": lambda: scen_exc("close() raises during failure path", RuntimeError("original"), sab=True),
         "reuse": scen_reuse, "lt": scen_launch_timeout}[name]()
    print("final descendants:", descendants())

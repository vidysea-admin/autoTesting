import json, socket, sys, tempfile, time, urllib.request
from pathlib import Path
import autotester
print("autotester.__file__", autotester.__file__)
from autotester.browser import launch
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project, SecretRef

def mk(tmp):
    p = Project(slug="pathlynks", name="P", base_url="https://app.pathlynks.test",
                allowed_domains=["pathlynks.test"], headed=False,
                secrets=[SecretRef(key="PATHLYNKS_PASSWORD", domains=["pathlynks.test"])])
    env = tmp / ".env"; env.write_text("PATHLYNKS_PASSWORD=dummy-not-real\n", encoding="utf-8")
    return p, SecretStore.load(p, env)

def acc(h, port):
    try: socket.create_connection((h, port), timeout=2).close(); return True
    except OSError: return False

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url):
    with opener.open(url, timeout=5) as r: return json.load(r)

# P1
tmp = Path(tempfile.mkdtemp(prefix="p1-", dir=sys.argv[1]))
p, st = mk(tmp)
s = BrowserSession(p, st, tmp/"run", ProjectPaths("pathlynks", tmp), expose_cdp=True)
s.start()
try:
    url = s.cdp_url; port = int(url.rsplit(":",1)[1])
    print("P1 cdp_url", url)
    lst = get(url + "/json/list")
    print("P1 /json/list needs no secret: targets", len(lst), "ws page url present:", all("webSocketDebuggerUrl" in t for t in lst))
    print("P1 127.0.0.2 accepts:", acc("127.0.0.2", port))
    print("P1 portfile:", (s.paths.profile_dir/"DevToolsActivePort").read_text().splitlines()[0])
finally:
    s.close()
print("P1 after close cdp_url", s.cdp_url, "file exists", (s.paths.profile_dir/"DevToolsActivePort").exists())
time.sleep(1); print("P1 port accepting after close", acc("127.0.0.1", port))

# P2: exception during start() after launch, before publish
tmp = Path(tempfile.mkdtemp(prefix="p2-", dir=sys.argv[1]))
p, st = mk(tmp)
s = BrowserSession(p, st, tmp/"run", ProjectPaths("pathlynks", tmp), expose_cdp=True)
orig = BrowserSession._timeout
def boom(self, requested=30000):
    raise RuntimeError("simulated budget exceeded after launch")
BrowserSession._timeout = boom
try:
    try:
        s.start()
    except RuntimeError as e:
        print("P2 start raised:", e)
finally:
    BrowserSession._timeout = orig
pf = s.paths.profile_dir/"DevToolsActivePort"
print("P2 after failed start: port file exists", pf.exists(), "context still open", s._context is not None)
if pf.exists():
    port = int(pf.read_text().splitlines()[0])
    print("P2 leaked endpoint accepting on 127.0.0.1:", acc("127.0.0.1", port), "json/list targets", len(get(f"http://127.0.0.1:{port}/json/list")))
print("P2 cdp_url", s.cdp_url)
s.close()
print("P2 after caller close(): file exists", pf.exists())
if pf.exists() is False:
    pass
time.sleep(1)
try: print("P2 port accepting after close", acc("127.0.0.1", port))
except NameError: pass

# P3: probe fail-open on non-refusal OSError
import socket as _s
real = _s.create_connection
def timing_out(*a, **k): raise TimeoutError("simulated drop")
launch.socket.create_connection = timing_out
print("P3 _reaches_past_loopback on timeout ->", launch._reaches_past_loopback(1))
def cant_assign(*a, **k): raise OSError(49, "Can't assign requested address (macOS lo0 has no 127.0.0.2)")
launch.socket.create_connection = cant_assign
print("P3 _reaches_past_loopback on 'cannot assign' ->", launch._reaches_past_loopback(1))
launch.socket.create_connection = real

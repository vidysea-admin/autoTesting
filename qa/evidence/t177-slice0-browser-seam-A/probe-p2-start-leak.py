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

# P2: exception during start() after launch, before publish
tmp = Path(tempfile.mkdtemp(prefix="p2-", dir=sys.argv[1]))
p, st = mk(tmp)
s = BrowserSession(p, st, tmp/"run", ProjectPaths("pathlynks", tmp), expose_cdp=True)
orig = BrowserSession._timeout
calls=[0]
def boom(self, requested=30000):
    calls[0]+=1
    if calls[0]>=2: raise RuntimeError("simulated budget exceeded after launch")
    return {}
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


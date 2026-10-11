"""HTTP + queue refusal attacks. No real network, no real litellm, no browser."""
import sys, os, json, logging, io, shutil, socket, traceback, tempfile, pathlib
WT = "D:/autoTesting/.worktrees/t202-any-model-provider"
sys.path.insert(0, WT + "/src"); sys.path.insert(0, WT + "/tests")
HERE = pathlib.Path(__file__).parent
ROOT = HERE / "root_http3"
shutil.rmtree(ROOT, ignore_errors=True); ROOT.mkdir()
os.environ["AUTOTESTER_ROOT"] = str(ROOT)
os.environ["AUTOTESTER_APPROVAL_KEY"] = "test-only-key"
for k in ("AUTOTESTER_MODEL","LITELLM_API_KEY","LITELLM_API_BASE","OLLAMA_BASE_URL","OPENAI_API_KEY",
          "ANTHROPIC_API_KEY","GEMINI_API_KEY","GOOGLE_API_KEY"):
    os.environ.pop(k, None)

# no real network: refuse every non-loopback connect
attempts = []
_rc, _rce = socket.socket.connect, socket.socket.connect_ex
def _loop(a): return isinstance(a, tuple) and a and a[0] in ("127.0.0.1","::1","localhost")
def _refuse(self, a):
    if _loop(a): return _rc(self, a)
    attempts.append(a); raise AssertionError(f"NETWORK {a!r}")
def _refuse_ex(self, a):
    if _loop(a): return _rce(self, a)
    attempts.append(a); return 1
socket.socket.connect = _refuse; socket.socket.connect_ex = _refuse_ex

import pytest
from litellm_fake import FakeLiteLLM
mp = pytest.MonkeyPatch()
def install_fake(missing=("SOME_API_KEY",), responses=()):
    f = FakeLiteLLM(list(responses), missing_keys=list(missing))
    sys.modules["litellm"] = f
    os.environ["LITELLM_MODE"] = "PRODUCTION"; os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    return f
fake = install_fake()

logbuf = io.StringIO()
h = logging.StreamHandler(logbuf); h.setLevel(1)
logging.getLogger().addHandler(h); logging.getLogger().setLevel(1)

from fastapi.testclient import TestClient
from autotester.ui.app import app
import autotester.ui.routes_runs as routes_runs
import autotester.ui.run_execution as run_execution
import autotester.providers as providers
from autotester.ui import run_queue
from autotester.browser.session import BrowserSession
from autotester.store.project_store import ProjectStore
from autotester.schema.case import Case
from autotester.schema.enums import CaseKind, CaseClass, Action
from autotester.schema.flowspec import Step
from autotester.schema.project import ProviderConfig
from run_approval_fixture import grant_live_case_approval

launched = []
def _boom(self):
    launched.append("BrowserSession.start"); raise AssertionError("BROWSER LAUNCH")
BrowserSession.start = _boom

client = TestClient(app, raise_server_exceptions=False)
r = client.post("/onboard", data={"slug": "demo", "name": "Demo", "base_url": "https://demo.test",
                                  "allowed_domains": "demo.test"})
assert r.status_code in (200, 303), r.text[:200]
store = ProjectStore("demo", ROOT)
store.add_case(Case(project="demo", flow_id="flow-home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
    title="Homepage loads", steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")]))
grant_live_case_approval(store, target=store.load_project().base_url)

def set_providers(**roles):
    p = store.load_project()
    store.save_project(p.model_copy(update={"providers": ProviderConfig(**roles)}))

def qfile():
    p = ROOT / ".work" / "run_queue.json"
    return p.read_text(encoding="utf-8") if p.exists() else None


import time
HTML = {"accept": "text/html"}
class _Ok:
    def available(self): return True
jobs = []
for name, spec in [("1MB model unavailable", "litellm:" + "a"*1_000_000), ("1MB unknown id", "z"*1_000_000),
                   ("1MB spaces-in-model", "litellm:" + "a b"*300_000), ("100k model", "litellm:" + "a"*100_000)]:
    set_providers(judge=spec)
    for tag, hdr in (("json", {}), ("html", HTML)):
        t = time.perf_counter()
        r = client.post("/projects/demo/run", headers=hdr, follow_redirects=False)
        print(f"[{name}] press {tag}: {r.status_code} len={len(r.text)} {time.perf_counter()-t:.2f}s")
    set_providers()
    routes_runs.for_role = lambda project, role: _Ok()
    run_queue._QUEUE = run_queue.RunQueue(spawn=jobs.append, path=run_queue._queue_file)
    client.post("/projects/demo/run", follow_redirects=False)
    set_providers(judge=spec); routes_runs.for_role = providers.for_role
    t = time.perf_counter(); jobs.pop()(); 
    page = client.get("/projects/demo/report").text
    print(f"   queue refusal+report page: {time.perf_counter()-t:.2f}s, report len={len(page)}, queue file bytes={len(qfile() or '')}")
print("browser launches:", launched, "| network:", attempts)

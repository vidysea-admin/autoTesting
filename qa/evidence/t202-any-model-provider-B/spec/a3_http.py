"""HTTP + queue refusal attacks. No real network, no real litellm, no browser."""
import sys, os, json, logging, io, shutil, socket, traceback, tempfile, pathlib
WT = "D:/autoTesting/.worktrees/t202-any-model-provider"
sys.path.insert(0, WT + "/src"); sys.path.insert(0, WT + "/tests")
HERE = pathlib.Path(__file__).parent
ROOT = HERE / "root_http"
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

HTML = {"accept": "text/html"}
specs = [
 ("unavailable ok-shape", "litellm:some/model"),
 ("empty model", "litellm:"), ("at sign", "litellm:a@b"), ("vertex@", "litellm:vertex_ai/claude-3-5-sonnet@20240620"),
 ("script", "litellm:<script>alert(1)</script>"), ("script id", "<script>alert(1)</script>"),
 ("cred as id", "sk-abc123"), ("cred as id:model", "sk-abc123:m"), ("ws before colon", "litellm :x"),
 ("nbsp before colon", "litellm\u00a0:x"), ("cred as model", "litellm:sk-live-abc123def456"),
 ("query key model", "litellm:openai/gpt-4o?key=SECRETQ"), ("NUL", "litellm:gpt\x00-4"),
 ("secret placeholder", "litellm:{{SECRET:KEY}}"), ("vision list as judge", "gemini,anthropic"),
 ("quote", "litellm:a'b\"c"),
]
print("=== A. press (POST /run), real factory, Accept json & html ===")
for name, spec in specs:
    set_providers(judge=spec)
    out = {}
    for tag, hdr in (("json", {}), ("html", HTML)):
        try:
            r = client.post("/projects/demo/run", headers=hdr, follow_redirects=False)
            out[tag] = (r.status_code, r.headers.get("content-type"), r.text)
        except Exception as e:
            out[tag] = ("EXC", type(e).__name__, str(e)[:200])
    j, hh = out["json"], out["html"]
    import re
    m = re.search(r"<p>(.*?)</p>", hh[2], re.S)
    print(f"[{name}] spec={spec!r}\n   json: {j[0]} {j[1]} {j[2][:330]!r}\n   html: {hh[0]} {hh[1]} <p>={(m.group(1) if m else hh[2][:200])[:330]!r}")
    if "<script>" in hh[2]: print("   !! RAW <script> in html body")
    if "<script>alert" in j[2]: print("   (json body carries raw markup; content-type", j[1], ")")
print("queue file after presses:", qfile())
print("browser launches:", launched, "| network attempts:", attempts)

print("\n=== B. env AUTOTESTER_MODEL path (default providers) ===")
set_providers()
for model in ["gemini/gemini-2.5-pro", "https://user:pw-canary@host/v1", "sk-live-abc123def456", "<script>alert(1)</script>", "a b c"]:
    os.environ["AUTOTESTER_MODEL"] = model
    for tag, hdr in (("json", {}), ("html", HTML)):
        r = client.post("/projects/demo/run", headers=hdr, follow_redirects=False)
        print(f"[env {model!r}] {tag}: {r.status_code} {r.text[:300]!r}")
os.environ.pop("AUTOTESTER_MODEL")

print("\n=== C. queue start-time re-check ===")
class _Ok:
    def available(self): return True
jobs = []
for name, spec in specs:
    set_providers()   # defaults
    orig = routes_runs.for_role
    routes_runs.for_role = lambda project, role: _Ok()
    run_queue._QUEUE = run_queue.RunQueue(spawn=jobs.append)
    r = client.post("/projects/demo/run", follow_redirects=False)
    assert r.status_code == 303, (r.status_code, r.text[:200])
    set_providers(judge=spec)
    routes_runs.for_role = providers.for_role
    try:
        jobs.pop()()
    except BaseException as e:
        print("   !! job raised", type(e).__name__, str(e)[:200])
    snap = run_queue.get_queue().snapshot()
    e = snap[-1]
    page = client.get("/projects/demo/report").text
    reasonhtml = re.findall(r"<span class='meta'>(.*?)</span>", page, re.S)
    print(f"[{name}] status={e.status.value} reason={e.reason!r}\n   report-page reason spans={reasonhtml[-1:]!r}")
    if "<script>" in page: print("   !! RAW <script> on report page")
    routes_runs.for_role = orig
disk = qfile()
print("queue file on disk has raw <script>:", "<script>" in (disk or ""), "| has SECRETQ:", "SECRETQ" in (disk or ""), "| has sk-abc123:", "sk-abc123" in (disk or ""))
print("sample disk reasons:", [x.get("reason") for x in json.loads(disk)["entries"]][:20] if disk else None)
print("browser launches:", launched, "| network attempts:", attempts)
lg = logbuf.getvalue()
print("log lines:", len(lg.splitlines()), "| log contains sk-abc123:", "sk-abc123" in lg, "| SECRETQ:", "SECRETQ" in lg, "| pw-canary:", "pw-canary" in lg, "| <script>:", "<script>" in lg)
for line in lg.splitlines():
    if any(t in line for t in ("sk-abc123","SECRETQ","<script>","sk-live")): print("   LOG:", line[:300])

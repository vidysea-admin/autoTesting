import sys, os, re, shutil, socket, pathlib, traceback, logging, io
WT = "D:/autoTesting/.worktrees/t202-any-model-provider"
sys.path.insert(0, WT + "/src"); sys.path.insert(0, WT + "/tests")
HERE = pathlib.Path(__file__).parent
ROOT = HERE / "root_cli"; shutil.rmtree(ROOT, ignore_errors=True); ROOT.mkdir()
os.environ["AUTOTESTER_ROOT"] = str(ROOT); os.environ["AUTOTESTER_APPROVAL_KEY"] = "k"
for k in ("AUTOTESTER_MODEL","LITELLM_API_KEY","LITELLM_API_BASE","OLLAMA_BASE_URL","OPENAI_API_KEY","ANTHROPIC_API_KEY","GEMINI_API_KEY","GOOGLE_API_KEY"):
    os.environ.pop(k, None)
attempts=[]; _rc,_rce=socket.socket.connect,socket.socket.connect_ex
def _loop(a): return isinstance(a, tuple) and a and a[0] in ("127.0.0.1","::1","localhost")
def _r(self,a):
    if _loop(a): return _rc(self,a)
    attempts.append(a); raise AssertionError(f"NETWORK {a!r}")
def _re(self,a):
    if _loop(a): return _rce(self,a)
    attempts.append(a); return 1
socket.socket.connect=_r; socket.socket.connect_ex=_re
from litellm_fake import FakeLiteLLM
fake = FakeLiteLLM([], missing_keys=["SOME_API_KEY"]); sys.modules["litellm"] = fake
os.environ["LITELLM_MODE"]="PRODUCTION"; os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]="True"
from typer.testing import CliRunner
from fastapi.testclient import TestClient
from test_expand_cli import _seed
from test_coverage_wiring import _a_case
from autotester.cli import app as cli_app
from autotester.ui.app import app
from autotester.store.project_store import ProjectStore
from autotester.schema.project import ProviderConfig
store = _seed(ROOT)
runner = CliRunner(mix_stderr=False) if "mix_stderr" in CliRunner.__init__.__code__.co_varnames else CliRunner()

def show(name, res):
    exc = res.exception
    out = res.stdout if hasattr(res, "stdout") else res.output
    err = getattr(res, "stderr", "") if True else ""
    try: err = res.stderr
    except Exception: err = "(n/a)"
    print(f"[{name}] exit={res.exit_code} exc={type(exc).__name__ if exc and not isinstance(exc, SystemExit) else None}"
          f"{(': '+str(exc)[:160]) if exc and not isinstance(exc, SystemExit) else ''}\n    stdout={out.strip()[:320]!r}\n    stderr={err.strip()[:200]!r} lines={len(out.strip().splitlines())}")

print("=== CLI expand --provider ===")
provs = ["litellm:some/model", "litellm:", "litellm:x@y", "nonsense", "litellm:ollama/llama3 secretvalue",
         "sk-live-abc123", "sk-live-abc123:model", "litellm :x", "litellm:sk-live-abc123def", "litellm:openai/gpt-4o?key=SECRETQ",
         "gemini,anthropic", "litellm:<b>x</b>", "", "litellm:vertex_ai/claude-3-5-sonnet@20240620",
         "litellm:https://user:pw@host/v1"]
for p in provs:
    show(f"expand {p!r}", runner.invoke(cli_app, ["expand", "demo", "--provider", p]))

print("\n=== CLI other commands that call providers.get(unparsed) ===")
show("ledger relitigation sk-live-abc123", runner.invoke(cli_app, ["ledger", "relitigation", "some unit text", "--provider", "sk-live-abc123"]))
show("ledger relitigation litellm:some/model", runner.invoke(cli_app, ["ledger", "relitigation", "some unit text", "--provider", "litellm:some/model"]))
from autotester.schema.project import Source
from autotester.schema.enums import SourceKind
try:
    src = store.add_source(Source(project="demo", kind=SourceKind.VIDEO, path="x.mp4", label="x"))
    sid = getattr(src, "id", None) or store.list_sources()[0].id
    show("ingest run sk-live-abc123", runner.invoke(cli_app, ["ingest", "run", "demo", sid, "--provider", "sk-live-abc123"]))
    show("ingest run litellm:some/model", runner.invoke(cli_app, ["ingest", "run", "demo", sid, "--provider", "litellm:some/model"]))
    show("ingest analyze --models sk-live-abc123", runner.invoke(cli_app, ["ingest", "analyze", "demo", sid, "--models", "sk-live-abc123"]))
except Exception as e:
    print("ingest setup failed:", type(e).__name__, str(e)[:200]); traceback.print_exc()
show("orchestrate sk-live-abc123", runner.invoke(cli_app, ["orchestrate", "demo", "--provider", "sk-live-abc123"]))

print("\n=== providers command ===")
show("providers", runner.invoke(cli_app, ["providers"]))
os.environ["OLLAMA_BASE_URL"] = "http://user:pw-canary@host:11434"
show("providers w/ OLLAMA_BASE_URL userinfo", runner.invoke(cli_app, ["providers"]))
os.environ.pop("OLLAMA_BASE_URL")

print("\n=== learn route (POST /cases/generate) ===")
client = TestClient(app, raise_server_exceptions=False)
def setp(**roles):
    p = store.load_project(); store.save_project(p.model_copy(update={"providers": ProviderConfig(**roles)}))
for spec in ["litellm:", "litellm:a@b", "litellm:some/model", "litellm:<script>alert(1)</script>", "sk-live-abc123", "<script>x</script>",
             "litellm :x", "litellm:sk-live-abc123def", "litellm:openai/gpt-4o?key=SECRETQ", "gemini,anthropic"]:
    setp(agent=spec)
    r = client.post("/projects/demo/cases/generate")
    m = re.search(r"<p>(.*?)</p>", r.text, re.S)
    raw = "<script>" in r.text
    print(f"[learn agent={spec!r}] {r.status_code} {r.headers.get('content-type')} <p>={(m.group(1) if m else r.text[:160])[:300]!r} rawscript={raw}")
setp()
for model in ["https://user:pw-canary@host/v1", "<script>alert(1)</script>"]:
    os.environ["AUTOTESTER_MODEL"] = model
    r = client.post("/projects/demo/cases/generate"); m = re.search(r"<p>(.*?)</p>", r.text, re.S)
    print(f"[learn env AUTOTESTER_MODEL={model!r}] {r.status_code} <p>={(m.group(1) if m else r.text[:160])[:300]!r} rawscript={'<script>' in r.text}")
os.environ.pop("AUTOTESTER_MODEL")

# vision route
print("\n=== sources analyze route (vision ensemble from project.json) ===")
sid = store.list_sources()[0].id if store.list_sources() else None
for vis in ["sk-live-abc123", "<script>x</script>", "litellm:some/model", "gemini,sk-live-abc123"]:
    p = store.load_project(); store.save_project(p.model_copy(update={"providers": ProviderConfig(vision=vis)}))
    if sid:
        r = client.post(f"/projects/demo/sources/{sid}/analyze", headers={"accept":"text/html"}, follow_redirects=False)
        m = re.search(r"<p>(.*?)</p>", r.text, re.S)
        print(f"[vision={vis!r}] {r.status_code} <p>={(m.group(1) if m else r.text[:200])[:300]!r} rawscript={'<script>' in r.text}")
print("network attempts:", attempts)

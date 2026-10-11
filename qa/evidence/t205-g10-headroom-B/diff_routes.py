"""Differential: refusal behaviour of POST /projects/{slug}/run (argv[1] = label). Fake keys only."""
import json, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, "D:/autoTesting/.worktrees/t205-g10-headroom/tests")
root = Path(tempfile.mkdtemp(prefix="b-diff-"))
os.environ["AUTOTESTER_ROOT"] = str(root); os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
from autotester.core.ids import APPROVAL_KEY_ENV
os.environ[APPROVAL_KEY_ENV] = "fake-approval-key-for-b-check"
(root / ".env").write_text("DEMO_PW=FAKE-SECRET-VALUE-123\nOTHER_KEY=zzz\n", encoding="utf-8")

from fastapi.testclient import TestClient
import autotester.ui.routes_runs as rr
from autotester.ui.app import app
from autotester.schema.project import Project, SecretRef
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.store.project_store import ProjectStore
from run_approval_fixture import grant_live_case_approval

AVAIL = {"v": True}
class Judge:
    trace = None
    def available(self): return AVAIL["v"]
rr.LangChainFallbackProvider = Judge

class FakeQueue:
    full = False
    submitted = []
    def submit(self, project, **kw):
        if FakeQueue.full:
            raise rr.QueueFull("3 runs of 'demo' are already waiting; wait for one to start")
        FakeQueue.submitted.append((project, kw))
    def planning(self, run_id):  # not used here
        raise AssertionError("planning must not be reached in a gate check")
    def grant(self, *a): raise AssertionError
rr.get_queue = lambda: FakeQueue()

client = TestClient(app, follow_redirects=False)
out = []
def post(slug, label):
    r = client.post(f"/projects/{slug}/run")
    body = r.text
    leaked = [v for v in ("FAKE-SECRET-VALUE-123", "zzz", str(root), "Traceback") if v in body]
    out.append((label, r.status_code, body[:300] if r.status_code >= 400 else r.headers.get("location"), leaked))

for s in ["Bad_Slug", "UPPER", "a_b", "%2e%2e", "a%00b", "a%0A", "ghost"]:
    post(s, f"slug {s}")

def project(secrets=None):
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"], secrets=secrets or []))
    return store

store = project()
post("demo", "no cases")
step = Step(order=0, action=Action.CLICK, target="#go")
store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="t", steps=[step]))
AVAIL["v"] = False
post("demo", "no provider")
AVAIL["v"] = True
post("demo", "no approval")
fs = ProjectStore("frn", root)
fs.save_project(Project(slug="frn", name="Frn", base_url="https://demo.test", allowed_domains=["demo.test"]))
fs.add_case(Case(project="demo", flow_id="g", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="x", steps=[step]))
post("frn", "foreign case in project")
# credentials: a case that types a secret, key declared, value absent in .env
store2 = ProjectStore("cred", root)
store2.save_project(Project(slug="cred", name="Cred", base_url="https://demo.test", allowed_domains=["demo.test"], secrets=[SecretRef(key="MISSING_PW", domains=["demo.test"])]))
store2.add_case(Case(project="cred", flow_id="h", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="s",
                     steps=[Step(order=0, action=Action.FILL, target="#pw", value="{{SECRET:MISSING_PW}}")]))
post("cred", "missing credential")
# small approval
grant_live_case_approval(store, max_actions=1)
post("demo", "approval too small")
grant_live_case_approval(store)
post("demo", "covering approval")
FakeQueue.full = True
post("demo", "queue full")
FakeQueue.full = False

# worker path
from autotester.schema.run_queue import QueueEntry
from autotester.ui.run_queue import RunRefused
import shutil
shutil.rmtree(root / "projects" / "demo" / "approvals.jsonl", ignore_errors=True)
ap = root / "projects" / "demo" / "approvals.jsonl"
if ap.exists(): ap.unlink()
try:
    rr._run_queued(QueueEntry(id="run-X1", project="demo"))
    out.append(("worker without approval", "NO EXCEPTION", "", []))
except RunRefused as e:
    out.append(("worker without approval", "RunRefused", str(e)[:200], [v for v in ("FAKE-SECRET-VALUE-123", str(root)) if v in str(e)]))
except Exception as e:
    out.append(("worker without approval", type(e).__name__, str(e)[:200], []))
print(sys.argv[1], "run dir exists:", (root / "projects" / "demo" / "runs").exists())
for row in out:
    print(json.dumps(row, default=str))

import os, sys, secrets, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); site_port = sys.argv[2]
root.mkdir(parents=True, exist_ok=True)
os.environ["AUTOTESTER_ROOT"] = str(root)
key = secrets.token_hex(32); os.environ["AUTOTESTER_APPROVAL_KEY"] = key
(root / ".env").write_text(f"AUTOTESTER_APPROVAL_KEY={key}\n", encoding="utf-8")
from autotester.auth import accounts, groups
from autotester.auth.access import set_owner
from autotester.schema.project import Project
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.store.project_store import ProjectStore
PW = "correct-horse-battery"
admin = accounts.signup("admin@live.test", PW)
dev = accounts.signup("dev@live.test", PW)
gid = next(g.id for g in groups.list_groups() if g.seed == "developer")
accounts.set_user_groups(dev.id, [gid])
base = f"http://127.0.0.1:{site_port}"
store = ProjectStore("livefix", root)
store.save_project(Project(slug="livefix", name="Live Fixture", base_url=f"{base}/index.html",
    allowed_domains=["127.0.0.1"], headed=True,
    providers={"vision": "gemini", "agent": "mock", "judge": "mock"}))
store.add_case(Case(project="livefix", flow_id="flow_home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
    title="Homepage loads", steps=[Step(order=1, action=Action.NAVIGATE, target=f"{base}/index.html")]))
a = RunApproval(project="livefix", run_kind=ApprovalKind.LIVE_CASE, target=base, scope="local fixture site only",
    max_actions=10000, max_probes=0, wall_clock_s=100000.0, granted_by="t201-live-fixture",
    granted_at="2026-10-13", expires_at="2099-01-01"); a.sign(); store.add_approval(a)
set_owner("livefix", dev.id)
print("admin", admin.id, "dev", dev.id)

"""Checker probe: a role whose sign-in was never attempted, in whole-run reads (PW4)."""
import sys, tempfile, pathlib
W = "D:/autoTesting/.worktrees/g11-port-wiring"
sys.path[:0] = [W + "/src", W + "/tests"]
from role_port_app import build_project, start_app
from role_port_run import ALICE, BOB, SIX, context, declare, sign_in
from autotester.browser.secrets import SecretStore
from autotester.schema.role_step import RoleStep
from autotester.stages.multi_role_session import RoleSessions
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.role_session_port import LiveRolePort
import autotester
print("PKG", autotester.__file__)

tmp = pathlib.Path(tempfile.mkdtemp(prefix="chk_unatt_", dir="D:/autoTesting/.work/tmp"))
app, run_dir = start_app(), tmp / "run"
run_dir.mkdir()
declare(run_dir)
project = build_project(app, tmp)
secrets = SecretStore.load(project, tmp / ".env", strict=False)
try:
    with RoleSessions(project, secrets, run_dir, paths_root=tmp) as roles:
        port = LiveRolePort(roles, [sign_in(app)], success_selectors=["#ok"])
        port.login(ALICE)  # bob is NEVER attempted
        for p in ("/home", "/dashboard", "/reports", "/orders"):
            port.perform(RoleStep(id="v", role_id=ALICE, action=f"goto {p}"))
        summary, findings = run_oracles(context(run_dir, port), SIX)
        for s in summary.statuses:
            print("STATUS", s.oracle.value, s.state.value, s.reason)
        print("FINDINGS", len(findings), sorted({(f.role, f.oracle.value) for f in findings}))
finally:
    app.stop()

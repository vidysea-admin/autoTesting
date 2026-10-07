import os, sys
from fastapi import HTTPException
from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired, prepare_account_grant
from autotester.core.paths import ProjectPaths
from autotester.schema.enums import ApprovalKind
from autotester.ui import routes_runs as rr
from autotester.ui.helpers import _load_project_or_404
os.environ.pop("AUTOTESTER_APPROVAL_KEY", None)   # F-A: no signing key anywhere (.env has none)
store, project = _load_project_or_404("pathlynks")
cases = [c for c in store.list_cases() if c.id == project.login_case_id]
paths = ProjectPaths("pathlynks")
secrets = SecretStore.load(project, paths.env_file, strict=False)
keys = rr._require_declared_values(project, secrets, "pathlynks", cases)
try:
    rr._require_live_case_approval(project, store, cases, secrets, keys); print("F-A RESULT: NOT REFUSED (bad)")
except HTTPException as e: print("F-A refused:", e.status_code, str(e.detail)[:140].replace("\n"," "))
except Exception as e: print("F-A refused (exc):", type(e).__name__, str(e)[:140])
os.environ["AUTOTESTER_APPROVAL_KEY"] = "falsification-only-key"
try:
    prepare_account_grant(project, secrets, kind=ApprovalKind.ADVERSARIAL, account_keys=keys, actions=4, probes=80, wall_clock_s=32.0); print("F-B RESULT: NOT REFUSED (bad)")
except ApprovalRequired as e: print("F-B refused:", str(e)[:140])
a = prepare_account_grant(project, secrets, kind=ApprovalKind.LIVE_CASE, account_keys=keys, actions=4, probes=80, wall_clock_s=32.0)
print("F-B control (LIVE_CASE with key) minted:", a.id[:5])
try:
    prepare_account_grant(project, secrets, kind=ApprovalKind.LIVE_CASE, account_keys={"PATHLYNKS_USER_EMAIL","NOT_DECLARED_KEY"}, actions=4, probes=80, wall_clock_s=32.0); print("F-C RESULT: NOT REFUSED (bad)")
except ApprovalRequired as e: print("F-C refused:", str(e)[:140])

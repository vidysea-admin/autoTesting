"""Probe (not a mutant): does a REFUSED escalation attempt leave an AU22 {actor,target,action} line?
Copied into the throwaway copy's tests/ and run there; writes the audit rows to PROBE_OUT."""
import json, os
from pathlib import Path
import pytest
from auth_harness import ADMIN, account, gate_on, group_id, login
from autotester.auth import groups, accounts

@pytest.fixture()
def root(tmp_path, monkeypatch):
    return gate_on(tmp_path, monkeypatch)

def test_probe_refused_escalation_audit(root):
    account(ADMIN)
    ops_group = groups.create_group("Ops", ["users.manage"])
    uid = account("ops@team.test")
    accounts.set_user_groups(uid, [ops_group.id])
    ops = login("ops@team.test")
    resp = ops.post(f"/admin/users/{uid}/groups", data={"group_id": [group_id("admin")]})
    assert resp.status_code == 403
    rows = [json.loads(ln) for ln in (root / ".work" / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    mine = [r for r in rows if r.get("email") == "ops@team.test" or r.get("actor") == "ops@team.test"]
    Path(os.environ["PROBE_OUT"]).write_text(json.dumps(mine, indent=1), encoding="utf-8")

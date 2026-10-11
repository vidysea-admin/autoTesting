"""T-204 fix cycle 1, AU27 last bullet: "Each refused attempt is audited under AU22 (status 403,
with {actor, target, action}) and holds no password or session value." Both blind checkers
found the refusal returned before `audit.record_action`, so only the request line existed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, gate_on, group_id, login
from fastapi.testclient import TestClient

from autotester.auth import accounts, groups


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _actions(root: Path) -> list[dict[str, str]]:
    path = root / ".work" / "audit.jsonl"
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    return [{k: v for k, v in row.items() if k != "ts"} for row in lines if "action" in row]


def _ops(*perms: str) -> tuple[TestClient, int, int]:
    """An Admin plus a non-admin 'Ops' holding `perms`; returns (ops client, admin id, group id)."""
    admin_id = account(ADMIN)
    ops_group = groups.create_group("Ops", list(perms))
    accounts.set_user_groups(account("ops@team.test"), [ops_group.id])
    return login("ops@team.test"), admin_id, ops_group.id


def test_au27_a_refused_password_reset_is_audited_with_actor_target_action(root: Path) -> None:
    ops, admin_id, _ = _ops("users.manage")
    resp = ops.post(f"/admin/users/{admin_id}/password", data={"password": "SECRET-" + PASSWORD})
    assert resp.status_code == 403
    assert {"actor": "ops@team.test", "target": ADMIN,
            "action": "user.password.refused"} in _actions(root)
    audit = (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")
    assert "SECRET-" not in audit and "argon2" not in audit and "at_session" not in audit


def test_au27_a_refused_admin_membership_change_is_audited(root: Path) -> None:
    ops, _, _ = _ops("users.manage")
    ops_id = accounts.find_user("ops@team.test").id
    resp = ops.post(f"/admin/users/{ops_id}/groups", data={"group_id": [group_id("admin")]})
    assert resp.status_code == 403
    assert {"actor": "ops@team.test", "target": "ops@team.test",
            "action": "user.groups.refused"} in _actions(root)


def test_au27_a_refused_group_edit_create_and_delete_are_audited(root: Path) -> None:
    ops, _, ops_group = _ops("groups.manage")
    assert ops.post(f"/admin/groups/{ops_group}", data={
        "name": "Ops", "permission": ["groups.manage", "settings.manage"]}).status_code == 403
    assert ops.post("/admin/groups", data={
        "name": "Wider", "permission": "settings.manage"}).status_code == 403
    admin_group = group_id("admin")
    refused = ops.post(f"/admin/groups/{admin_group}/delete", data={"confirm": "yes"})
    assert refused.status_code in {400, 403}
    rows = _actions(root)
    assert {"actor": "ops@team.test", "target": "Ops", "action": "group.update.refused"} in rows
    assert {"actor": "ops@team.test", "target": "Wider", "action": "group.create.refused"} in rows
    assert {"actor": "ops@team.test", "target": "Admin/CEO",
            "action": "group.delete.refused"} in rows
    assert groups.get_group(ops_group).permissions == ["groups.manage"]


def test_au27_a_refused_last_admin_action_is_audited_too(root: Path) -> None:
    """AU9 refusals (400) take the same path: the attempt is on record."""
    admin_id = account(ADMIN)
    admin = login(ADMIN)
    assert admin.post(f"/admin/users/{admin_id}/disable").status_code == 400
    assert {"actor": ADMIN, "target": ADMIN, "action": "user.disable.refused"} in _actions(root)

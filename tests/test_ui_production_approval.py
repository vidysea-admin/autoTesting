"""A human UI session can grant a signed production approval (D-088 / D-018).

The signer is the signed-in account (never a form field); an anonymous request, a role
without `access.approve`, or an Authorization-header (API token) request is refused; a
missing signing key fails closed; the row passes `require_project_approval`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import account, gate_on, login, team
from fastapi.testclient import TestClient

from autotester.core.consent import require_project_approval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

FORM = {"scope": "read and click", "expires_at": "2099-09-11T12:00",
        "timezone_offset_minutes": "0", "max_actions": "17", "wall_clock_s": "45"}


def _prod(root: Path, production: bool = True) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"], production=production))
    return store


def test_human_session_grants_a_signed_production_row_that_passes_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = gate_on(tmp_path, monkeypatch)
    store = _prod(root)
    admin = team()["admin"]
    page = admin.get("/projects/demo/env")
    assert "admin@team.test" in page.text and "name='granted_by'" not in page.text
    assert "name='production' value='1'" in page.text
    for kind in ("crawl", "live_case"):   # production not posted: forced on server-side
        resp = admin.post("/projects/demo/crawl-approval",
                          data={**FORM, "kind": kind, "granted_by": "forged"})
        assert resp.status_code == 303
    rows = store.list_approvals()
    assert {r.run_kind for r in rows} == {ApprovalKind.CRAWL, ApprovalKind.LIVE_CASE}
    assert all(r.production and r.granted_by == "admin@team.test"
               and r.is_signed_and_verified for r in rows)
    project = store.load_project()
    for kind in (ApprovalKind.CRAWL, ApprovalKind.LIVE_CASE):
        got = require_project_approval(rows, project=project, kind=kind,
                                       target="https://demo.test", actions=5)
        assert got.run_kind is kind


def test_no_session_or_wrong_role_or_api_token_is_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = gate_on(tmp_path, monkeypatch)
    store = _prod(root)
    account("admin@team.test")
    account("tester@team.test", "tester")
    anon = TestClient(app, follow_redirects=False)
    assert anon.post("/projects/demo/crawl-approval", data=FORM).status_code in (401, 403, 303)
    tester = login("tester@team.test")
    assert tester.post("/projects/demo/crawl-approval", data=FORM).status_code in (403, 404)
    admin = login("admin@team.test")
    token = admin.post("/projects/demo/crawl-approval", data=FORM,
                       headers={"Authorization": "Bearer abc"})
    assert token.status_code == 403
    assert store.list_approvals() == []


def test_missing_signing_key_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = gate_on(tmp_path, monkeypatch)
    store = _prod(root)
    account("admin@team.test")
    admin = login("admin@team.test")
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)
    monkeypatch.setattr("autotester.core.ids._signing_key",
                        lambda: (_ for _ in ()).throw(
                            __import__("autotester.core.ids", fromlist=["x"]).SigningKeyMissing(
                                "AUTOTESTER_APPROVAL_KEY is not set")))
    resp = admin.post("/projects/demo/crawl-approval", data=FORM)
    assert resp.status_code == 400 and "AUTOTESTER_APPROVAL_KEY" in resp.text
    assert store.list_approvals() == []

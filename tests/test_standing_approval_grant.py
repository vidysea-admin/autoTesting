"""D-111: the two grant surfaces (CLI `approve --standing`, the UI form) and the UI Revoke.

The gate itself is in `test_standing_approval.py`. Here: the CLI refuses `--standing`
with a date, without either, for a non-crawl kind, or over the per-run caps; the UI form
has a "Standing, until revoked" option, lists a standing grant plainly and offers a Revoke
that appends a signed `ApprovalRevocation` (a human session only, as granting is).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from autotester.cli import app as cli_app
from autotester.core.consent import ApprovalRequired, require_approval
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.store.approval_revocations import list_revocations
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app as ui_app

runner = CliRunner()
URL = "https://demo.test/"
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
STANDING_FORM = {"scope": "read and click safe controls", "standing": "1",
                 "max_actions": "17", "wall_clock_s": "45"}


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url=URL, allowed_domains=["demo.test"]))
    return s


def _approve(*extra: str, kind: str = "crawl") -> object:
    return runner.invoke(cli_app, [
        "approve", "demo", "--kind", kind, "--target", URL, "--scope", "s",
        "--granted-by", "umesh", *extra])


# -- CLI ---------------------------------------------------------------------

def test_cli_standing_grant_writes_a_signed_row_with_no_expiry(store: ProjectStore) -> None:
    out = _approve("--standing")
    assert out.exit_code == 0, out.output
    row = store.list_approvals()[0]
    assert row.standing and row.expires_at is None and row.is_signed_and_verified
    assert "standing" in out.output.lower()
    far = datetime(2099, 1, 1, tzinfo=UTC)
    assert require_approval([row], project="demo", kind=ApprovalKind.CRAWL, target=URL,
                            actions=10, probes=1, wall_clock_s=60.0, now=far).id == row.id


def test_cli_standing_with_a_date_or_without_either_is_refused(store: ProjectStore) -> None:
    both = _approve("--standing", "--expires", TOMORROW)
    neither = _approve()
    assert both.exit_code == 1 and "either" in both.output.lower()
    assert neither.exit_code == 1 and "--standing" in neither.output
    assert store.list_approvals() == []


def test_cli_standing_adversarial_and_other_kinds_are_refused(store: ProjectStore) -> None:
    for kind in ("adversarial", "live_case", "read"):
        out = _approve("--standing", kind=kind)
        assert out.exit_code == 1 and "standing" in out.output.lower(), kind
    assert store.list_approvals() == []


def test_cli_standing_keeps_the_per_run_caps(store: ProjectStore) -> None:
    assert _approve("--standing", "--max-actions", "2001").exit_code == 1
    assert _approve("--standing", "--wall-clock", "86401").exit_code == 1
    assert store.list_approvals() == []


def test_cli_dated_grant_keeps_its_30_day_ceiling(store: ProjectStore) -> None:
    far = (date.today() + timedelta(days=40)).isoformat()
    assert _approve("--expires", far).exit_code == 1
    assert _approve("--expires", TOMORROW).exit_code == 0
    assert store.list_approvals()[0].standing is False


# -- UI ----------------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    return TestClient(ui_app)


def test_ui_form_offers_standing_and_expiry_is_no_longer_unconditionally_required(
    client: TestClient, store: ProjectStore,
) -> None:
    page = client.get("/projects/demo/env").text
    assert "Standing, until revoked" in page and "name='standing'" in page


def test_ui_standing_grant_is_saved_signed_and_listed_plainly_with_revoke(
    client: TestClient, store: ProjectStore,
) -> None:
    page = client.post("/projects/demo/crawl-approval", data=STANDING_FORM)
    row = store.list_approvals()[0]
    assert row.standing and row.expires_at is None and row.is_signed_and_verified
    assert row.run_kind is ApprovalKind.CRAWL and row.granted_by != ""
    assert "Standing, until revoked" in page.text
    assert f"/projects/demo/crawl-approval/{row.id}/revoke" in page.text and "Revoke" in page.text


def test_ui_identical_standing_submit_is_still_idempotent(
    client: TestClient, store: ProjectStore,
) -> None:
    client.post("/projects/demo/crawl-approval", data=STANDING_FORM)
    client.post("/projects/demo/crawl-approval", data=STANDING_FORM)
    assert len(store.list_approvals()) == 1


def test_ui_standing_with_a_date_or_for_live_case_is_refused(
    client: TestClient, store: ProjectStore,
) -> None:
    dated = client.post("/projects/demo/crawl-approval", data={
        **STANDING_FORM, "expires_at": "2099-01-01T00:00", "timezone_offset_minutes": "0"})
    live = client.post("/projects/demo/crawl-approval", data={**STANDING_FORM, "kind": "live_case"})
    assert dated.status_code == 400 and live.status_code == 400
    assert store.list_approvals() == []


def test_ui_dated_grant_still_requires_an_expiry(client: TestClient, store: ProjectStore) -> None:
    out = client.post("/projects/demo/crawl-approval", data={
        k: v for k, v in STANDING_FORM.items() if k != "standing"})
    assert out.status_code == 400 and store.list_approvals() == []


def test_ui_standing_grant_keeps_the_per_run_caps(client: TestClient, store: ProjectStore) -> None:
    out = client.post("/projects/demo/crawl-approval",
                      data={**STANDING_FORM, "max_actions": "2001"})
    assert out.status_code == 400 and store.list_approvals() == []


def _standing(store: ProjectStore) -> RunApproval:
    return store.add_approval(RunApproval(
        project="demo", run_kind=ApprovalKind.CRAWL, target=URL, scope="s",
        max_actions=5, wall_clock_s=30.0, granted_by="Asha", granted_at="2026-10-28",
        expires_at=None, standing=True).sign())


def test_ui_revoke_appends_a_signed_revocation_and_the_grant_leaves_the_list(
    client: TestClient, store: ProjectStore,
) -> None:
    row = _standing(store)
    page = client.post(f"/projects/demo/crawl-approval/{row.id}/revoke",
                       data={"reason": "project paused"})
    assert page.status_code == 200 and "No crawl approval is in force" in page.text
    assert store.list_approvals() == []
    revs = list_revocations(store.paths.approval_revocations)
    assert len(revs) == 1 and revs[0].approval_id == row.id and revs[0].is_valid
    assert revs[0].reason == "project paused" and "@" in revs[0].revoked_by
    assert store.paths.approvals.read_text().count("\n") == 1  # the grant file is untouched


def test_ui_revoke_of_an_unknown_id_writes_nothing(client: TestClient, store: ProjectStore) -> None:
    out = client.post("/projects/demo/crawl-approval/appr_nope/revoke", data={})
    assert out.status_code in (400, 404)
    assert list_revocations(store.paths.approval_revocations) == []


def test_ui_revoke_refuses_an_api_token_request(client: TestClient, store: ProjectStore) -> None:
    row = _standing(store)
    out = client.post(f"/projects/demo/crawl-approval/{row.id}/revoke", data={},
                      headers={"authorization": "Bearer x"})
    assert out.status_code == 403
    assert len(store.list_approvals()) == 1


def test_a_revoked_standing_grant_no_longer_covers_a_run(
    client: TestClient, store: ProjectStore,
) -> None:
    row = _standing(store)
    client.post(f"/projects/demo/crawl-approval/{row.id}/revoke", data={})
    with pytest.raises(ApprovalRequired):
        require_approval(store.list_approvals(), project="demo", kind=ApprovalKind.CRAWL,
                         target=URL)
    assert isinstance(list_revocations(store.paths.approval_revocations)[0], ApprovalRevocation)

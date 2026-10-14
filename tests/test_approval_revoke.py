"""Signed approval revocation: refused when valid, ignored when unsigned or forged."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.core.consent import ApprovalRequired, require_approval
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()
URL = "https://demo.test/"


def _approval() -> RunApproval:
    exp = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    return RunApproval(project="demo", run_kind=ApprovalKind.CRAWL, target=URL, scope="s",
                       max_actions=5, max_probes=5, wall_clock_s=60.0, granted_by="u",
                       granted_at="2026-10-14", expires_at=exp).sign()


def _revocation(signed: bool, approval: RunApproval) -> ApprovalRevocation:
    row = ApprovalRevocation(approval_id=approval.id, revoked_by="u", reason="r",
                             revoked_at="2026-10-14T00:00:00+00:00")
    return row.sign() if signed else row


def _check(approval: RunApproval, revs: list[ApprovalRevocation]) -> RunApproval:
    return require_approval([approval], project="demo", kind=ApprovalKind.CRAWL, target=URL,
                            actions=1, probes=1, wall_clock_s=1, revocations=revs)


def test_unrevoked_row_is_accepted() -> None:
    a = _approval()
    assert _check(a, []).id == a.id


def test_signed_revocation_refuses_row() -> None:
    a = _approval()
    with pytest.raises(ApprovalRequired, match="revoked"):
        _check(a, [_revocation(True, a)])


def test_unsigned_revocation_is_ignored() -> None:
    a = _approval()
    assert _check(a, [_revocation(False, a)]).id == a.id


def test_forged_revocation_is_ignored() -> None:
    a = _approval()
    forged = _revocation(False, a).model_copy(update={"signature": "ab" * 32})
    assert _check(a, [forged]).id == a.id
    tampered = _revocation(True, a).model_copy(update={"reason": "edited"})
    assert _check(a, [tampered]).id == a.id


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    ProjectStore("demo", tmp_path).save_project(
        Project(slug="demo", name="Demo", base_url=URL, allowed_domains=["demo.test"]))
    return tmp_path


def test_cli_revoke_end_to_end(root: Path) -> None:
    store = ProjectStore("demo", root)
    a = store.add_approval(_approval())
    out = runner.invoke(app, ["revoke", "demo", a.id, "--by", "umesh", "--reason", "no"])
    assert out.exit_code == 0, out.output
    assert store.list_approvals() == []
    assert store.paths.approvals.read_text().count("\n") == 1  # grant file untouched


def test_cli_unknown_id_and_missing_key(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = ProjectStore("demo", root)
    a = store.add_approval(_approval())
    bad = runner.invoke(app, ["revoke", "demo", "appr_nope", "--by", "u", "--reason", "r"])
    assert bad.exit_code == 1
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY")
    nokey = runner.invoke(app, ["revoke", "demo", a.id, "--by", "u", "--reason", "r"])
    assert nokey.exit_code == 1
    assert not store.paths.approval_revocations.exists()

"""Residual callers of the consent gate (D-088 follow-up to approval-prod-gate).

`ai_capture.capture_run` takes a `Project` and uses the production rule (tested in
test_ai_capture.py). The two callers that keep bare `require_approval` can never be aimed at a
project's live target: discovery reads local directories, video review names a provider id.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from run_approval_fixture import project_of
from test_ai_capture import _approval, _capture, _reply

from autotester.cli_video_review import build_gate
from autotester.core.consent import ApprovalRequired
from autotester.schema.ai_target import ReadScope, ScanLimits
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.video_review import ReviewPlan
from autotester.stages.discover import approved_roots
from autotester.stages.video_review import ReviewRefused

LIVE = "https://shop.test/"


def _row(kind: ApprovalKind, target: str) -> RunApproval:
    return RunApproval(project="demo", run_kind=kind, target=target, scope="t", max_actions=99,
        max_probes=99, wall_clock_s=1e5, granted_by="Umesh", granted_at="2026-10-13",
        expires_at="2099-01-01", production=True).sign()


def test_discovery_cannot_be_pointed_at_a_live_url(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    scope = ReadScope(project="demo", project_root=str(root), limits=ScanLimits(),
                      approvals=[_row(ApprovalKind.READ, LIVE)])
    with pytest.raises((OSError, ValueError)):
        approved_roots([Path(LIVE)], scope, _redactor())


def test_discovery_outside_root_is_not_satisfied_by_a_live_target_row(tmp_path: Path) -> None:
    root, other = tmp_path / "proj", tmp_path / "other"
    root.mkdir()
    other.mkdir()
    scope = ReadScope(project="demo", project_root=str(root), limits=ScanLimits(),
                      approvals=[_row(ApprovalKind.LIVE_CASE, LIVE),
                                 _row(ApprovalKind.READ, LIVE)])
    with pytest.raises(ApprovalRequired):
        approved_roots([other], scope, _redactor())


def test_video_review_gate_ignores_live_target_rows() -> None:
    class _Store:
        def list_approvals(self):
            return [_row(ApprovalKind.LIVE_CASE, LIVE), _row(ApprovalKind.CRAWL, LIVE),
                    _row(ApprovalKind.VIDEO_REVIEW, LIVE)]

    class _Provider:
        id = "fake"

    plan = ReviewPlan(frame_count=1, call_count=1, est_cost_usd=0.0)
    gate = build_gate(_Store(), "demo", _Provider(), lambda: plan, lambda: None)
    with pytest.raises(ReviewRefused):
        gate()


def _redactor():
    from autotester.core.redact import Redactor
    return Redactor({})



@pytest.mark.parametrize("variant", ["derived", "production_false"])
def test_production_project_refuses_account_or_nonproduction_row_before_any_send(variant):
    prod = project_of("demo", production=True)
    row = _approval(production=variant != "production_false",
                    granted_by="account-derived:D-068" if variant == "derived" else "umesh")
    sent: list[str] = []
    with pytest.raises(ApprovalRequired, match="production gate"):
        _capture(project=prod, approvals=[row], send=lambda u, p: sent.append(p) or _reply())
    assert sent == []
    ok = _approval(production=True)
    assert len(_capture(project=prod, approvals=[ok]).exchanges) == 1

"""Consent follow-ups from the 2026-10-28 live runs (inbox) and D-111 checker-B N1/N2.

1. the refusal's grant hint prints the declared target, not `[REDACTED]:KEY`;
2. its `--max-probes` is sized from the planned steps with margin, not the bare floor;
3. several covering approvals: the run binds to the widest, not the first match;
4. a same-day re-grant after a revoke is a NEW row (full timestamp), not the revoked id;
5. the UI `standing` field is on only for an explicit `1` / `on`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from autotester.cli import app as cli_app
from autotester.core.consent import (
    MAX_GRANT_PROBES,
    PROBES_PER_ACTION,
    ApprovalRequired,
    require_approval,
)
from autotester.core.exit_codes import ExitCode
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation
from autotester.schema.case import Case
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project
from autotester.stages.execute import probe_request
from autotester.stages.run_gates import LaunchRefused, require_live_case_approval
from autotester.stages.run_service import _report
from autotester.store.approval_revocations import add_revocation
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app as ui_app

URL = "https://demo.test/login"
NOW = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)
runner = CliRunner()


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url=URL, allowed_domains=["demo.test"]))
    return s


def _case(n_steps: int) -> Case:
    steps = [Step(order=i, action=Action.CLICK, target="#x",
                  expected=ExpectedState(visible_text=["ok"])) for i in range(n_steps)]
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="t", steps=steps)


def _row(**kw: object) -> RunApproval:
    fields: dict[str, object] = dict(
        project="demo", run_kind=ApprovalKind.LIVE_CASE, target=URL, scope="s",
        max_actions=100, max_probes=100, wall_clock_s=600.0, granted_by="umesh",
        granted_at="2026-10-28T09:00:00+00:00", expires_at="2026-12-01T00:00:00+00:00")
    fields.update(kw)
    return RunApproval(**fields).sign()  # type: ignore[arg-type]


def _need(rows: list[RunApproval], **kw: object) -> RunApproval:
    args: dict[str, object] = dict(project="demo", kind=ApprovalKind.LIVE_CASE, target=URL,
                                   actions=10, probes=10, wall_clock_s=100.0, now=NOW)
    args.update(kw)
    return require_approval(rows, **args)  # type: ignore[arg-type]


# -- (1) the hint prints the declared target -------------------------------------------------

def test_the_grant_hint_target_survives_the_report_scrub_when_it_is_an_env_value(
    store: ProjectStore,
) -> None:
    """A project whose base_url IS a `.env` value (a login URL) must still show it in the hint."""
    (store.paths.root / ".env").write_text(
        f"DEMO_LOGIN_URL={URL}\nDEMO_PASSWORD=hunter2-real-secret\n", encoding="utf-8")
    message = ('Grant one with:\n  uv run autotester approve demo '
               f'--target "{URL}" x hunter2-real-secret')
    out = _report(store, "demo", ExitCode.REFUSED, message=message).message
    assert out is not None and f'--target "{URL}"' in out
    assert "[REDACTED]:DEMO_LOGIN_URL" not in out
    assert "hunter2-real-secret" not in out and "[REDACTED]:DEMO_PASSWORD" in out


def test_a_secret_that_is_not_the_target_stays_masked_everywhere_else(store: ProjectStore) -> None:
    (store.paths.root / ".env").write_text(f"DEMO_LOGIN_URL={URL}\nDEMO_TOKEN=tok-9f8e7d6c\n",
                                           encoding="utf-8")
    report = _report(store, "demo", ExitCode.INFRA, message="boom tok-9f8e7d6c",
                     case_ids=["tok-9f8e7d6c"])
    assert "tok-9f8e7d6c" not in report.model_dump_json()


# -- (2) the probe estimate in the hint ------------------------------------------------------

def test_the_live_case_hint_probes_are_sized_from_the_planned_steps(
    store: ProjectStore,
) -> None:
    cases = [_case(6), _case(6), _case(6)]   # 18 actions; floor = 3/step (settle + 2 expected)
    floor = probe_request(cases)
    assert floor == 54
    with pytest.raises(LaunchRefused) as exc:
        require_live_case_approval(store.load_project(), store, cases)
    hinted = int(str(exc.value.reason).split("--max-probes ")[1].split()[0])
    assert hinted >= 18 * PROBES_PER_ACTION > floor
    assert hinted <= MAX_GRANT_PROBES


def test_the_hint_keeps_a_larger_floor_and_never_exceeds_the_grant_cap() -> None:
    with pytest.raises(ApprovalRequired, match=r"--max-probes 500\b"):
        _need([], actions=2, probes=500)
    with pytest.raises(ApprovalRequired) as exc:
        _need([], actions=2000, probes=3)
    assert f"--max-probes {MAX_GRANT_PROBES} " in str(exc.value) + " "


def test_the_gate_itself_still_checks_the_floor_not_the_hint() -> None:
    narrow = _row(max_probes=20, max_actions=100)   # >= the floor of 18, < 20 per action of 100
    assert _need([narrow], actions=10, probes=18).id == narrow.id


# -- (3) several covering approvals: the widest wins -----------------------------------------

def test_the_widest_covering_approval_is_bound_not_the_first() -> None:
    narrow = _row(max_actions=20, max_probes=34, wall_clock_s=430.0)
    wide = _row(max_actions=200, max_probes=400, wall_clock_s=1800.0,
                granted_at="2026-10-28T10:00:00+00:00")
    assert _need([narrow, wide]).id == wide.id
    assert _need([wide, narrow]).id == wide.id


def test_a_tie_keeps_the_first_and_a_human_row_beats_a_wider_account_row() -> None:
    a = _row(granted_at="2026-10-28T08:00:00+00:00")
    b = _row(granted_at="2026-10-28T08:30:00+00:00")
    assert _need([a, b]).id == a.id
    derived = _row(granted_by="account-derived:D-068", max_actions=900, max_probes=9000,
                   wall_clock_s=9000.0)
    assert _need([derived, a]).id == a.id


def test_a_non_covering_wide_row_is_never_chosen_over_a_covering_one() -> None:
    covers = _row(max_probes=100)
    expired = _row(max_actions=999, max_probes=9999, wall_clock_s=9999.0,
                   expires_at="2026-10-01T00:00:00+00:00")
    assert _need([expired, covers]).id == covers.id


# -- (4) a same-day re-grant after a revoke is a new row -------------------------------------

def _approve() -> object:
    return runner.invoke(cli_app, [
        "approve", "demo", "--kind", "crawl", "--target", URL, "--scope", "s",
        "--granted-by", "umesh", "--standing", "--max-actions", "50", "--wall-clock", "300"])


def test_a_same_day_regrant_after_a_revoke_gets_a_fresh_id(store: ProjectStore) -> None:
    assert _approve().exit_code == 0
    first = store.list_approvals()[0]
    add_revocation(store.paths.approval_revocations,
                   ApprovalRevocation(approval_id=first.id, revoked_by="umesh",
                                      revoked_at=NOW.isoformat(), reason="paused").sign())
    assert store.list_approvals() == []
    assert _approve().exit_code == 0
    live = store.list_approvals()
    assert len(live) == 1 and live[0].id != first.id
    assert "T" in live[0].granted_at                 # a full timestamp, not a bare date
    assert require_approval(live, project="demo", kind=ApprovalKind.CRAWL, target=URL,
                            actions=10, wall_clock_s=60.0).id == live[0].id


# -- (5) the UI standing flag is explicit ----------------------------------------------------

FORM = {"scope": "read", "max_actions": "17", "wall_clock_s": "45"}


@pytest.mark.parametrize("value, standing", [("1", True), ("on", True), ("ON", True)])
def test_ui_standing_is_on_for_an_explicit_one_or_on(
    store: ProjectStore, value: str, standing: bool,
) -> None:
    out = TestClient(ui_app).post("/projects/demo/crawl-approval", data={**FORM, "standing": value})
    assert out.status_code in (200, 303)
    assert [r.standing for r in store.list_approvals()] == [standing]


@pytest.mark.parametrize("value", ["0", "false", "off", "no", "yes", "true", "x", " "])
def test_ui_standing_is_not_on_for_any_other_non_empty_value(
    store: ProjectStore, value: str,
) -> None:
    """Without standing the grant needs a dated expiry, so it is refused and nothing is saved."""
    out = TestClient(ui_app).post("/projects/demo/crawl-approval", data={**FORM, "standing": value})
    assert out.status_code == 400
    assert store.list_approvals() == []

"""Contract: qa/contracts/multi-role-platform.md MP31 (T-218, build leg on SYNTHETIC run evidence).

The live run with the 8 real role accounts is MP35 [GATED]; nothing here opens a browser."""

from __future__ import annotations

import functools
from datetime import UTC, datetime, timedelta

import pytest

from autotester.schema.approval import RunApproval
from autotester.schema.ceo_run_evidence import CeoRunEvidence, RoleLogin
from autotester.schema.enums import ApprovalKind
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.oracle_context import OracleState, OracleStatus
from autotester.schema.role_account import RoleAccount
from autotester.stages import oracle_registry
from autotester.stages.ceo_run_evidence import run_evidence_problems

START = datetime(2026, 10, 18, 9, 0, tzinfo=UTC)
PLATFORMS = ["parent", "school", "admin"]
PLATFORM_OF = ["parent", "parent", "parent", "school", "school", "school", "admin", "admin"]


def accounts() -> list[RoleAccount]:
    return [RoleAccount(id=f"role{n}", role=f"role {n}", platform_id=PLATFORM_OF[n - 1],
                        username_key=f"ROLE{n}_USER", password_key=f"ROLE{n}_PASS")
            for n in range(1, 9)]


def approval(**over) -> RunApproval:
    fields = {
        "project": "demo", "run_kind": ApprovalKind.LIVE_CASE, "target": "https://demo.test",
        "scope": "headed acceptance run", "max_actions": 500, "max_probes": 50,
        "wall_clock_s": 7200.0, "production": True, "granted_by": "Umesh",
        "granted_at": (START - timedelta(days=1)).isoformat(),
        "expires_at": (START + timedelta(days=2)).isoformat(),
    }
    return RunApproval(**{**fields, **over}).sign()


def evidence(approval_id: str, **over) -> CeoRunEvidence:
    fields = {
        "project_slug": "demo", "started_at": START, "headed": True,
        "run_approval_id": approval_id, "declared_platform_ids": list(PLATFORMS),
        "logins": [RoleLogin(role_account_id=a.id, platform_id=a.platform_id, outcome="ok")
                   for a in accounts()],
        "oracle_table": [
            OracleStatus(oracle=o, module=oracle_registry.module_name(o),
                         state=OracleState.NOT_BUILT if i % 2 else OracleState.RAN)
            for i, o in enumerate(OracleName)],
    }
    return CeoRunEvidence(**{**fields, **over})


def problems(ev: CeoRunEvidence, rows=None, accts=None, platforms=None) -> list[str]:
    return run_evidence_problems(
        ev, role_accounts=accts or accounts(), declared_platform_ids=platforms or PLATFORMS,
        approvals=rows if rows is not None else [granted()])



@functools.cache
def granted() -> RunApproval:
    """One signed approval, built lazily (the signing key is set by a session fixture)."""
    return approval()


def test_mp31_complete_synthetic_evidence_has_no_problems() -> None:
    assert problems(evidence(granted().id)) == []


def test_mp31_a_missing_role_account_fails() -> None:
    ev = evidence(granted().id)
    ev = ev.model_copy(update={"logins": [x for x in ev.logins if x.role_account_id != "role5"]})
    assert any("role5" in p and "0 login outcomes" in p for p in problems(ev))


def test_mp31_fewer_than_eight_onboarded_accounts_fails() -> None:
    seven = accounts()[:7]
    ev = evidence(granted().id)
    ev = ev.model_copy(update={"logins": ev.logins[:7]})
    assert any("7 role accounts" in p for p in problems(ev, accts=seven))


def test_mp31_a_declared_platform_without_a_login_outcome_fails() -> None:
    ev = evidence(granted().id)
    on_admin = {"role7", "role8"}
    kept = [x for x in ev.logins if x.role_account_id not in on_admin]
    ev = ev.model_copy(update={"logins": kept})
    found = problems(ev)
    assert any("declared platform admin has no login outcome" in p for p in found)


def test_mp31_login_outcomes_on_the_wrong_or_an_undeclared_platform_fail() -> None:
    ev = evidence(granted().id)
    bad = list(ev.logins)
    bad[0] = RoleLogin(role_account_id="role1", platform_id="school", outcome="ok")
    bad.append(RoleLogin(role_account_id="ghost", platform_id="parent", outcome="ok"))
    found = problems(ev.model_copy(update={"logins": bad}))
    assert any("role1 logged in on school" in p for p in found)
    assert any("ghost" in p and "not an onboarded" in p for p in found)
    assert any("differ" in p for p in problems(evidence(granted().id, declared_platform_ids=["x"])))


def test_mp31_a_failed_login_is_recorded_not_hidden() -> None:
    ev = evidence(granted().id)
    logins = [x.model_copy(update={"outcome": "failed"}) if x.role_account_id == "role3" else x
              for x in ev.logins]
    assert problems(ev.model_copy(update={"logins": logins})) == []   # completeness, not success


def test_mp31_the_run_approval_must_exist_be_signed_intact_and_unexpired() -> None:
    assert any("not found" in p for p in problems(evidence("appr_missing")))
    unsigned = RunApproval(**{**granted().model_dump(), "signature": ""})
    assert any("unsigned" in p for p in problems(evidence(unsigned.id), rows=[unsigned]))
    forged = approval(max_actions=9999)
    forged.max_actions = 1
    assert any("edited" in p for p in problems(evidence(forged.id), rows=[forged]))
    expired = approval(expires_at=(START - timedelta(hours=1)).isoformat())
    assert any("expired" in p for p in problems(evidence(expired.id), rows=[expired]))
    other = approval(project="other")
    assert any("another project" in p for p in problems(evidence(other.id), rows=[other]))


def test_mp31_a_missing_signing_key_is_a_problem_not_acceptance(monkeypatch) -> None:
    ev = evidence(granted().id)
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY")
    assert any("signing key not configured" in p for p in problems(ev))


def test_mp31_the_run_must_be_headed() -> None:
    assert any("headed" in p for p in problems(evidence(granted().id, headed=False)))


@pytest.mark.parametrize("gone", list(OracleName))
def test_mp31_an_oracle_missing_from_the_table_fails(gone: OracleName) -> None:
    ev = evidence(granted().id)
    table = [row for row in ev.oracle_table if row.oracle is not gone]
    found = problems(ev.model_copy(update={"oracle_table": table}))
    assert found == [f"oracle {gone.value} missing from the table"]


def test_mp31_the_table_covers_every_registry_entry_in_all_three_states() -> None:
    ev = evidence(granted().id)
    assert {row.oracle for row in ev.oracle_table} == set(OracleName)
    assert {row.state for row in ev.oracle_table} == {OracleState.RAN, OracleState.NOT_BUILT}
    twice = ev.model_copy(update={"oracle_table": [*ev.oracle_table, ev.oracle_table[0]]})
    assert any("listed 2 times" in p for p in problems(twice))


def test_mp31_evidence_holds_ids_and_outcomes_only() -> None:
    dumped = evidence(granted().id).model_dump_json()
    assert "ROLE1_PASS" not in dumped and "ROLE1_USER" not in dumped
    with pytest.raises(ValueError):
        RoleLogin(role_account_id="role1", platform_id="parent", outcome="ok", password="x")
    with pytest.raises(ValueError, match="timezone"):
        evidence(granted().id, started_at=datetime(2026, 10, 18, 9, 0))

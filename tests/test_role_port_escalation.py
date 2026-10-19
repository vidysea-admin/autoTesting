"""g11-oracle-wiring W4 (MP19, MPI4): the role-assign transport on the live port, always reverted.

An accepted assign is a P0 finding and is undone in the same run; an unreachable, locked or
unbound control is never pressed. Synthetic data only (MPI2)."""

from __future__ import annotations

import json
import urllib.request

import pytest
from role_port_app import HOST
from role_port_run import ALICE, BOB
from role_port_wired import (
    CONTROLS,
    PLANNED,
    Wired,
    _status,
)

from autotester.schema.authz_probe import (
    AuthzPlan,
    PrivilegeProbe,
    ProbeLog,
    RoleAssignControl,
)
from autotester.schema.enums import WritePolicy
from autotester.schema.multi_role_enums import (
    FindingClass,
    OracleName,
)
from autotester.schema.oracle_context import OracleState
from autotester.schema.role_control import ControlBinding
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.role_port_state import RoleLoginFailed, UnsupportedStep
from autotester.stages.role_session_port import LiveRolePort


def test_w4_an_accepted_assign_is_a_p0_finding_and_is_reverted_in_the_same_run(
        wired_port: Wired, probed_port) -> None:
    _, findings, run_dir, _ = probed_port
    (assigned,) = [f for f in findings if f.finding_id == "authz-priv-admin-make-admin"]
    assert "reverted in run" in assigned.title
    assert assigned.finding_class is FindingClass.PRIVILEGE_ESCALATION
    record = json.loads((run_dir / "authz" / "reverts.jsonl").read_text(encoding="utf-8"))
    assert record["control_id"] == "make-admin" and record["reverted"] is True
    assert wired_port.app.roles["alice"] == "user"                  # back where it was


def test_w4_a_control_the_role_cannot_reach_is_not_pressed(wired_port: Wired, probed_port) -> None:
    findings = probed_port[1]
    assert not [f for f in findings if f.finding_id.endswith("-locked")]
    locked = RoleAssignControl(id="locked", url="/assign-locked")
    assert wired_port.port.can_reach(ALICE, locked) is False


def test_w4_a_control_with_no_binding_is_refused_not_assumed_safe(wired_port: Wired) -> None:
    with pytest.raises(UnsupportedStep):
        wired_port.port.can_reach(ALICE, RoleAssignControl(id="unbound", url="/assign"))


def test_w4_below_allow_writes_the_control_is_listed_unprobed_and_never_pressed(
        wired_port: Wired) -> None:
    store = wired_port.store("g11readonly", write_policy=WritePolicy.READ_ONLY)
    wired_port.grant(store, PLANNED)
    run_dir = wired_port.run_dir("read-only")
    ctx = wired_port.context("g11readonly", run_dir)
    summary, findings = run_oracles(ctx, [OracleName.PRIVILEGE])
    assert _status(summary, OracleName.PRIVILEGE).state is OracleState.RAN
    log = ProbeLog.model_validate_json(
        (run_dir / "authz" / "privilege_log.json").read_text(encoding="utf-8"))
    assert {u.reason.value for u in log.unprobed} == {"write_policy"}
    assert not [f for f in findings if f.finding_id.endswith("-make-admin")]
    assert wired_port.app.roles["alice"] == "user"


def test_w4_on_the_live_port_an_unbound_control_is_listed_unprobed_not_called_refused(
        wired_port: Wired) -> None:
    plan = AuthzPlan(platform_id="app", privilege_probes=[PrivilegeProbe(
        id="admin", higher_role_id=BOB, lower_role_id=ALICE,
        controls=[RoleAssignControl(id="unbound", url="/assign")])])
    wired_port.grant(wired_port.store("g11unbound"), 2)
    run_dir = wired_port.run_dir("unbound", plan)
    ctx = wired_port.context("g11unbound", run_dir)
    summary, findings = run_oracles(ctx, [OracleName.PRIVILEGE])
    assert _status(summary, OracleName.PRIVILEGE).state is OracleState.RAN and findings == []
    log = ProbeLog.model_validate_json(
        (run_dir / "authz" / "privilege_log.json").read_text(encoding="utf-8"))
    assert [(u.item, u.reason.value) for u in log.unprobed] == [
        ("privilege:admin:control_unbound", "transport_error")]
    assert wired_port.app.roles["alice"] == "user"


def test_w4_a_role_signed_out_while_probing_is_unprobed_not_read_as_refused(
        wired_port: Wired) -> None:
    """A dead session lands on the sign-in page, where no control exists: that is not a refusal."""
    expire = urllib.request.Request(
        f"http://127.0.0.1:{wired_port.app.port}/api/expire?u=alice",
        headers={"Host": f"{HOST}:{wired_port.app.port}"})
    urllib.request.urlopen(expire, timeout=5).read()
    control = RoleAssignControl(id="make-admin", url="/assign")
    try:
        with pytest.raises(RoleLoginFailed):
            wired_port.port.can_reach(ALICE, control)
    finally:
        wired_port.port.login(ALICE)
    assert wired_port.port.can_reach(ALICE, control) is True


def test_w4_a_press_whose_outcome_is_not_shown_is_still_undone_and_recorded(
        wired_port: Wired) -> None:
    """The click took (alice is admin) but the proof element never shows: the oracle must revert."""
    wired_port.port._controls["unproven"] = ControlBinding(
        control_id="unproven", assign_locator="#make-admin", accepted_target="#never-shown",
        revert_locator="#undo-admin", reverted_target="#now-user")
    try:
        plan = AuthzPlan(platform_id="app", privilege_probes=[PrivilegeProbe(
            id="admin", higher_role_id=BOB, lower_role_id=ALICE,
            controls=[RoleAssignControl(id="unproven", url="/assign")])])
        wired_port.grant(wired_port.store("g11unproven"), 2)
        run_dir = wired_port.run_dir("unproven", plan)
        summary, findings = run_oracles(wired_port.context("g11unproven", run_dir),
                                        [OracleName.PRIVILEGE])
    finally:
        del wired_port.port._controls["unproven"]
    assert _status(summary, OracleName.PRIVILEGE).state is OracleState.RAN and findings == []
    record = json.loads((run_dir / "authz" / "reverts.jsonl").read_text(encoding="utf-8"))
    assert record["control_id"] == "unproven" and record["reverted"] is True
    assert wired_port.app.roles["alice"] == "user"


def test_w4_two_bindings_for_one_control_are_refused_not_silently_merged() -> None:
    twin = [CONTROLS[0], CONTROLS[0].model_copy(update={"assign_locator": "#other"})]
    with pytest.raises(ValueError):
        LiveRolePort(None, [], controls=twin)  # type: ignore[arg-type]

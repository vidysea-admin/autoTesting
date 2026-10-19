
import pytest
from role_port_run import ALICE, BOB
from role_port_wired import Wired, _status
from autotester.schema.authz_probe import AuthzPlan, PrivilegeProbe, RoleAssignControl
from autotester.schema.multi_role_enums import OracleName
from autotester.stages.oracle_registry import run_oracles
from autotester.schema.oracle_context import OracleContext, OracleState


def test_p1_cap_one_read_then_controls_are_not_navigated(wired_port: Wired) -> None:
    plan = AuthzPlan(platform_id="app", request_cap=1, privilege_probes=[PrivilegeProbe(
        id="admin", higher_role_id=BOB, lower_role_id=ALICE, read_urls=["/api/admin/users"],
        controls=[RoleAssignControl(id="make-admin", url="/assign"),
                  RoleAssignControl(id="locked", url="/assign-locked")])])
    wired_port.grant(wired_port.store("g11cap"), 5)
    run_dir = wired_port.run_dir("cap", plan)
    before = len(wired_port.app.reads)
    summary, findings = run_oracles(wired_port.context("g11cap", run_dir), [OracleName.PRIVILEGE])
    after = wired_port.app.reads[before:]
    print("REQUESTS", after)
    assert [r for r in after if "assign" in r] == [], after


def test_p2_nested_context_validation_does_not_echo_input() -> None:
    with pytest.raises(Exception) as err:
        OracleContext(project_slug="p", run_dir="r", scenario_id="s", role_ids=[], platform_ids=[],
                      declarations={"payment_paths": {"paths": [{"id": "canary-secret-value"}]}})
    print("ERR", str(err.value)[:400])
    assert "canary-secret-value" not in str(err.value)


def test_p1b_cap_one_read_then_no_assign_page_is_loaded(wired_port: Wired) -> None:
    plan = AuthzPlan(platform_id="app", request_cap=1, privilege_probes=[PrivilegeProbe(
        id="admin", higher_role_id=BOB, lower_role_id=ALICE, read_urls=["/api/admin/users"],
        controls=[RoleAssignControl(id="make-admin", url="/assign"),
                  RoleAssignControl(id="locked", url="/assign-locked")])])
    wired_port.grant(wired_port.store("g11capb"), 7)
    run_dir = wired_port.run_dir("capb", plan)
    b = len(wired_port.app.loads)
    run_oracles(wired_port.context("g11capb", run_dir), [OracleName.PRIVILEGE])
    print("LOADS", wired_port.app.loads[b:])
    assert wired_port.app.loads[b:] == []
    assert wired_port.app.roles["alice"] == "user"

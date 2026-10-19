"""T-213 (multi-role-platform.md MP19, MP20, MPI4): the vertical-privilege oracle.

A fixture app with one escalatable endpoint and one correctly refused one; a role-assign control
that works for the lower role and one that does not. Success is P0 and, for a role-assign, is
reverted in the same run with the revert recorded. Every call goes through a counting fake.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from authz_fakes import NOW, PII_MARKERS, ReadOnlyApp, Scaffold, rows
from cross_role_fakes import FakeClock

from autotester.schema.authz_probe import (
    AuthzPlan,
    PrivilegeProbe,
    ProbeLog,
    RevertRecord,
    RoleAssignControl,
    StopReason,
)
from autotester.schema.enums import WritePolicy
from autotester.schema.multi_role_enums import FindingClass, OracleName, Priority
from autotester.stages import oracle_privilege, oracle_tenant
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_registry import run_oracles

OPEN = "/api/admin/users"
SHUT = "/api/admin/settings"


def _control(cid: str) -> RoleAssignControl:
    return RoleAssignControl(id=cid, url=f"/admin/roles/{cid}")


def _probe(**kw: object) -> PrivilegeProbe:
    fields: dict[str, object] = {"id": "admin-area", "higher_role_id": "admin",
                                 "lower_role_id": "teacher", "read_urls": [OPEN, SHUT]}
    return PrivilegeProbe(**{**fields, **kw})  # type: ignore[arg-type]


def _plan(*probes: PrivilegeProbe, **kw: object) -> AuthzPlan:
    return AuthzPlan(platform_id="primary", privilege_probes=list(probes) or [_probe()],
                     request_interval_s=0, **kw)  # type: ignore[arg-type]


def _run(sc: Scaffold, port: object | None = None):
    fc = FakeClock()
    return oracle_privilege.run_privilege_pass(sc.context(port), clock=fc.now, sleep=fc.sleep,
                                               now=NOW)


def _log(sc: Scaffold) -> ProbeLog:
    path = sc.run_dir / "authz" / "privilege_log.json"
    return ProbeLog.model_validate_json(path.read_text("utf-8"))


def _reverts(sc: Scaffold) -> list[RevertRecord]:
    path = sc.run_dir / "authz" / "reverts.jsonl"
    return [RevertRecord.model_validate_json(x) for x in path.read_text("utf-8").splitlines()] \
        if path.exists() else []


@pytest.fixture
def sc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Scaffold:
    return Scaffold(tmp_path, monkeypatch)


# --- MP19: replay of a higher role's reads --------------------------------------------------

def test_mp19_one_escalatable_endpoint_is_p0_and_the_refused_one_is_not(sc: Scaffold) -> None:
    sc.app.serve("teacher", OPEN, data=rows("u", 2))
    sc.app.serve("teacher", SHUT, status=403)
    sc.plan(_plan())
    sc.grant(2)
    findings = _run(sc)
    assert len(findings) == 1
    f = findings[0]
    assert f.finding_class is FindingClass.PRIVILEGE_ESCALATION
    assert priority_for(f.finding_class) is Priority.P0
    assert f.role == "teacher" and f.oracle is OracleName.PRIVILEGE
    assert f.url_template == OPEN and f.steps == ["login teacher", f"goto {OPEN}"]
    assert [(r, p) for r, p in sc.app.reads] == [("teacher", OPEN), ("teacher", SHUT)]


def test_mp19_the_replay_is_a_read_as_the_lower_role_and_keeps_no_response(sc: Scaffold) -> None:
    sc.app.serve("teacher", OPEN, data=rows("u", 2))
    sc.plan(_plan())
    sc.grant(2)
    findings = _run(sc)
    text = sc.tree_text() + json.dumps([f.model_dump(mode="json") for f in findings])
    assert not any(m in text for m in (*PII_MARKERS, "school.invalid"))
    assert sc.app.assigns == [] and sc.app.reverts == []
    assert len(sc.files("authz-priv-admin-area-r1.json")) == 1


def test_mp19_a_clean_app_reports_nothing(sc: Scaffold) -> None:
    sc.app.serve("teacher", OPEN, status=401)
    sc.app.serve("teacher", SHUT, status=403)
    sc.plan(_plan())
    sc.grant(2)
    assert _run(sc) == [] and _log(sc).findings == 0


# --- MP19: role-assign, one attempt per control, reverted -----------------------------------

def _controls(sc: Scaffold) -> None:
    sc.plan(_plan(_probe(read_urls=[], controls=[_control("promote"), _control("invite")])))
    sc.app.accepts = {"promote": True, "invite": False}
    sc.grant(4)


def test_mp19_a_successful_role_assign_is_p0_and_reverted_in_the_same_run(sc: Scaffold) -> None:
    _controls(sc)
    findings = _run(sc)
    assert [f.finding_class for f in findings] == [FindingClass.PRIVILEGE_ESCALATION]
    assert "(reverted in run)" in findings[0].title and findings[0].steps[1] == "click promote"
    assert sc.app.assigns == [("teacher", "promote"), ("teacher", "invite")]  # once per control
    assert sc.app.reverts == [("teacher", "promote")]  # only what succeeded
    [record] = _reverts(sc)
    assert record.reverted is True and record.control_id == "promote"
    assert record.finding_id == findings[0].finding_id and record.timestamp


@pytest.mark.parametrize("result", [False, RuntimeError("revert blew up")])
def test_mp19_a_revert_that_did_not_hold_is_recorded_and_called_out(
        sc: Scaffold, result: bool | Exception) -> None:
    _controls(sc)
    sc.app.revert_result = result
    findings = _run(sc)
    assert len(findings) == 1 and "NOT reverted" in findings[0].title
    [record] = _reverts(sc)
    assert record.reverted is False
    assert "blew up" not in sc.tree_text()


def test_mp19_a_control_the_lower_role_cannot_reach_is_never_attempted(sc: Scaffold) -> None:
    _controls(sc)
    sc.app.reachable = {"promote": False}
    findings = _run(sc)
    assert findings == [] and sc.app.assigns == [("teacher", "invite")]
    assert _reverts(sc) == []


def test_mp19_an_assign_that_raises_still_gets_a_revert_attempt_and_no_finding(
        sc: Scaffold) -> None:
    _controls(sc)
    sc.app.assign_raises = True
    assert _run(sc) == []
    assert sc.app.reverts == [("teacher", "promote"), ("teacher", "invite")]


def test_mp19_an_assign_that_raises_and_whose_revert_failed_is_recorded_for_the_operator(
        sc: Scaffold) -> None:
    """Cycle 1: state unknown after a raising assign must leave a trace, not only a revert try."""
    _controls(sc)
    sc.app.assign_raises = True
    sc.app.revert_result = False
    assert _run(sc) == []
    records = _reverts(sc)
    assert [(r.control_id, r.reverted) for r in records] == [("promote", False),
                                                             ("invite", False)]


def test_mp19_below_allow_writes_no_role_assign_is_sent_and_the_controls_are_named(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ro = Scaffold(tmp_path, monkeypatch, write_policy=WritePolicy.READ_ONLY)
    _controls(ro)
    assert _run(ro) == [] and ro.app.assigns == []
    assert [(u.item, u.reason) for u in _log(ro).unprobed] == [
        ("privilege:admin-area:control_promote", StopReason.WRITE_POLICY),
        ("privilege:admin-area:control_invite", StopReason.WRITE_POLICY)]


def test_mp19_a_port_that_cannot_escalate_names_the_controls_unprobed(sc: Scaffold) -> None:
    sc.app.serve("teacher", OPEN, data=rows("u", 1))
    sc.plan(_plan(_probe(read_urls=[OPEN], controls=[_control("promote")])))
    sc.grant(4)
    findings = _run(sc, port=ReadOnlyApp(sc.app))
    assert len(findings) == 1  # the read still ran
    assert [u.reason for u in _log(sc).unprobed] == [StopReason.NO_ESCALATION_TRANSPORT]


def test_mp19_a_transport_that_cannot_tell_if_a_control_is_reachable_names_it_unprobed(
        sc: Scaffold) -> None:
    """g11-oracle-wiring W4: an error from `can_reach` is "could not tell", never "refused"."""
    class Unsure(type(sc.app)):  # type: ignore[misc]
        def can_reach(self, role_id: str, control: RoleAssignControl) -> bool:
            raise RuntimeError("no binding; this text must not be reported")

    port = Unsure()
    sc.plan(_plan(_probe(read_urls=[OPEN], controls=[_control("promote")])))
    sc.grant(4)
    _run(sc, port=port)
    assert [(u.item, u.reason) for u in _log(sc).unprobed] == [
        ("privilege:admin-area:control_promote", StopReason.TRANSPORT_ERROR)]
    assert port.assigns == [] and "must not be reported" not in sc.tree_text()


# --- MP20 / MPI4 bounds on this oracle -------------------------------------------------------

def test_mp20_the_cap_reserves_room_for_the_revert_so_it_is_never_exceeded(sc: Scaffold) -> None:
    _controls(sc)
    sc.plan(_plan(_probe(read_urls=[], controls=[_control("promote"), _control("invite")]),
                  request_cap=3))
    findings = _run(sc)
    assert len(findings) == 1
    assert sc.app.calls == 2  # promote: assign + revert; invite needs 3 and none is left
    log = _log(sc)
    # the reach look is paid too: promote = look + assign + revert = 3, so invite sends nothing
    assert log.sent == 3 and [(u.item, u.reason) for u in log.unprobed] == [
        ("privilege:admin-area:control_invite", StopReason.REQUEST_CAP)]


def test_mp20_replayed_reads_stop_at_the_cap_and_the_rest_is_named(sc: Scaffold) -> None:
    sc.plan(_plan(_probe(read_urls=[OPEN, SHUT, "/api/admin/logs"]), request_cap=1))
    sc.grant(5)
    _run(sc)
    assert len(sc.app.reads) == 1
    assert [u.item for u in _log(sc).unprobed] == [
        "privilege:admin-area:read_2", "privilege:admin-area:read_3"]


def test_the_two_oracles_share_one_platform_cap_through_their_logs(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", "/api/students?page=1", data=rows("a", 1) + rows("b", 1))
    sc.app.serve("tenant-b", "/api/students?page=1", data=rows("b", 2))
    sc.app.serve("teacher", OPEN, data=rows("u", 1))
    from autotester.schema.authz_probe import TenantProbe
    tenant = TenantProbe(id="students", viewer_role_id="tenant-a", owner_role_id="tenant-b",
                         list_url="/api/students?page=1")
    sc.plan(AuthzPlan(platform_id="primary", tenant_probes=[tenant],
                      privilege_probes=[_probe(read_urls=[OPEN, SHUT])], request_cap=3,
                      request_interval_s=0))
    sc.grant(10)
    fc = FakeClock()
    oracle_tenant.run_tenant_pass(sc.context(), clock=fc.now, sleep=fc.sleep, now=NOW)
    oracle_privilege.run_privilege_pass(sc.context(), clock=fc.now, sleep=fc.sleep, now=NOW)
    assert len(sc.app.reads) == 3  # 2 tenant lists + 1 replay; the second replay is over the cap
    assert [u.reason for u in _log(sc).unprobed] == [StopReason.REQUEST_CAP]


def test_the_approval_gate_covers_reads_and_both_attempt_and_revert(sc: Scaffold) -> None:
    from autotester.stages.authz_probe import plan_size
    plan = _plan(_probe(read_urls=[OPEN], controls=[_control("promote")]))
    assert plan_size(plan) == 3  # one read + (attempt + possible revert)
    sc.plan(plan)
    sc.grant(2)
    from autotester.core.consent import ApprovalRequired
    with pytest.raises(ApprovalRequired):
        _run(sc)
    assert sc.app.calls == 0


def test_registry_runs_the_real_privilege_module(sc: Scaffold) -> None:
    sc.app.serve("teacher", OPEN, data=rows("u", 1))
    sc.plan(_plan())
    sc.grant(2)
    summary, found = run_oracles(sc.context(), [OracleName.PRIVILEGE])
    status = next(s for s in summary.statuses if s.oracle is OracleName.PRIVILEGE)
    assert status.state.value == "ran" and status.finding_count == 1 and len(found) == 1

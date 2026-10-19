"""g11-oracle-wiring W3 (MP18-MP20): tenant and privilege oracles on the live port, gate unchanged.

The T-213 gate (signed ADVERSARIAL RunApproval, probe ceiling) is NOT stubbed: its refusals are
asserted with the app's request counter at zero. Synthetic data only (MPI2)."""

from __future__ import annotations

import json
import urllib.request

import pytest
from imap_fake import PASSWORD
from role_port_app import HOST
from role_port_run import ALICE, BOB
from role_port_wired import (
    AUTHZ,
    CONTROLS,
    PLANNED,
    Wired,
    _status,
)

from autotester.schema.authz_probe import (
    AuthzPlan,
    PrivilegeProbe,
    ProbeLog,
    ProbeReply,
    ReadTransport,
    RoleAssignControl,
)
from autotester.schema.multi_role_enums import (
    FindingClass,
    OracleName,
)
from autotester.schema.oracle_context import OracleState
from autotester.stages.authz_probe import plan_size
from autotester.stages.multi_role_session import PlatformScopeError
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.role_port_authz import rows_from
from autotester.stages.role_port_state import RoleLoginFailed


def test_w3_the_live_port_is_the_probe_transport_the_gate_asks_for(wired_port: Wired) -> None:
    assert isinstance(wired_port.port, ReadTransport)


def test_w3_the_tenant_oracle_finds_the_planted_cross_tenant_row(probed_port) -> None:
    summary, findings, *_ = probed_port
    assert _status(summary, OracleName.TENANT).state is OracleState.RAN
    (leak,) = [f for f in findings if f.finding_class is FindingClass.DATA_LEAK]
    assert leak.role == ALICE and leak.count == 1
    assert leak.leak_evidence is not None and leak.leak_evidence.field_names == ["id", "name"]


def test_w3_the_privilege_oracle_finds_the_read_the_lower_role_should_not_have(probed_port) -> None:
    summary, findings, *_ = probed_port
    assert _status(summary, OracleName.PRIVILEGE).state is OracleState.RAN
    reads = [f for f in findings if f.finding_id.startswith("authz-priv-admin-r")]
    assert [f.finding_id for f in reads] == ["authz-priv-admin-r1"]   # users: 200; audit: 403
    assert reads[0].finding_class is FindingClass.PRIVILEGE_ESCALATION


def test_w3_every_probe_stays_inside_the_planned_count(wired_port: Wired, probed_port) -> None:
    requests = probed_port[3]
    assert 0 < requests <= PLANNED
    log = json.loads((probed_port[2] / "authz" / "tenant_log.json").read_text(encoding="utf-8"))
    assert ProbeLog.model_validate(log).sent <= PLANNED


def test_w3_every_request_the_run_made_is_counted_including_the_role_assign_page_loads(
        wired_port: Wired, probed_port) -> None:
    """The full authz run on the fixture app: the api reads AND the /assign* pages that
    `can_reach` and `assign` load must all be inside what the two oracles paid the budget."""
    _, _, run_dir, reads, loads = probed_port
    sent = sum(ProbeLog.model_validate_json((run_dir / "authz" / f"{o.value}_log.json").read_text(
        encoding="utf-8")).sent for o in AUTHZ)
    assert loads >= 3, "the fixture must have seen the role-assign page loads"
    assert reads + loads <= sent


def _tight_plan(cap: int) -> AuthzPlan:
    return AuthzPlan(platform_id="app", request_cap=cap, privilege_probes=[PrivilegeProbe(
        id="admin", higher_role_id=BOB, lower_role_id=ALICE,
        controls=[RoleAssignControl(id="make-admin", url="/assign"),
                  RoleAssignControl(id="locked", url="/assign-locked")])])


def test_w3_nothing_is_sent_once_the_request_cap_is_spent(wired_port: Wired) -> None:
    """Real scenario: a cap of 3 pays for the first control's look, press and undo, so the second
    control's page must not be loaded at all, and is listed unprobed for `request_cap`."""
    wired_port.grant(wired_port.store("g11cap3"), 6)
    run_dir, before = wired_port.run_dir("cap3", _tight_plan(3)), len(wired_port.app.loads)
    summary, _ = run_oracles(wired_port.context("g11cap3", run_dir), [OracleName.PRIVILEGE])
    assert _status(summary, OracleName.PRIVILEGE).state is OracleState.RAN
    assert wired_port.app.loads[before:] == ["alice:/assign", "alice:/assign"]   # look, press
    log = ProbeLog.model_validate_json(
        (run_dir / "authz" / "privilege_log.json").read_text(encoding="utf-8"))
    assert log.sent == 3 and [(u.item, u.reason.value) for u in log.unprobed] == [
        ("privilege:admin:control_locked", "request_cap")]
    assert wired_port.app.roles["alice"] == "user"


def test_w3_a_cap_too_small_for_a_press_and_its_undo_sends_not_even_the_look(
        wired_port: Wired) -> None:
    """Real scenario: cap 2 cannot cover look + press + undo, so no /assign* page is loaded."""
    wired_port.grant(wired_port.store("g11cap2"), 6)
    run_dir, before = wired_port.run_dir("cap2", _tight_plan(2)), len(wired_port.app.loads)
    run_oracles(wired_port.context("g11cap2", run_dir), [OracleName.PRIVILEGE])
    assert wired_port.app.loads[before:] == []
    log = ProbeLog.model_validate_json(
        (run_dir / "authz" / "privilege_log.json").read_text(encoding="utf-8"))
    assert log.sent == 0 and {u.reason.value for u in log.unprobed} == {"request_cap"}
    assert wired_port.app.roles["alice"] == "user"


def test_w3_a_plan_whose_every_control_is_reachable_stays_inside_the_signed_approval(
        wired_port: Wired, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real scenario: the lower role CAN open both role-assign pages, so each control costs a look,
    a press and an undo. An operator signs an approval for exactly the planned probe count; the run
    must not send more than that (MP20: the planned count is covered by the signed approval)."""
    twin = CONTROLS[0].model_copy(update={"control_id": "make-admin-b"})
    monkeypatch.setitem(wired_port.port._controls, "make-admin-b", twin)
    plan = AuthzPlan(platform_id="app", privilege_probes=[PrivilegeProbe(
        id="admin", higher_role_id=BOB, lower_role_id=ALICE,
        read_urls=["/api/admin/users", "/api/admin/audit"],
        controls=[RoleAssignControl(id="make-admin", url="/assign"),
                  RoleAssignControl(id="make-admin-b", url="/assign")])])
    planned = plan_size(plan)
    assert planned == 8                       # 2 reads + 2 controls x (look + press + undo)
    wired_port.grant(wired_port.store("g11both"), planned)
    run_dir = wired_port.run_dir("both", plan)
    run_oracles(wired_port.context("g11both", run_dir), [OracleName.PRIVILEGE])
    log = ProbeLog.model_validate_json(
        (run_dir / "authz" / "privilege_log.json").read_text(encoding="utf-8"))
    pressed = (run_dir / "authz" / "reverts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(pressed) == 2, "both controls must have been reachable and pressed"
    assert log.planned == planned and log.sent <= planned
    assert wired_port.app.roles["alice"] == "user"


def test_w3_no_foreign_row_or_secret_reaches_disk(wired_port: Wired, probed_port) -> None:
    text = wired_port.tree_text()
    assert "ZZNAME" not in text and PASSWORD not in text and "alice-port-pw" not in text


def test_w3_a_missing_approval_sends_nothing_and_leaves_one_refusal_line(wired_port: Wired) -> None:
    store = wired_port.store("g11noapproval")
    run_dir, before = wired_port.run_dir("no-approval"), len(wired_port.app.reads)
    summary, findings = run_oracles(wired_port.context("g11noapproval", run_dir), AUTHZ)
    assert [_status(summary, o).reason for o in AUTHZ] == ["ApprovalRequired"] * 2
    assert findings == [] and len(wired_port.app.reads) == before
    lines = (store.paths.dir / "authz" / "refusals.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2                       # one per oracle that asked, none sent anything


def test_w3_an_approval_covering_fewer_probes_than_planned_is_refused(wired_port: Wired) -> None:
    wired_port.grant(wired_port.store("g11small"), 2)
    before = len(wired_port.app.reads)
    run_dir = wired_port.run_dir("small")
    summary, findings = run_oracles(wired_port.context("g11small", run_dir), AUTHZ)
    assert [_status(summary, o).reason for o in AUTHZ] == ["ApprovalRequired"] * 2
    assert findings == [] and len(wired_port.app.reads) == before


def test_w3_the_code_ceiling_refuses_an_oversized_plan_whatever_the_approval_says(
        wired_port: Wired) -> None:
    big = AuthzPlan(platform_id="app", privilege_probes=[
        PrivilegeProbe(id=f"p{i}", higher_role_id=BOB, lower_role_id=ALICE,
                       read_urls=[f"/api/admin/r{n}" for n in range(20)]) for i in range(4)])
    wired_port.grant(wired_port.store("g11big"), 500)
    before = len(wired_port.app.reads)
    summary, _ = run_oracles(wired_port.context("g11big", wired_port.run_dir("big", big)), AUTHZ)
    assert [_status(summary, o).reason for o in AUTHZ] == ["ProbeCeilingExceeded"] * 2
    assert len(wired_port.app.reads) == before


def test_w3_a_url_off_the_platform_is_never_requested(wired_port: Wired) -> None:
    before = wired_port.app.offsite_hits
    with pytest.raises(PlatformScopeError):
        wired_port.port.read(ALICE, f"http://127.0.0.1:{wired_port.app.port}/x")
    with pytest.raises(PlatformScopeError):              # a redirect hop is checked too
        wired_port.port.read(ALICE, "/go-away")
    assert wired_port.app.offsite_hits == before


def test_w3_a_logged_out_role_reads_as_401_never_as_the_login_page_200(wired_port: Wired) -> None:
    expire = urllib.request.Request(  # by IP, with the platform's Host header (no DNS in the way)
        f"http://127.0.0.1:{wired_port.app.port}/api/expire?u=alice",
        headers={"Host": f"{HOST}:{wired_port.app.port}"})
    urllib.request.urlopen(expire, timeout=5).read()
    try:
        assert wired_port.port.read(ALICE, "/api/rows").status == 401
    finally:
        wired_port.port.login(ALICE)
    reply = wired_port.port.read(ALICE, "/api/rows")
    assert reply.ok and {r["id"] for r in reply.rows} == {"a1", "a2", "b1"}


def test_w3_rows_come_from_json_only_and_a_page_has_none() -> None:
    assert rows_from('{"results": [{"id": 1}, 7, {"id": 2}]}') == [{"id": 1}, {"id": 2}]
    assert rows_from('[{"id": 1}]') == [{"id": 1}]
    assert rows_from('{"id": 9, "name": "x"}') == [{"id": 9, "name": "x"}]
    assert rows_from("<html>not json</html>") == [] and rows_from("42") == []
    assert len(rows_from(json.dumps([{"i": n} for n in range(500)]))) == 200
    assert ProbeReply(status=200, rows=[{"i": 1}]).model_dump() == {"status": 200}


def test_w3_a_role_whose_sign_in_failed_is_never_probed(wired_port: Wired) -> None:
    """The working half of a broken login must not read as a clean probe (the PW4 rule)."""
    state = wired_port.port._states[ALICE]
    before, state.failed = wired_port.app.reads, "wrong password"
    try:
        with pytest.raises(RoleLoginFailed):
            wired_port.port.read(ALICE, "/api/rows")
    finally:
        state.failed = None
    assert wired_port.app.reads == before

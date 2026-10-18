"""Vertical-privilege oracle: reads and role-assigns a lower role should not be able to do (MP19).

One job: replay reads captured in a higher role's session as a LOWER role (a 2xx is a P0
`PRIVILEGE_ESCALATION`), and make ONE role-assign attempt per control the lower role can reach. An
accepted role-assign is also P0 and is reverted in the same run; whether the revert held is
written to `authz/reverts.jsonl` (`RevertRecord`) and said in the finding's title -- an assign that
could not be undone is still reported, and loudly.

Writes follow the project's `write_policy` (D-018, D-053, not re-litigated): a role-assign attempt
is a write, so below `ALLOW_WRITES` the controls are listed as unprobed (`write_policy`) and
nothing is sent to them. Reads, the approval gate, the ceiling and the request cap are
`stages/authz_probe.py`'s; this module sends nothing a gate has not passed and calls no provider.
The responses are never kept: only the status decides.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime

from autotester.schema.authz_probe import (
    EscalationTransport,
    PrivilegeProbe,
    ProbeLog,
    RevertRecord,
    RoleAssignControl,
    StopReason,
    UnprobedItem,
)
from autotester.schema.enums import WritePolicy
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.stages.authz_probe import (
    AUTHZ_DIR,
    ProbeSession,
    abs_url,
    evidence_url,
    finding_id,
    open_session,
    privilege_cost,
    read_safely,
    write_log,
)
from autotester.stages.leak_evidence import write_finding
from autotester.store.filestore import append_jsonl


def _finding(probe: PrivilegeProbe, prep: ProbeSession, fid: str, title: str, url: str,
             verb: str, target: str) -> MultiRoleFinding:
    template = evidence_url(url)
    return MultiRoleFinding(
        finding_id=fid, finding_class=FindingClass.PRIVILEGE_ESCALATION, title=title[:200],
        role=probe.lower_role_id, platform_id=prep.platform.id, url_template=template,
        steps=[f"login {probe.lower_role_id}", f"{verb} {target}"], count=1,
        oracle=OracleName.PRIVILEGE)


def _replay_reads(probe: PrivilegeProbe, prep: ProbeSession,
                  unprobed: list[UnprobedItem]) -> list[MultiRoleFinding]:
    """Each captured higher-role read, once, as the lower role. 2xx = the lower role got in."""
    found: list[MultiRoleFinding] = []
    for index, url in enumerate(probe.read_urls, start=1):
        stop = prep.budget.take()
        if stop is not None:
            unprobed += [UnprobedItem(item=f"privilege:{probe.id}:read_{i}", reason=stop)
                         for i in range(index, len(probe.read_urls) + 1)]
            return found
        reply = read_safely(prep.transport, probe.lower_role_id, abs_url(prep.platform, url))
        if reply is None:
            unprobed.append(UnprobedItem(item=f"privilege:{probe.id}:read_{index}",
                                         reason=StopReason.TRANSPORT_ERROR))
        elif reply.ok:  # the success decision: a lower role answered 2xx on a higher role's read
            template = evidence_url(url)
            found.append(_finding(
                probe, prep, finding_id("priv", probe.id, f"r{index}"),
                f"Privilege: {probe.lower_role_id} can read what {probe.higher_role_id} reads",
                url, "goto", template))
    return found


def _revert(esc: EscalationTransport, role_id: str, control: RoleAssignControl) -> bool:
    try:
        return bool(esc.revert(role_id, control))
    except Exception:  # the error text could carry a page; only "did not revert" is kept
        return False


def _reaches(esc: EscalationTransport, role_id: str, control: RoleAssignControl) -> bool:
    try:
        return bool(esc.can_reach(role_id, control))
    except Exception:
        return False


def _assign(probe: PrivilegeProbe, control: RoleAssignControl, prep: ProbeSession,
            esc: EscalationTransport) -> MultiRoleFinding | None:
    """One attempt. Accepted => revert at once (outside the cap, reserved up front) and record."""
    try:
        accepted = bool(esc.assign(probe.lower_role_id, control))
    except Exception:  # state unknown: undo if anything took, report nothing we cannot prove
        _revert(esc, probe.lower_role_id, control)
        prep.budget.extra()
        return None
    if not accepted:
        return None
    reverted = _revert(esc, probe.lower_role_id, control)
    prep.budget.extra()
    fid = finding_id("priv", probe.id, control.id)
    append_jsonl(prep.run_dir / AUTHZ_DIR / "reverts.jsonl", RevertRecord(
        finding_id=fid, control_id=control.id, role_id=probe.lower_role_id, reverted=reverted,
        timestamp=datetime.now(UTC).isoformat()))
    state = "reverted in run" if reverted else "NOT reverted, undo by hand"
    return _finding(
        probe, prep, fid,
        f"Privilege: {probe.lower_role_id} assigned a role via {control.id} ({state})",
        control.url, "click", control.id)


def _role_assigns(probe: PrivilegeProbe, prep: ProbeSession, esc: EscalationTransport | None,
                  unprobed: list[UnprobedItem]) -> list[MultiRoleFinding]:
    found: list[MultiRoleFinding] = []
    for control in probe.controls:
        item = f"privilege:{probe.id}:control_{control.id}"
        if prep.project.write_policy is not WritePolicy.ALLOW_WRITES:
            unprobed.append(UnprobedItem(item=item, reason=StopReason.WRITE_POLICY))
        elif esc is None:
            unprobed.append(UnprobedItem(item=item, reason=StopReason.NO_ESCALATION_TRANSPORT))
        elif _reaches(esc, probe.lower_role_id, control):
            stop = prep.budget.take(reserve=2)
            if stop is not None:
                unprobed.append(UnprobedItem(item=item, reason=stop))
                continue
            hit = _assign(probe, control, prep, esc)
            if hit is not None:
                found.append(hit)
    return found


def probe_privilege(prep: ProbeSession) -> tuple[list[MultiRoleFinding], list[UnprobedItem]]:
    """Replay and role-assign for every privilege probe in the plan, within `prep.budget`."""
    esc = prep.transport if isinstance(prep.transport, EscalationTransport) else None
    findings: list[MultiRoleFinding] = []
    unprobed: list[UnprobedItem] = []
    for probe in prep.plan.privilege_probes:
        findings += _replay_reads(probe, prep, unprobed)
        findings += _role_assigns(probe, prep, esc, unprobed)
    return findings, unprobed


def run_privilege_pass(context: OracleContext, *, clock: Callable[[], float],
              sleep: Callable[[float], None], now: datetime | None = None,
              ) -> list[MultiRoleFinding]:
    """Gate, probe, store the findings and the log. A refused plan raises with nothing sent."""
    prep = open_session(context, OracleName.PRIVILEGE, clock=clock, sleep=sleep, now=now)
    before = prep.budget.sent
    findings, unprobed = probe_privilege(prep)
    for finding in findings:
        write_finding(prep.run_dir, finding)
    write_log(prep.run_dir, ProbeLog(
        oracle=OracleName.PRIVILEGE, platform_id=prep.platform.id,
        planned=sum(privilege_cost(p) for p in prep.plan.privilege_probes),
        sent=prep.budget.sent - before, elapsed_s=round(prep.budget.elapsed(), 3),
        findings=len(findings), unprobed=unprobed))
    return findings


def run(context: OracleContext) -> list[MultiRoleFinding]:
    """The oracle registry's entry point (`schema/oracle_context.py`, HOW TO WRITE AN ORACLE)."""
    return run_privilege_pass(context, clock=time.monotonic, sleep=time.sleep)

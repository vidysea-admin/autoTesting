"""Check that one CEO-benchmark run's evidence is complete (MP31, build leg on fixture evidence).

One job: `run_evidence_problems` returns every reason a run record cannot stand as the acceptance
run -- an onboarded role account without a login outcome, a declared platform nobody logged in on,
no valid signed RunApproval, a run that was not headed, or an oracle missing from the ran / not
built / not run table. Empty means complete. It judges completeness only: it never says the run
passed, and it never opens a browser or reads a credential (the real run is MP35, gated).

The approval is judged by the approval itself (`RunApproval.is_intact`,
`is_signed_and_verified`, `is_expired`), the same checks `core/consent.py` relies on; a missing
signing key reads as a problem, never as acceptance.
"""

from __future__ import annotations

from collections import Counter

from autotester.core.ids import SigningKeyMissing
from autotester.schema.approval import RunApproval
from autotester.schema.ceo_run_evidence import CeoRunEvidence
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.role_account import RoleAccount

REQUIRED_ROLE_ACCOUNTS = 8


def _role_problems(evidence: CeoRunEvidence, accounts: list[RoleAccount]) -> list[str]:
    problems: list[str] = []
    if len(accounts) != REQUIRED_ROLE_ACCOUNTS:
        problems.append(
            f"project onboards {len(accounts)} role accounts, the benchmark needs "
            f"{REQUIRED_ROLE_ACCOUNTS}")
    seen = Counter(login.role_account_id for login in evidence.logins)
    by_id = {a.id: a for a in accounts}
    for account in accounts:
        if seen[account.id] != 1:
            problems.append(f"role account {account.id}: {seen[account.id]} login outcomes "
                            "(needs exactly one)")
    for login in evidence.logins:
        account = by_id.get(login.role_account_id)
        if account is None:
            problems.append(f"login for {login.role_account_id}, not an onboarded role account")
        elif account.platform_id != login.platform_id:
            problems.append(f"role account {account.id} logged in on {login.platform_id}, "
                            f"onboarded on {account.platform_id}")
    return problems


def _platform_problems(evidence: CeoRunEvidence, declared: list[str]) -> list[str]:
    problems = [] if sorted(evidence.declared_platform_ids) == sorted(declared) else [
        "evidence platforms differ from the project's declared platforms"]
    covered = {login.platform_id for login in evidence.logins}
    problems += [f"declared platform {p} has no login outcome" for p in declared
                 if p not in covered]
    problems += [f"login outcome on undeclared platform {p}" for p in sorted(covered)
                 if p not in declared]
    return problems


def _approval_problems(evidence: CeoRunEvidence, approvals: list[RunApproval]) -> list[str]:
    row = next((a for a in approvals if a.id == evidence.run_approval_id), None)
    if row is None:
        return [f"RunApproval {evidence.run_approval_id} not found"]
    problems: list[str] = []
    if row.project != evidence.project_slug:
        problems.append("RunApproval belongs to another project")
    if not row.is_intact:
        problems.append("RunApproval was edited after it was granted")
    try:
        if not row.is_signed_and_verified:
            problems.append("RunApproval is unsigned or its signature does not verify")
    except SigningKeyMissing:
        problems.append("RunApproval cannot be verified: signing key not configured")
    if row.is_expired(evidence.started_at):
        problems.append("RunApproval had expired at run start")
    return problems


def _oracle_problems(evidence: CeoRunEvidence) -> list[str]:
    counts = Counter(row.oracle for row in evidence.oracle_table)
    problems = [f"oracle {o.value} missing from the table" for o in OracleName if not counts[o]]
    problems += [f"oracle {o.value} listed {n} times" for o, n in counts.items() if n > 1]
    return problems


def run_evidence_problems(
    evidence: CeoRunEvidence, *, role_accounts: list[RoleAccount],
    declared_platform_ids: list[str], approvals: list[RunApproval],
) -> list[str]:
    """Why this run record is not complete (MP31). Empty means complete."""
    problems = _role_problems(evidence, role_accounts)
    problems += _platform_problems(evidence, declared_platform_ids)
    problems += _approval_problems(evidence, approvals)
    if not evidence.headed:
        problems.append("run was not recorded as headed (a real visible browser)")
    return problems + _oracle_problems(evidence)

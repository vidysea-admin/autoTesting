"""T-217 (multi-role-platform.md MP27, mail half): credentials sent in plain mail.

Each synthetic token shape (numeric code, mixed temporary password, URL query token, URL path
token) is mailed through the loopback fake IMAP server and read by the real reader and the real
cross-role runner; the credential-policy oracle reads the decided mailbox assertion. A finding
names the rule and a count, never the token. Synthetic only (MPI2).
"""

from __future__ import annotations

import imaplib
from datetime import UTC, datetime

import pytest
from cross_role_fakes import FakeClock
from imap_fake import PASSWORD, USER, FakeImap, make_mail

from autotester.schema.credential_policy import POLICY_FILE, CredentialPolicy, PasswordRules
from autotester.schema.cross_role_assertion import (
    AssertionOutcome,
    AssertVerdict,
    CrossRoleAssertion,
    Observation,
)
from autotester.schema.cross_role_scenario import CrossRoleScenario
from autotester.schema.mail_observation import (
    MailObservation,
    MailQuery,
    MailReadResult,
    MailReadState,
)
from autotester.schema.mailbox_ref import MailboxRef
from autotester.schema.multi_role_enums import AssertChannel, Expectation, FindingClass, OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.role_step import RoleStep
from autotester.sources.imap_mailbox import read_mailbox
from autotester.stages.cross_role_runner import run_scenario
from autotester.stages.oracle_credential_policy import credential_findings
from autotester.stages.oracle_mailbox import observation_from_read

RULES = PasswordRules(min_length=10, require_upper=True)
SINCE = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)
REF = MailboxRef(host_key="QA_IMAP_HOST", user_key="QA_IMAP_USER", password_key="QA_IMAP_PASS")
DECLARED = {"QA_IMAP_HOST", "QA_IMAP_USER", "QA_IMAP_PASS"}

# --- MP27 mail half: outgoing messages carrying each synthetic token shape ------------------
SHAPES = {
    "numeric code": "Your verification code: 482913",
    "mixed token": "Your temporary password: Tmp#7aK9xQ2w",
    "url query token": "Reset here: https://app.example.test/reset?token=Zx81Qa7Lm92PqRt",
    "url path token": "Reset here: https://app.example.test/r/Zx81Qa7Lm92PqRtVw4Yb3Nc",
}


class MailPort:
    """Only the mailbox channel is real: it reads the loopback fake IMAP server."""

    def __init__(self, creds: dict[str, str]) -> None:
        self.creds = creds

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        query = MailQuery(since=SINCE, recipient="role.b@example.test")
        result = read_mailbox(REF, query, self.creds, declared_keys=DECLARED,
                              connector=lambda h, p, t: imaplib.IMAP4(h, p, timeout=t))
        return observation_from_read(result, assertion.target)


def _mail_run(body: str, tmp_path, allowed: list[str] | None = None):
    policy = CredentialPolicy(rules=RULES, flows=[], token_allowed_assertions=allowed or [])
    (tmp_path / POLICY_FILE).write_text(policy.model_dump_json(), encoding="utf-8")
    scenario = CrossRoleScenario(
        id="signup", title="Account created", roles=["admin", "parent"],
        steps=[RoleStep(id="create", role_id="admin", action="click #create-account")],
        assertions=[CrossRoleAssertion(
            id="welcome-mail", observer_role_id="parent", channel=AssertChannel.MAILBOX,
            expectation=Expectation.PRESENT, target="welcome", within_s=2, poll_interval_s=0.5)])
    mail = make_mail(1, subject="Welcome to the portal", body=body)
    with FakeImap(mails=[mail]) as server:
        creds = {"QA_IMAP_HOST": server.address, "QA_IMAP_USER": USER, "QA_IMAP_PASS": PASSWORD}
        return run_scenario(scenario, MailPort(creds), FakeClock(), project_slug="demo",
                            run_dir=str(tmp_path), platform_ids=["school"],
                            oracles=[OracleName.CREDENTIAL_POLICY])


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_mp27_a_mail_carrying_a_token_shape_is_a_finding_without_the_value(shape,
                                                                         tmp_path) -> None:
    result = _mail_run(SHAPES[shape], tmp_path)
    (finding,) = result.findings
    assert finding.finding_class is FindingClass.WEAK_CREDENTIAL_POLICY
    assert "credential_in_plain_mail" in finding.title and finding.role == "parent"
    assert finding.count >= 1 and finding.steps == ["click #create-account"]
    secret = SHAPES[shape].split(" ")[-1].split("=")[-1].split("/")[-1]
    assert secret not in result.model_dump_json()


def test_mp27_a_clean_welcome_mail_is_no_finding_and_the_oracle_ran(tmp_path) -> None:
    result = _mail_run("Welcome, your account is ready. Sign in on the portal.", tmp_path)
    assert result.findings == []
    state = {s.oracle: s for s in result.oracle_summary.statuses}[OracleName.CREDENTIAL_POLICY]
    assert state.state is OracleState.RAN


def test_mp27_a_mail_declared_to_carry_a_one_time_link_is_not_flagged(tmp_path) -> None:
    result = _mail_run(SHAPES["url query token"], tmp_path, allowed=["welcome-mail"])
    assert result.findings == []


def test_mp27_the_token_count_is_read_from_the_mail_oracles_own_wording() -> None:
    """The coupling to `oracle_mailbox`: if its detail wording changes, this goes red."""
    read = MailReadResult(state=MailReadState.READ, messages=[
        MailObservation(uid=1, subject="Welcome", credential_token_count=2)])
    detail = observation_from_read(read, "welcome").detail
    outcome = AssertionOutcome(
        assertion_id="welcome-mail", observer_role_id="parent", within_s=2,
        channel=AssertChannel.MAILBOX, expectation=Expectation.PRESENT,
        verdict=AssertVerdict.PASSED, last_observation=detail)
    ctx = OracleContext(project_slug="demo", run_dir=".", scenario_id="s",
                        platform_ids=["school"], assertion_outcomes=[outcome])
    (finding,) = credential_findings(ctx, CredentialPolicy(rules=RULES))
    assert finding.count == 2

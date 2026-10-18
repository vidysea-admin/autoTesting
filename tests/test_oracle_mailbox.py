"""T-212 (multi-role-platform.md MP15-MP17): the mailbox oracle over the cross-role runner.

The unit tests build `OracleContext`s by hand; the end-to-end tests drive `run_scenario` with a
port whose mailbox channel is a real `read_mailbox` against the loopback fake IMAP server, so the
chain assertion -> read -> observation -> verdict -> finding is the shipped one. Synthetic only.
"""

from __future__ import annotations

import imaplib
from datetime import UTC, datetime

import pytest
from cross_role_fakes import FakeClock
from imap_fake import PASSWORD, USER, FakeImap, make_mail

from autotester.schema.cross_role_assertion import (
    AssertionOutcome,
    AssertVerdict,
    CrossRoleAssertion,
    Observation,
)
from autotester.schema.cross_role_scenario import CrossRoleScenario
from autotester.schema.mail_observation import MailQuery, MailReadResult, MailReadState
from autotester.schema.mail_observation import MailUnavailableReason as Why
from autotester.schema.mailbox_ref import MailboxRef
from autotester.schema.multi_role_enums import (
    AssertChannel,
    Expectation,
    FindingClass,
    OracleName,
    Priority,
)
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.role_step import RoleStep
from autotester.sources.imap_mailbox import read_mailbox
from autotester.stages.cross_role_runner import run_scenario
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_mailbox import (
    MailboxIncompleteError,
    MailboxUnavailableError,
    observation_from_read,
    run,
)

REF = MailboxRef(host_key="QA_IMAP_HOST", user_key="QA_IMAP_USER", password_key="QA_IMAP_PASS")
DECLARED = {"QA_IMAP_HOST", "QA_IMAP_USER", "QA_IMAP_PASS"}
SINCE = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)


def _outcome(*, verdict: AssertVerdict, seen: str | None,
             expectation: Expectation = Expectation.PRESENT,
             channel: AssertChannel = AssertChannel.MAILBOX,
             aid: str = "welcome-mail") -> AssertionOutcome:
    return AssertionOutcome(
        assertion_id=aid, observer_role_id="parent", channel=channel, expectation=expectation,
        within_s=5, verdict=verdict, last_observation=seen, reason="never matched")


def _context(*outcomes: AssertionOutcome) -> OracleContext:
    return OracleContext(
        project_slug="demo", run_dir="runs/r1", scenario_id="invite",
        role_ids=["teacher", "parent"], platform_ids=["school"], assertion_outcomes=list(outcomes),
        steps=[RoleStep(id="login", role_id="teacher", action="login school-portal"),
               RoleStep(id="invite", role_id="teacher", action="click #invite-parent")])


def _read(subjects: list[str], *, capped: bool = False) -> MailReadResult:
    from autotester.schema.mail_observation import MailObservation
    return MailReadResult(
        state=MailReadState.READ, matched_on_server=len(subjects) + (3 if capped else 0),
        capped=capped,
        messages=[MailObservation(uid=i + 1, subject=s) for i, s in enumerate(subjects)])


# --- observation_from_read: the bridge from a read to one look at the channel ---------------
def test_a_subject_match_is_a_matched_observation_without_the_subject_text() -> None:
    seen = observation_from_read(_read(["Welcome to the school portal", "Receipt"]), "welcome")
    assert seen.matched is True and "Welcome" not in seen.detail and "2 message" in seen.detail


def test_no_match_after_a_complete_read_is_a_real_not_matched() -> None:
    seen = observation_from_read(_read(["Receipt"]), "welcome")
    assert seen.matched is False and "no subject match" in seen.detail


def test_an_unavailable_read_raises_so_the_runner_cannot_count_it_as_absence() -> None:
    gone = MailReadResult(state=MailReadState.UNAVAILABLE, reason=Why.LOGIN_REFUSED)
    with pytest.raises(MailboxUnavailableError):
        observation_from_read(gone, "welcome")


def test_a_capped_read_with_no_match_is_incomplete_not_absent() -> None:
    with pytest.raises(MailboxIncompleteError):
        observation_from_read(_read(["Receipt"], capped=True), "welcome")
    assert observation_from_read(_read(["Welcome"], capped=True), "welcome").matched is True


def test_a_pattern_that_is_not_a_regex_is_matched_as_plain_text() -> None:
    assert observation_from_read(_read(["Fees (due) [2026]"]), "(due").matched is True


# --- run(): findings only for proven non-delivery -------------------------------------------
def test_a_present_mail_that_a_complete_read_never_found_is_a_mail_not_delivered_finding() -> None:
    failed = _outcome(verdict=AssertVerdict.FAILED, seen="3 messages read; no subject match")
    (finding,) = run(_context(failed))
    assert finding.finding_class is FindingClass.MAIL_NOT_DELIVERED
    assert finding.oracle is OracleName.MAILBOX and finding.role == "parent"
    assert finding.platform_id == "school" and finding.count == 1
    assert finding.steps == ["login school-portal", "click #invite-parent"]
    assert priority_for(finding.finding_class) is Priority.P1 and finding.leak_evidence is None


def test_passed_absent_ui_and_not_run_assertions_make_no_finding() -> None:
    quiet = [
        _outcome(verdict=AssertVerdict.PASSED, seen="1 message"),
        _outcome(verdict=AssertVerdict.FAILED, seen="1 message",
                 expectation=Expectation.ABSENT, aid="a2"),
        _outcome(verdict=AssertVerdict.FAILED, seen="row not shown",
                 channel=AssertChannel.UI, aid="a3"),
        _outcome(verdict=AssertVerdict.NOT_RUN, seen=None, aid="a4"),
    ]
    assert run(_context(*quiet)) == []


def test_an_unobservable_mailbox_is_errored_not_a_clean_pass() -> None:
    with pytest.raises(MailboxUnavailableError):
        run(_context(_outcome(verdict=AssertVerdict.FAILED, seen=None)))


def test_proven_findings_are_kept_when_another_assertion_was_unobservable() -> None:
    proven = _outcome(verdict=AssertVerdict.FAILED, seen="2 messages read; no subject match",
                      aid="a1")
    blind = _outcome(verdict=AssertVerdict.FAILED, seen=None, aid="a2")
    assert [f.finding_id for f in run(_context(proven, blind))] == ["mail-a1"]


def test_the_oracle_is_wired_into_the_registry_as_the_mailbox_module() -> None:
    from autotester.stages.oracle_registry import run_oracles
    ctx = _context(_outcome(verdict=AssertVerdict.FAILED, seen="1 message read; no subject match"))
    summary, findings = run_oracles(ctx, [OracleName.MAILBOX])
    status = next(s for s in summary.statuses if s.oracle is OracleName.MAILBOX)
    assert status.state is OracleState.RAN and status.finding_count == 1 == len(findings)
    blind = _context(_outcome(verdict=AssertVerdict.FAILED, seen=None))
    status = next(s for s in run_oracles(blind, [OracleName.MAILBOX])[0].statuses
                  if s.oracle is OracleName.MAILBOX)
    assert status.state is OracleState.ERRORED and status.reason == "MailboxUnavailableError"


# --- end to end: runner -> mailbox channel -> fake IMAP -> verdict -> finding ----------------
class MailPort:
    """The role-session port with only the mailbox channel real: it reads the fake server."""

    def __init__(self, creds: dict[str, str]) -> None:
        self.creds = creds

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        query = MailQuery(since=SINCE, recipient="role.b@example.test")
        result = read_mailbox(REF, query, self.creds, declared_keys=DECLARED,
                              connector=lambda h, p, t: imaplib.IMAP4(h, p, timeout=t))
        return observation_from_read(result, assertion.target)


def _scenario(target: str, expectation: Expectation) -> CrossRoleScenario:
    return CrossRoleScenario(
        id="invite", title="Teacher invites a parent", roles=["teacher", "parent"],
        steps=[RoleStep(id="invite", role_id="teacher", action="click #invite-parent")],
        assertions=[CrossRoleAssertion(
            id="welcome-mail", observer_role_id="parent", channel=AssertChannel.MAILBOX,
            expectation=expectation, target=target, within_s=2, poll_interval_s=0.5)])


def _creds(server: FakeImap, password: str = PASSWORD) -> dict[str, str]:
    return {"QA_IMAP_HOST": server.address, "QA_IMAP_USER": USER, "QA_IMAP_PASS": password}


def _drive(server: FakeImap, scenario: CrossRoleScenario, password: str = PASSWORD):
    return run_scenario(scenario, MailPort(_creds(server, password)), FakeClock(),
                        project_slug="demo", run_dir="runs/r1", platform_ids=["school"],
                        oracles=[OracleName.MAILBOX])


def test_e2e_the_invite_mail_arrives_so_the_assertion_passes_and_there_is_no_finding() -> None:
    mail = make_mail(1, subject="Welcome to the school portal", body="hi")
    with FakeImap(mails=[mail]) as server:
        result = _drive(server, _scenario("welcome", Expectation.PRESENT))
    assert result.assertions[0].verdict is AssertVerdict.PASSED and result.findings == []
    assert set(server.verbs()) <= {"CAPABILITY", "LOGIN", "EXAMINE", "UID", "LOGOUT"}


def test_e2e_the_invite_mail_never_arrives_so_a_finding_is_raised() -> None:
    with FakeImap(mails=[make_mail(1, subject="Unrelated receipt", body="hi")]) as server:
        result = _drive(server, _scenario("welcome", Expectation.PRESENT))
    assert result.assertions[0].verdict is AssertVerdict.FAILED
    assert [f.finding_class for f in result.findings] == [FindingClass.MAIL_NOT_DELIVERED]


def test_e2e_absent_passes_only_after_a_complete_read_of_the_window() -> None:
    with FakeImap(mails=[make_mail(1, subject="Unrelated receipt", body="hi")]) as server:
        result = _drive(server, _scenario("welcome", Expectation.ABSENT))
    assert result.assertions[0].verdict is AssertVerdict.PASSED


def test_e2e_a_broken_login_is_never_read_as_the_mail_being_absent() -> None:
    with FakeImap(mails=[]) as server:
        absent = _drive(server, _scenario("welcome", Expectation.ABSENT), password="wrong-canary")
        present = _drive(server, _scenario("welcome", Expectation.PRESENT), password="wrong-canary")
    assert absent.assertions[0].verdict is AssertVerdict.FAILED       # absence not proven
    assert present.findings == []                                      # nothing was proven missing
    state = {s.oracle: s for s in present.oracle_summary.statuses}[OracleName.MAILBOX]
    assert state.state is OracleState.ERRORED and "wrong-canary" not in present.model_dump_json()

"""g11-oracle-wiring W2 (MP13, MP14, MP16, MP17, SA9): the mailbox channel on the live port.

The unmodified mailbox oracle drives `LiveRolePort` against a loopback fake IMAP server and a real
Chromium. Synthetic data only (MPI2)."""

from __future__ import annotations

import copy
import imaplib

import pytest
from imap_fake import PASSWORD
from role_port_run import ALICE, BOB
from role_port_wired import (
    Wired,
    _drive,
    _mail_scenario,
    _status,
)

from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.multi_role_enums import (
    AssertChannel,
    Expectation,
    FindingClass,
    OracleName,
)
from autotester.schema.oracle_context import OracleState
from autotester.stages.oracle_mailbox import MailboxUnavailableError
from autotester.stages.role_port_state import ChannelUnavailable


def test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader(wired_port: Wired) -> None:
    result = _drive(wired_port, _mail_scenario(Expectation.PRESENT))
    assert result.assertions[0].verdict.value == "passed" and result.findings == []
    assert set(wired_port.imap.verbs()) <= {"CAPABILITY", "LOGIN", "EXAMINE", "UID", "LOGOUT"}
    assert not wired_port.imap.seen                                 # BODY.PEEK: nothing marked read
    assert PASSWORD not in result.model_dump_json()


def test_w2_a_mail_that_never_arrived_is_a_finding(wired_port: Wired) -> None:
    result = _drive(wired_port, _mail_scenario(Expectation.PRESENT, "invoice"))
    assert result.assertions[0].verdict.value == "failed"
    assert [f.finding_class for f in result.findings] == [FindingClass.MAIL_NOT_DELIVERED]


def test_w2_absent_passes_only_after_a_complete_read_of_the_window(wired_port: Wired) -> None:
    result = _drive(wired_port, _mail_scenario(Expectation.ABSENT, "invoice"))
    assert result.assertions[0].verdict.value == "passed"


def test_w2_an_unreadable_mailbox_is_never_read_as_absence_or_as_a_clean_run(
        wired_port: Wired) -> None:
    def refuse(_host: str, _port: int, _timeout: float) -> imaplib.IMAP4:
        raise ConnectionRefusedError("mailbox down; this text must not be copied")

    blind = copy.copy(wired_port.port)
    blind._mail_connector = refuse
    absent = _drive(wired_port, _mail_scenario(Expectation.ABSENT, "invoice"), blind, "blind-a")
    present = _drive(wired_port, _mail_scenario(Expectation.PRESENT), blind, "blind-p")
    assert absent.assertions[0].verdict.value == "failed"      # absence was not proven
    assert present.findings == []                              # nothing proven missing either
    status = _status(present.oracle_summary, OracleName.MAILBOX)
    assert status.state is OracleState.ERRORED and status.reason == "MailboxUnavailableError"
    assert "must not be copied" not in present.model_dump_json()


def test_w2_a_role_with_no_mailbox_declared_raises_instead_of_matching_nothing(
        wired_port: Wired) -> None:
    look = CrossRoleAssertion(id="m", observer_role_id=BOB, channel=AssertChannel.MAILBOX,
                              expectation=Expectation.PRESENT, target="welcome", within_s=1)
    with pytest.raises(ChannelUnavailable):
        wired_port.port.observe(look)
    blind = copy.copy(wired_port.port)
    blind._mail_connector = lambda *_a: (_ for _ in ()).throw(OSError("down"))
    with pytest.raises(MailboxUnavailableError):
        blind.observe(look.model_copy(update={"observer_role_id": ALICE}))

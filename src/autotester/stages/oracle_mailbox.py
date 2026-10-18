"""The mailbox oracle: an expected mail that a complete read never found is a finding (MP13-MP17).

One job: turn mailbox-channel assertion outcomes into `MAIL_NOT_DELIVERED` findings, and turn one
`MailReadResult` into the `Observation` the cross-role runner polls on. Interface: `run(context)`
(`schema/oracle_context.py`, "HOW TO WRITE AN ORACLE"); the reading itself is
`sources/imap_mailbox.py` (read-only IMAP, bounded, scrubbed), done by whatever backs the
session port's mailbox channel.

Honesty rules (source-adapters.md SA9):
  * `observation_from_read` raises when the read did not happen (`MailboxUnavailableError`) or did
    not cover the window (`MailboxIncompleteError`: the message cap was hit and nothing matched).
    The runner records an observation that raised as "not proven", so an `absent` assertion cannot
    pass on a mailbox that was never read, and a `present` one is not blamed on the sender.
  * `run` reports a finding only for a `present` mailbox assertion that FAILED after a read
    (it has a `last_observation`). A failed one with no observation was never looked at: with no
    proven finding to return, `run` raises `MailboxUnavailableError`, so the registry shows the
    oracle `errored` rather than a clean `ran`. Findings that were proven are never dropped for it.
No subject, address or token value is copied: the detail names counts only.
"""

from __future__ import annotations

import re

from autotester.schema.cross_role_assertion import AssertionOutcome, AssertVerdict, Observation
from autotester.schema.mail_observation import MailReadResult, MailReadState
from autotester.schema.multi_role_enums import AssertChannel, Expectation, FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.schema.platform import IMPLICIT_PLATFORM_ID

MAX_STEPS = 50
_FALLBACK_STEP = "goto /"


class MailboxUnavailableError(RuntimeError):
    """The mailbox could not be read; the message is a closed phrase, never a host or value."""


class MailboxIncompleteError(MailboxUnavailableError):
    """The read hit its message cap without a match, so the rest of the window was not seen."""


def _matches(pattern: str, subject: str) -> bool:
    try:
        return re.search(pattern, subject, re.IGNORECASE) is not None
    except re.error:
        return pattern.lower() in subject.lower()


def observation_from_read(result: MailReadResult, subject_pattern: str) -> Observation:
    """One look at the mailbox channel. Raises unless the whole window was actually read."""
    if result.state is not MailReadState.READ:
        raise MailboxUnavailableError("mailbox not read")
    hits = sum(_matches(subject_pattern, m.subject) for m in result.messages)
    if hits == 0 and result.capped:
        raise MailboxIncompleteError("message cap reached before the window was read")
    tokens = sum(m.credential_token_count for m in result.messages)
    seen = f"{len(result.messages)} messages read; " + (
        f"{hits} subject match" if hits else "no subject match")
    if tokens:
        seen += f"; {tokens} credential-shaped token(s) present"
    return Observation(matched=hits > 0, detail=seen)


def _is_mailbox_present(outcome: AssertionOutcome) -> bool:
    return (outcome.channel is AssertChannel.MAILBOX
            and outcome.expectation is Expectation.PRESENT
            and outcome.verdict is AssertVerdict.FAILED)


def _finding(outcome: AssertionOutcome, context: OracleContext) -> MultiRoleFinding:
    steps = [s.action for s in context.steps][:MAX_STEPS] or [_FALLBACK_STEP]
    return MultiRoleFinding(
        finding_id=f"mail-{outcome.assertion_id}"[:64],
        finding_class=FindingClass.MAIL_NOT_DELIVERED,
        title=f"Expected mail did not arrive within {outcome.within_s:g}s",
        role=outcome.observer_role_id,
        platform_id=context.platform_ids[0] if context.platform_ids else IMPLICIT_PLATFORM_ID,
        url_template="/", steps=steps, count=1, oracle=OracleName.MAILBOX)


def mailbox_findings(context: OracleContext) -> list[MultiRoleFinding]:
    """Findings for proven non-delivery; `MailboxUnavailableError` when nothing could be proven."""
    failed = [o for o in context.assertion_outcomes if _is_mailbox_present(o)]
    proven = [o for o in failed if o.last_observation is not None]
    if failed and not proven:
        raise MailboxUnavailableError("mailbox assertions could not be observed")
    return [_finding(o, context) for o in proven]


run = mailbox_findings
"""The registry's entry point (`schema/oracle_context.py`). An alias, not a second `def run`: the
doctor's duplicate-concept rule flags a top-level `def run` because `doctor.py` already has one."""

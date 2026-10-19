"""The mailbox channel of the live role port (MP13-MP17, MPI5).

One job: answer `observe(assertion)` for `AssertChannel.MAILBOX`. The observer role's
`RoleAccount.mailbox_ref` names three `.env` KEYS; `sources/imap_mailbox.py::read_mailbox` does the
read (read-only IMAP, bounded by since-time, recipient and a message cap, bodies scrubbed) and
`stages/oracle_mailbox.py::observation_from_read` turns the result into an `Observation`. This
module only wires them: it holds no IMAP code, resolves only keys the project DECLARED
(`credentials_from_store`) and never lets a value into an error.

Honesty rules (SA9): a role with no mailbox declared, or no usable recipient, raises
`ChannelUnavailable`; an unreadable mailbox raises `MailboxUnavailableError` and a capped read with
no match raises `MailboxIncompleteError` (both from `observation_from_read`). The runner records an
observation that raised as "not proven", so an `absent` assertion cannot pass on a mailbox that was
never read. The recipient is the mailbox's own login unless the caller maps a role to another
address; the window starts when the port was built (less `SKEW`), so mail from before the run is
not mistaken for mail the run caused.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.mail_observation import MailQuery
from autotester.sources.imap_mailbox import Connector, credentials_from_store, read_mailbox
from autotester.stages.oracle_mailbox import observation_from_read
from autotester.stages.role_port_state import ChannelUnavailable, PortBase


class MailMixin(PortBase):
    """The mailbox half of `LiveRolePort.observe`."""

    _mail_connector: Connector
    _mail_since: datetime
    _mail_recipients: Mapping[str, str]

    def _observe_mailbox(self, assertion: CrossRoleAssertion) -> Observation:
        role_id = assertion.observer_role_id
        ref = self.roles.account(role_id).mailbox_ref
        if ref is None:
            raise ChannelUnavailable(f"role {role_id} has no mailbox declared")
        store = self.roles.secrets
        credentials = credentials_from_store(store, ref)
        recipient = self._mail_recipients.get(role_id) or credentials.get(ref.user_key, "")
        try:
            query = MailQuery(since=self._mail_since, recipient=recipient)
        except ValueError:
            raise ChannelUnavailable(f"role {role_id} has no usable mail recipient") from None
        result = read_mailbox(ref, query, credentials, declared_keys=set(store.keys()),
                              extra_secrets=store.scrub_values(),
                              connector=self._mail_connector)
        return observation_from_read(result, assertion.target)

"""Read a role's mailbox over IMAP: read-only, bounded, scrubbed (SA9, MP16-MP17).

One job: turn a `MailboxRef` (KEYS only) and a `MailQuery` into a `MailReadResult`. Not an EMAIL
`Source`: `sources/email.py` parses local `.eml`/`.mbox` files and this module reuses its parser for
the body, but registers nothing.

Read-only is structural: `_Session` is the only code that talks to the server and it has no method
for a write verb; every command it sends is checked against `ALLOWED_COMMANDS` (LOGIN, EXAMINE,
UID SEARCH, UID FETCH with BODY.PEEK, LOGOUT) and logged, so a caller can show the verbs that were
used (MP34). `EXAMINE` opens the folder read-only, so nothing is marked read, moved or deleted.

Bounded: the server search carries SINCE and TO, the newest `max_messages` are fetched (at most
`MAX_MESSAGE_BYTES` each), results are filtered again locally by recipient and date, and the
connection has a timeout. Scrubbed: the subject and body pass `Redactor.scrub` (the mailbox's own
host, user and password plus any `extra_secrets`); the subject also passes `mask_pii`. A body is
never stored; only which credential-shaped token kinds it held and how many
(`mask_credential_tokens`).

Honest failure: a missing or undeclared key, a refused login, a refused folder, a timeout or an
unreachable host is `unavailable` with a closed reason and never any server text, host or value
(only the exception TYPE decides the reason). It is never "no message arrived".
"""

from __future__ import annotations

import contextlib
import email
import email.policy
import email.utils
import imaplib
import ssl
from collections.abc import Callable, Collection, Mapping
from datetime import UTC, datetime
from typing import Any

from autotester.browser.secrets import SecretStore
from autotester.core.redact import Redactor, mask_pii
from autotester.schema.mail_observation import (
    MailObservation,
    MailQuery,
    MailReadResult,
    MailReadState,
    MailUnavailableReason,
    mask_credential_tokens,
)
from autotester.schema.mailbox_ref import MailboxRef
from autotester.sources.email import parse_eml_bytes

ALLOWED_COMMANDS = frozenset({"LOGIN", "EXAMINE", "UID SEARCH", "UID FETCH BODY.PEEK", "LOGOUT"})
MAX_MESSAGE_BYTES = 262_144
DEFAULT_PORT = 993
SUBJECT_MAX = 200
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_ADDRESS_HEADERS = ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To")
Connector = Callable[[str, int, float], imaplib.IMAP4]


def ssl_connector(host: str, port: int, timeout: float) -> imaplib.IMAP4:
    """The production connection: IMAP over TLS with certificate checks."""
    return imaplib.IMAP4_SSL(host, port, timeout=timeout, ssl_context=ssl.create_default_context())


class _Refused(Exception):
    def __init__(self, reason: MailUnavailableReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class _Session:
    """The only door to the server. It has no method that could write."""

    def __init__(self, client: Any, log: list[str]) -> None:
        self._client = client
        self._log = log

    def _note(self, verb: str) -> None:
        if verb not in ALLOWED_COMMANDS:       # explicit, so `python -O` cannot strip the guard
            raise AssertionError(f"{verb} is not a read-only command")
        self._log.append(verb)

    def login(self, user: str, password: str) -> None:
        self._note("LOGIN")
        try:
            self._client.login(user, password)
        except imaplib.IMAP4.error:
            raise _Refused(MailUnavailableReason.LOGIN_REFUSED) from None

    def examine(self, folder: str) -> None:
        self._note("EXAMINE")
        kind, _ = self._client.select(_quote(folder), readonly=True)
        if kind != "OK":
            raise _Refused(MailUnavailableReason.FOLDER_REFUSED)

    def search(self, query: MailQuery) -> list[int]:
        self._note("UID SEARCH")
        since = query.since.astimezone(UTC)
        day = f"{since.day:02d}-{_MONTHS[since.month - 1]}-{since.year}"
        kind, data = self._client.uid("SEARCH", None, "SINCE", day, "TO", _quote(query.recipient))
        if kind != "OK":
            raise _Refused(MailUnavailableReason.PROTOCOL_ERROR)
        return sorted(int(u) for u in (data[0] or b"").split())

    def fetch(self, uid: int) -> bytes | None:
        self._note("UID FETCH BODY.PEEK")
        kind, data = self._client.uid("FETCH", str(uid), f"(BODY.PEEK[]<0.{MAX_MESSAGE_BYTES}>)")
        if kind != "OK":
            raise _Refused(MailUnavailableReason.PROTOCOL_ERROR)
        return next((item[1] for item in data if isinstance(item, tuple)), None)

    def logout(self) -> None:
        self._note("LOGOUT")
        with contextlib.suppress(imaplib.IMAP4.error, OSError):
            self._client.logout()


def _sent_at(msg: email.message.Message) -> datetime | None:
    try:
        sent = email.utils.parsedate_to_datetime(str(msg.get("Date", "")))
    except (TypeError, ValueError, IndexError):
        return None
    return sent if sent.tzinfo else sent.replace(tzinfo=UTC)


def _addressed_to(msg: email.message.Message, recipient: str) -> bool:
    shown = " ".join(str(v) for h in _ADDRESS_HEADERS for v in msg.get_all(h, []))
    return recipient.lower() in shown.lower()


def _observe(uid: int, raw: bytes, query: MailQuery, redactor: Redactor) -> MailObservation | None:
    """One message as the oracle may remember it; None when it is outside the bounds."""
    try:
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        if not _addressed_to(msg, query.recipient):
            return None
        sent = _sent_at(msg)
        if sent is not None and sent < query.since:
            return None
        subject = " ".join(str(msg.get("Subject", "") or "").split())
    except Exception:  # a header the parser cannot read: remembered as unreadable, not dropped
        return MailObservation(uid=uid, subject="", readable=False)
    parsed = parse_eml_bytes(raw)
    texts = [redactor.scrub(subject), redactor.scrub(parsed.body_text or "")]
    masked_subject, kinds, count = mask_credential_tokens(texts[0])
    _, body_kinds, body_count = mask_credential_tokens(texts[1])
    return MailObservation(
        uid=uid, subject=mask_pii(masked_subject)[:SUBJECT_MAX], received_at=sent,
        readable=parsed.error is None,
        credential_token_kinds=sorted({*kinds, *body_kinds}, key=lambda k: k.value),
        credential_token_count=count + body_count)


def credentials_from_store(store: SecretStore, ref: MailboxRef) -> dict[str, str]:
    """Values of the mailbox keys the PROJECT DECLARED; an undeclared key resolves to nothing."""
    values = store.scrub_values()
    return {k: values[k] for k in (ref.host_key, ref.user_key, ref.password_key)
            if k in store and values.get(k)}


def _unavailable(reason: MailUnavailableReason, log: list[str],
                 keys: list[str] | None = None) -> MailReadResult:
    return MailReadResult(state=MailReadState.UNAVAILABLE, reason=reason,
                          missing_keys=keys or [], command_log=list(log))


def _fetch_all(session: _Session, query: MailQuery, redactor: Redactor) -> MailReadResult:
    found = session.search(query)
    newest = found[-query.max_messages:]
    seen = [(uid, session.fetch(uid)) for uid in newest]
    mails = [_observe(uid, raw, query, redactor) for uid, raw in seen if raw]
    return MailReadResult(state=MailReadState.READ, messages=[m for m in mails if m],
                          matched_on_server=len(found), capped=len(found) > len(newest))


def read_mailbox(ref: MailboxRef, query: MailQuery, credentials: Mapping[str, str], *,
                 declared_keys: Collection[str], extra_secrets: Mapping[str, str] | None = None,
                 connector: Connector = ssl_connector) -> MailReadResult:
    """One bounded, read-only look at a mailbox. Never raises for an unreadable mailbox."""
    keys = [ref.host_key, ref.user_key, ref.password_key]
    log: list[str] = []
    if undeclared := [k for k in keys if k not in declared_keys]:
        return _unavailable(MailUnavailableReason.KEY_UNDECLARED, log, undeclared)
    if missing := [k for k in keys if not credentials.get(k)]:
        return _unavailable(MailUnavailableReason.KEY_MISSING, log, missing)
    redactor = Redactor({**(extra_secrets or {}), **{k: credentials[k] for k in keys}})
    host, _, port = credentials[ref.host_key].partition(":")
    try:
        client = connector(host, int(port or DEFAULT_PORT), query.timeout_s)
        session = _Session(client, log)
        try:
            session.login(credentials[ref.user_key], credentials[ref.password_key])
            session.examine(ref.folder)
            result = _fetch_all(session, query, redactor)
        finally:
            session.logout()
    except _Refused as refused:
        return _unavailable(refused.reason, log)
    except imaplib.IMAP4.error:
        return _unavailable(MailUnavailableReason.PROTOCOL_ERROR, log)
    except (OSError, ValueError):                      # unreachable, timed out, or a bad host value
        return _unavailable(MailUnavailableReason.UNREACHABLE, log)
    return result.model_copy(update={"command_log": list(log)})

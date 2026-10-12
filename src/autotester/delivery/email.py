"""The outbound mail adapters: the dry-run outbox and the SMTP sender (hosting.md HO27, HO29).

One job: put one rendered message in front of one recipient, or fail with a short reason. This is
the ONLY module that imports `smtplib` and the only one that holds the SMTP password, and only for
the length of a `send` call: it is read from the environment mapping at send time and lives in no
model, record, log line or exception text. Failures raise `TransportError` naming the exception
CLASS and the SMTP code, never the server's words (they can echo an address or a credential).

The outbox adapter is the default until the SMTP settings exist; it writes the would-be message
under a directory the caller passes in and sends nothing. Under pytest the default client factory
refuses any non-loopback host, so a dummy host in a test environment cannot reach a network.
"""

from __future__ import annotations

import contextlib
import os
import smtplib
import ssl
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path
from typing import Any, Protocol

from autotester.core.env import TEST_MARKER
from autotester.schema.delivery import (
    LOOPBACK,
    SAFE_KEY,
    DeliveryStatus,
    NotificationPref,
    Recipient,
    RenderedMessage,
    SmtpConfig,
)

ENV_HOST, ENV_PORT = "AUTOTESTER_SMTP_HOST", "AUTOTESTER_SMTP_PORT"
ENV_USER = "AUTOTESTER_SMTP_USER"
ENV_PASSWORD, ENV_FROM = "AUTOTESTER_SMTP_PASSWORD", "AUTOTESTER_SMTP_FROM"
ENV_FROM_NAME, ENV_TLS = "AUTOTESTER_SMTP_FROM_NAME", "AUTOTESTER_SMTP_TLS"
SMTP_TIMEOUT_SECONDS = 15.0
OUTBOX_SENDER = "autotester@localhost.invalid"


class TransportError(Exception):
    """A send failed. The text is safe to store: a class name and a code, never server words."""


class MailTransport(Protocol):
    outcome: DeliveryStatus  # what a successful send is recorded as: SENT or OUTBOXED

    def send(self, to: Recipient, message: RenderedMessage, *, key: str) -> None: ...


class SmtpClient(Protocol):
    def starttls(self, *, context: ssl.SSLContext) -> Any: ...
    def login(self, user: str, password: str) -> Any: ...
    def send_message(self, msg: EmailMessage, from_addr: str, to_addrs: list[str]) -> Any: ...
    def quit(self) -> Any: ...


ClientFactory = Callable[[str, int, bool, float], SmtpClient]


def may_email(pref: NotificationPref | None, *, can_view_report: bool) -> bool:
    """HO26: only a user whose box is ticked AND who still holds `report.view` at send time."""
    return bool(pref and pref.email_run_reports and can_view_report)


def build_mime(config: SmtpConfig | None, to: Recipient, message: RenderedMessage) -> EmailMessage:
    """One plain-text message, one recipient, no attachment, no Cc/Bcc."""
    sender = config.sender_address if config else OUTBOX_SENDER
    name = config.sender_name if config and config.sender_name else "AutoTester"
    msg = EmailMessage()
    msg["From"] = Address(display_name=name, addr_spec=sender)
    msg["To"] = Address(addr_spec=to.address)
    msg["Subject"] = message.subject
    msg["Auto-Submitted"] = "auto-generated"
    msg["Date"] = format_datetime(datetime.now(UTC))
    msg["Message-ID"] = make_msgid(domain=sender.rsplit("@", 1)[1])
    msg.set_content(message.body)
    return msg


def _describe(exc: BaseException) -> str:
    code = getattr(exc, "smtp_code", None)
    return type(exc).__name__ + (f" {code}" if isinstance(code, int) else "")


class OutboxAdapter:
    """Dry run: write `<dir>/<key>.eml` and send nothing. The first write for a key wins."""

    outcome = DeliveryStatus.OUTBOXED

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def send(self, to: Recipient, message: RenderedMessage, *, key: str) -> None:
        if not SAFE_KEY.fullmatch(key) or ".." in key:
            raise TransportError("outbox key is not a safe file name")
        self.directory.mkdir(parents=True, exist_ok=True)
        data = build_mime(None, to, message).as_bytes()
        tmp = self.directory / f".{uuid.uuid4().hex}.tmp"
        tmp.write_bytes(data)
        try:
            os.link(tmp, self.directory / f"{key}.eml")
        except FileExistsError:
            pass  # already outboxed for this key: a retry never writes a second copy
        finally:
            tmp.unlink(missing_ok=True)


def _default_factory(host: str, port: int, implicit_ssl: bool, timeout: float) -> SmtpClient:
    if TEST_MARKER in os.environ and host not in LOOPBACK:
        raise TransportError("live SMTP is disabled under test")
    if implicit_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context())
    return smtplib.SMTP(host, port, timeout=timeout)


class SmtpAdapter:
    """Send over SMTP with STARTTLS or implicit SSL, certificate verification on."""

    outcome = DeliveryStatus.SENT

    def __init__(self, config: SmtpConfig, password_source: Callable[[], str | None], *,
                 client_factory: ClientFactory | None = None,
                 timeout: float = SMTP_TIMEOUT_SECONDS) -> None:
        self._config, self._password_source = config, password_source
        self._factory, self._timeout = client_factory or _default_factory, timeout

    def __repr__(self) -> str:
        return f"SmtpAdapter(host={self._config.host!r}, tls={self._config.tls!r})"

    def send(self, to: Recipient, message: RenderedMessage, *, key: str) -> None:
        cfg, client = self._config, None
        try:
            msg = build_mime(cfg, to, message)
            client = self._factory(cfg.host, cfg.port, cfg.tls == "ssl", self._timeout)
            if cfg.tls == "starttls":
                client.starttls(context=ssl.create_default_context())
            if cfg.user:
                password = self._password_source()
                if not password:
                    raise TransportError("the SMTP password is not set")
                client.login(cfg.user, password)  # the credentials are used here, nowhere else
            client.send_message(msg, cfg.sender_address, [to.address])
        except TransportError:
            raise
        except (smtplib.SMTPException, OSError, ssl.SSLError, ValueError) as exc:
            raise TransportError(_describe(exc)) from None
        finally:
            _close(client)


def _close(client: SmtpClient | None) -> None:
    if client is None:
        return
    with contextlib.suppress(smtplib.SMTPException, OSError):
        client.quit()  # if the connection is already gone there is nothing to add


def smtp_config_from_env(environ: Mapping[str, str]) -> SmtpConfig | None:
    """The transport settings, or None when the host, port or sender is missing or unusable.

    Port 465 is implicit SSL; `_TLS` of 0/none is plain (loopback only); anything else is STARTTLS.
    """
    host, port, sender = (environ.get(k, "").strip() for k in (ENV_HOST, ENV_PORT, ENV_FROM))
    if not (host and port.isdigit() and sender):
        return None
    flag = environ.get(ENV_TLS, "").strip().lower()
    tls = "ssl" if port == "465" else "none" if flag in {"0", "none", "false"} else "starttls"
    try:
        return SmtpConfig(host=host, port=int(port), user=environ.get(ENV_USER) or None,
                          sender_address=sender, tls=tls,
                          sender_name=environ.get(ENV_FROM_NAME) or None)
    except ValueError:
        return None


def is_configured(environ: Mapping[str, str]) -> bool:
    """False shows "email is not configured on this server" (HO27); nothing raises."""
    return smtp_config_from_env(environ) is not None


def select_transport(environ: Mapping[str, str], outbox_dir: Path, *,
                     client_factory: ClientFactory | None = None) -> MailTransport:
    """SMTP when fully configured, otherwise the dry-run outbox. Never connects by itself."""
    config = smtp_config_from_env(environ)
    if config is None:
        return OutboxAdapter(outbox_dir)
    return SmtpAdapter(config, lambda: environ.get(ENV_PASSWORD), client_factory=client_factory)

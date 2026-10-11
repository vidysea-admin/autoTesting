"""Fakes for the report-delivery tests (T-201a): a recording SMTP client, a raising transport,
and a loopback SMTP server that lives inside the test process.

Nothing here reaches a network except `LoopbackSmtp`, which binds 127.0.0.1 on an ephemeral
port. `forbid_real_smtp` makes `smtplib.SMTP`/`SMTP_SSL` raise, so a code path that tried to
open a real connection would fail the test instead of mailing someone (hosting.md HO29).
"""

from __future__ import annotations

import base64
import smtplib
import socket
import socketserver
import threading
from datetime import UTC, datetime
from typing import Any

import pytest

from autotester.delivery.email import TransportError
from autotester.schema.delivery import (
    DeliveryStatus,
    Recipient,
    ReportLabel,
    ReportSummary,
    RunCounts,
    SmtpConfig,
)

REAL_SMTP = smtplib.SMTP  # captured before any patch, used only against 127.0.0.1
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
FAKE_PASSWORD = "unit-test-only-pw-not-a-secret"
CANARY_SECRET = "CANARY-SECRET-9f3a1c"
CANARY_PAGE = "CANARY-PAGE-TEXT-Dashboard-for-student-Asha-Rao"


def forbid_real_smtp(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Patch both smtplib client classes to fail loudly. Returns the list of attempts."""
    attempts: list[str] = []

    def boom(*args: Any, **kwargs: Any) -> None:
        attempts.append("smtplib connection attempted")
        raise AssertionError("a test reached for a real SMTP connection")

    monkeypatch.setattr(smtplib, "SMTP", boom)
    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)
    return attempts


def summary(**over: Any) -> ReportSummary:
    base: dict[str, Any] = dict(
        project_name="Demo Shop", run_id="run-0001", finished_at=NOW,
        counts=RunCounts(passed=7, failed=2, blocked=1, inconclusive=3),
        coverage_line="Coverage: 12 of 15 screens visited (80%)",
        label=ReportLabel.FAILED, report_url="https://tester.example.test/runs/run-0001",
    )
    base.update(over)
    return ReportSummary(**base)


def recipient(user_id: str = "user-a", address: str = "dev.a@example.test") -> Recipient:
    return Recipient(user_id=user_id, address=address)


def config(**over: Any) -> SmtpConfig:
    base: dict[str, Any] = dict(host="smtp.example.test", port=587, user="smtp-user",
                                sender_address="reports@example.test",
                                sender_name="AutoTester", tls="starttls")
    base.update(over)
    return SmtpConfig(**base)


class FakeSmtpClient:
    """Records every call; `fail` maps a method name to the exception it raises."""

    def __init__(self, fail: dict[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.fail = fail or {}
        self.sent: list[Any] = []

    def _do(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))
        if name in self.fail:
            raise self.fail[name]

    def starttls(self, *, context: Any = None) -> None:
        self._do("starttls", context)

    def login(self, user: str, password: str) -> None:
        self._do("login", user, password)

    def send_message(self, msg: Any, from_addr: str, to_addrs: list[str]) -> None:
        self._do("send_message", from_addr, tuple(to_addrs))
        self.sent.append(msg)

    def quit(self) -> None:
        self._do("quit")

    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


class FakeFactory:
    """A client factory; remembers the (host, port, ssl, timeout) it was asked for."""

    def __init__(self, client: FakeSmtpClient | None = None,
                 connect_error: Exception | None = None) -> None:
        self.client = client or FakeSmtpClient()
        self.connect_error = connect_error
        self.requests: list[tuple[str, int, bool, float]] = []

    def __call__(self, host: str, port: int, implicit_ssl: bool, timeout: float) -> FakeSmtpClient:
        self.requests.append((host, port, implicit_ssl, timeout))
        if self.connect_error:
            raise self.connect_error
        return self.client


class RaisingTransport:
    """A transport that raises on every attempt, with an error text that carries a secret."""

    outcome = DeliveryStatus.SENT

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.calls = 0

    def send(self, to: Recipient, message: Any, *, key: str) -> None:
        self.calls += 1
        raise TransportError(self.reason)


class OkTransport:
    outcome = DeliveryStatus.SENT

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, to: Recipient, message: Any, *, key: str) -> None:
        self.sent.append(key)


class _Handler(socketserver.StreamRequestHandler):
    def _say(self, line: str) -> None:
        self.wfile.write(line.encode() + b"\r\n")
        self.wfile.flush()

    def handle(self) -> None:
        server: LoopbackSmtp = self.server.owner  # type: ignore[attr-defined]
        if server.mode == "silent":
            threading.Event().wait(1.5)  # accept, then never speak: the client must time out
            return
        self._say("220 loopback ready")
        data_mode, buf = False, []
        while line := self.rfile.readline():
            text = line.decode(errors="replace").rstrip("\r\n")
            if data_mode:
                if text == ".":
                    server.messages.append("\r\n".join(buf))
                    data_mode, buf = False, []
                    self._say("250 queued")
                else:
                    buf.append(text[1:] if text.startswith("..") else text)
                continue
            verb = text.split(" ", 1)[0].upper()
            if verb == "EHLO":
                self.wfile.write(b"250-loopback\r\n250 AUTH PLAIN\r\n")
                self.wfile.flush()
            elif verb == "AUTH":
                raw = base64.b64decode(text.split()[-1]).split(b"\0")
                server.logins.append(raw[1].decode())
                self._say("235 ok")
            elif verb == "DATA":
                data_mode = True
                self._say("354 go")
            elif verb == "QUIT":
                self._say("221 bye")
                return
            else:
                self._say("250 ok")


class LoopbackSmtp:
    """In-process SMTP server on 127.0.0.1:<ephemeral>; never reachable from outside."""

    def __init__(self, mode: str = "ok") -> None:
        self.mode, self.messages, self.logins = mode, [], []
        self._srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
        self._srv.daemon_threads = True
        self._srv.owner = self  # type: ignore[attr-defined]
        self.port = self._srv.server_address[1]

    def __enter__(self) -> LoopbackSmtp:
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._srv.shutdown()
        self._srv.server_close()


def real_loopback_factory(host: str, port: int, implicit_ssl: bool, timeout: float) -> Any:
    assert host == "127.0.0.1" and not implicit_ssl, "loopback only"
    assert socket.getaddrinfo(host, port)
    return REAL_SMTP(host, port, timeout=timeout)

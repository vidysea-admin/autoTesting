"""The SMTP adapter against fakes only (hosting.md HO27, HO29; team-test-button.md TT8).

A recording fake client covers TLS mode, timeouts, credentials and failure text; one loopback
server in this process covers the real smtplib wire path. No test opens a real connection.
"""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
import time
from contextlib import nullcontext
from email import message_from_string
from pathlib import Path

import pytest
from delivery_fakes import (
    FAKE_PASSWORD,
    FakeFactory,
    FakeSmtpClient,
    LoopbackSmtp,
    config,
    forbid_real_smtp,
    real_loopback_factory,
    recipient,
    summary,
)
from pydantic import ValidationError

from autotester.delivery import email as mail
from autotester.delivery.email import (
    OutboxAdapter,
    SmtpAdapter,
    TransportError,
    build_mime,
    is_configured,
    select_transport,
    smtp_config_from_env,
)
from autotester.delivery.message import render_message
from autotester.schema.delivery import Recipient, RenderedMessage, SmtpConfig

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
ENV = {"AUTOTESTER_SMTP_HOST": "smtp.example.test", "AUTOTESTER_SMTP_PORT": "587",
       "AUTOTESTER_SMTP_USER": "smtp-user", "AUTOTESTER_SMTP_PASSWORD": FAKE_PASSWORD,
       "AUTOTESTER_SMTP_FROM": "reports@example.test", "AUTOTESTER_SMTP_FROM_NAME": "AutoTester"}


@pytest.fixture(autouse=True)
def _no_real_smtp(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    return forbid_real_smtp(monkeypatch)


def _adapter(factory: FakeFactory, cfg: SmtpConfig | None = None, **kw: object) -> SmtpAdapter:
    return SmtpAdapter(cfg or config(), lambda: FAKE_PASSWORD, client_factory=factory, **kw)


def test_starttls_then_login_then_send_with_certificate_verification_on() -> None:
    factory = FakeFactory()
    _adapter(factory).send(recipient(), render_message(summary()), key="k1")
    assert factory.client.names() == ["starttls", "login", "send_message", "quit"]
    ctx = factory.client.calls[0][1][0]
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    assert factory.client.calls[2][1] == ("reports@example.test", ("dev.a@example.test",))


def test_implicit_ssl_mode_skips_starttls_and_asks_the_factory_for_ssl() -> None:
    factory = FakeFactory()
    _adapter(factory, config(port=465, tls="ssl")).send(recipient(), render_message(summary()),
                                                        key="k1")
    assert factory.requests[0][2] is True and "starttls" not in factory.client.names()


def test_every_connection_carries_a_positive_timeout() -> None:
    factory = FakeFactory()
    _adapter(factory).send(recipient(), render_message(summary()), key="k1")
    assert 0 < factory.requests[0][3] <= 60
    assert 0 < mail.SMTP_TIMEOUT_SECONDS <= 60


def test_password_is_read_at_send_time_not_at_construction() -> None:
    reads: list[int] = []
    adapter = SmtpAdapter(config(), lambda: reads.append(1) or FAKE_PASSWORD,
                          client_factory=FakeFactory())
    assert reads == []
    adapter.send(recipient(), render_message(summary()), key="k1")
    assert reads == [1]


def test_authentication_failure_text_carries_neither_password_nor_server_words() -> None:
    err = smtplib.SMTPAuthenticationError(535, f"bad credentials {FAKE_PASSWORD}".encode())
    factory = FakeFactory(FakeSmtpClient(fail={"login": err}))
    with pytest.raises(TransportError) as info:
        _adapter(factory).send(recipient(), render_message(summary()), key="k1")
    text = str(info.value)
    assert FAKE_PASSWORD not in text and "bad credentials" not in text
    assert "SMTPAuthenticationError" in text and "535" in text
    assert "quit" in factory.client.names()  # the connection is closed on failure


@pytest.mark.parametrize("err", [TimeoutError("timed out"), ConnectionRefusedError("refused"),
                                 smtplib.SMTPServerDisconnected("gone"), ssl.SSLError("bad cert")])
def test_connect_failures_become_transport_errors_naming_only_the_class(err: Exception) -> None:
    with pytest.raises(TransportError) as info:
        _adapter(FakeFactory(connect_error=err)).send(recipient(), render_message(summary()),
                                                      key="k1")
    assert type(err).__name__ in str(info.value) and "refused" not in str(info.value)


def test_recipient_refusal_text_does_not_carry_the_address() -> None:
    err = smtplib.SMTPRecipientsRefused({"dev.a@example.test": (550, b"no such user")})
    factory = FakeFactory(FakeSmtpClient(fail={"send_message": err}))
    with pytest.raises(TransportError) as info:
        _adapter(factory).send(recipient(), render_message(summary()), key="k1")
    assert "dev.a@example.test" not in str(info.value)


def test_nothing_is_logged_with_the_password(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    err = smtplib.SMTPAuthenticationError(535, FAKE_PASSWORD.encode())
    for fail in ({}, {"login": err}):
        with pytest.raises(TransportError) if fail else nullcontext():
            _adapter(FakeFactory(FakeSmtpClient(fail=fail))).send(
                recipient(), render_message(summary()), key="k1")
    assert FAKE_PASSWORD not in caplog.text and FAKE_PASSWORD not in repr(_adapter(FakeFactory()))


def test_plain_text_login_is_refused_for_a_non_loopback_host() -> None:
    with pytest.raises(ValidationError):
        config(tls="none", host="smtp.example.test")
    assert config(tls="none", host="127.0.0.1").tls == "none"


def test_default_factory_never_connects_under_test_even_with_a_dummy_host(
        _no_real_smtp: list[str]) -> None:
    adapter = SmtpAdapter(config(host="smtp.example.invalid"), lambda: FAKE_PASSWORD)
    with pytest.raises(TransportError, match="disabled under test"):
        adapter.send(recipient(), render_message(summary()), key="k1")
    assert _no_real_smtp == []


def test_loopback_server_receives_one_well_formed_message_over_real_smtplib() -> None:
    with LoopbackSmtp() as srv:
        cfg = config(host="127.0.0.1", port=srv.port, tls="none")
        SmtpAdapter(cfg, lambda: FAKE_PASSWORD, client_factory=real_loopback_factory,
                    timeout=3.0).send(recipient(), render_message(summary()), key="k1")
        assert srv.logins == ["smtp-user"] and len(srv.messages) == 1
        msg = message_from_string(srv.messages[0])
    assert msg["To"] == "dev.a@example.test" and msg["Subject"].startswith("AutoTester report")
    assert msg["Cc"] is None and msg["Bcc"] is None and not msg.is_multipart()
    assert msg["Auto-Submitted"] == "auto-generated"


def test_silent_server_trips_the_timeout_instead_of_hanging() -> None:
    with LoopbackSmtp("silent") as srv:
        cfg = config(host="127.0.0.1", port=srv.port, tls="none")
        started = time.monotonic()
        with pytest.raises(TransportError):
            SmtpAdapter(cfg, lambda: FAKE_PASSWORD, client_factory=real_loopback_factory,
                        timeout=0.3).send(recipient(), render_message(summary()), key="k1")
    assert time.monotonic() - started < 3.0


@pytest.mark.parametrize("bad", ["a@x.test\r\nBcc: evil@x.test", "a@x.test\nCc: e@x.test",
                                 "a b@x.test", "a@x", "@x.test", "a@@x.test", "<a@x.test>",
                                 "a@x.test, b@x.test", "", "a@x.test;b@x.test"])
def test_recipient_address_validation_rejects_injection_and_malformed(bad: str) -> None:
    with pytest.raises(ValidationError):
        Recipient(user_id="user-a", address=bad)


def test_message_headers_have_exactly_one_recipient_and_no_extra_header() -> None:
    msg = build_mime(config(), recipient(), render_message(summary()))
    assert [a.addr_spec for a in msg["To"].addresses] == ["dev.a@example.test"]
    assert {k.lower() for k in msg} == {"from", "to", "subject", "auto-submitted",
                                                "date", "message-id", "mime-version",
                                                "content-type", "content-transfer-encoding"}


def test_rendered_message_refuses_a_line_break_in_the_subject() -> None:
    with pytest.raises(ValidationError):
        RenderedMessage(subject="hi\r\nBcc: evil@x.test", body="b")


def test_sender_name_with_a_line_break_is_refused_at_config() -> None:
    with pytest.raises(ValidationError):
        config(sender_name="Auto\r\nBcc: evil@x.test")


def test_config_from_env_maps_ports_to_tls_modes_and_handles_absence() -> None:
    assert smtp_config_from_env({}) is None and is_configured({}) is False
    assert smtp_config_from_env({"AUTOTESTER_SMTP_HOST": "h"}) is None
    cfg = smtp_config_from_env(ENV)
    assert cfg and cfg.tls == "starttls" and cfg.port == 587 and cfg.sender_name == "AutoTester"
    ssl_cfg = smtp_config_from_env({**ENV, "AUTOTESTER_SMTP_PORT": "465"})
    assert ssl_cfg is not None and ssl_cfg.tls == "ssl"
    assert is_configured(ENV) is True


def test_select_transport_is_the_outbox_unless_fully_configured(tmp_path: Path) -> None:
    assert isinstance(select_transport({}, tmp_path), OutboxAdapter)
    assert isinstance(select_transport({"AUTOTESTER_SMTP_PORT": "x"}, tmp_path), OutboxAdapter)
    assert isinstance(select_transport(ENV, tmp_path), SmtpAdapter)


def test_selected_smtp_adapter_reads_the_password_from_the_environment_mapping(
        tmp_path: Path) -> None:
    env = dict(ENV)
    factory = FakeFactory()
    adapter = select_transport(env, tmp_path, client_factory=factory)
    env["AUTOTESTER_SMTP_PASSWORD"] = "rotated-test-pw"
    adapter.send(recipient(), render_message(summary()), key="k1")
    assert factory.client.calls[1][1] == ("smtp-user", "rotated-test-pw")


def test_only_the_email_adapter_imports_smtplib() -> None:
    offenders = [str(p.relative_to(SRC)) for p in SRC.rglob("*.py")
                 if re.search(r"^\s*(import smtplib|from smtplib)", p.read_text("utf-8"), re.M)
                 and p.relative_to(SRC).as_posix() != "delivery/email.py"]
    assert offenders == []
    assert "import smtplib" in (SRC / "delivery" / "email.py").read_text("utf-8")

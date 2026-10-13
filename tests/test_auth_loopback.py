"""AU17: the login-off switch is honoured only on loopback and never when hosted (the pure
`auth.loopback` module, re-exported by `auth.config`)."""

from __future__ import annotations

import sys

import pytest

from autotester.auth import config, loopback


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AUTOTESTER_HOSTED", "AUTOTESTER_AUTH_DISABLED", "UVICORN_HOST"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sys, "argv", ["prog"])


def test_honoured_on_loopback_when_not_hosted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
    assert loopback.auth_disabled() is True


def test_ignored_when_hosted_even_on_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    assert loopback.auth_disabled() is False


@pytest.mark.parametrize("host", ["0.0.0.0", "10.0.0.5", "::"])
def test_ignored_when_bound_off_loopback(monkeypatch: pytest.MonkeyPatch, host: str) -> None:
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
    monkeypatch.setattr(sys, "argv", ["prog", "--host", host])
    assert loopback.auth_disabled() is False


def test_off_without_the_switch() -> None:
    assert loopback.auth_disabled() is False


def test_config_reexports_the_same_functions() -> None:
    assert config.auth_disabled is loopback.auth_disabled
    assert config.bind_host is loopback.bind_host and config.hosted is loopback.hosted

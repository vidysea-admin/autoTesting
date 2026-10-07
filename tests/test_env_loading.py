"""The repo-root `.env` loader — AT-228, and the leak the fix nearly introduced.

Two properties, and the second is the one that bit:

1. The CLI and the UI must agree about which credentials this machine has. They
   did not: `ui/app.py` loaded the repo-root `.env` and no CLI entry point did,
   so `autotester providers` answered `mock` while a working key sat on disk —
   and a HUMAN_GATE was filed against a blocker that did not exist.
2. **Real credentials must never enter a test process.** The first fix put the
   load in a typer callback, so every `CliRunner` invocation in this suite
   loaded the real `.env` into `os.environ` permanently, and four provider tests
   asserting "no key present" silently started running with a real key.
"""

from __future__ import annotations

import os
from pathlib import Path

from autotester.core.env import TEST_MARKER, load_repo_env


def test_a_test_process_never_loads_real_credentials(tmp_path: Path) -> None:
    """The guard, asserted directly. pytest sets PYTEST_CURRENT_TEST for every
    test, so this runs in exactly the condition it protects."""
    (tmp_path / ".env").write_text("LEAKED_KEY=super-secret\n", encoding="utf-8")

    assert TEST_MARKER in os.environ, "the guard's own precondition is absent"
    assert load_repo_env(tmp_path) == []
    assert "LEAKED_KEY" not in os.environ


def test_outside_a_test_process_it_loads_and_returns_KEYS_ONLY(
    tmp_path: Path, monkeypatch,
) -> None:
    """The other half — a loader that always refuses loads nothing. Returns key
    NAMES so a caller can answer "which credentials exist" without a value ever
    being returned, logged or asserted on."""
    monkeypatch.delenv(TEST_MARKER, raising=False)
    (tmp_path / ".env").write_text("ALPHA=one\nBETA=two\n# note\nEMPTY=\n", encoding="utf-8")

    loaded = load_repo_env(tmp_path)

    assert loaded == ["ALPHA", "BETA"], "EMPTY has no value and is not a credential"
    assert os.environ["ALPHA"] == "one"
    monkeypatch.delenv("ALPHA", raising=False)
    monkeypatch.delenv("BETA", raising=False)


def test_an_already_exported_value_is_never_overwritten(tmp_path: Path, monkeypatch) -> None:
    """An explicit export is a deliberate override; a file must not win over it."""
    monkeypatch.delenv(TEST_MARKER, raising=False)
    monkeypatch.setenv("ALPHA", "from-the-shell")
    (tmp_path / ".env").write_text("ALPHA=from-the-file\n", encoding="utf-8")

    assert load_repo_env(tmp_path) == []
    assert os.environ["ALPHA"] == "from-the-shell"


def test_an_empty_inherited_value_does_not_shadow_the_data_env_file(
    tmp_path: Path, monkeypatch,
) -> None:
    """AT-783: a server operator copies `.env.example` to `/etc/autotester/server.env`, so the
    compose `env_file` hands the container `ANTHROPIC_API_KEY=""`. That empty string must not
    block `<data>/.env`, where the real key lives."""
    monkeypatch.delenv(TEST_MARKER, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-from-data-env\n", encoding="utf-8")

    assert load_repo_env(tmp_path) == ["ANTHROPIC_API_KEY"]
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-from-data-env"


def test_a_missing_env_file_is_not_an_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(TEST_MARKER, raising=False)

    assert load_repo_env(tmp_path) == []


def test_the_CLI_actually_calls_the_loader_before_any_command(monkeypatch) -> None:
    """The wiring itself, which nothing could see.

    Sabotage EG — deleting `load_repo_env()` from the CLI callback — failed
    ZERO tests, and was reported INCONCLUSIVE rather than vacuous. The reason is
    the guard directly above: the loader refuses inside a test process, so no
    test could ever observe whether the CLI calls it. The protection made its own
    wiring invisible, which is AT-206's shape (a fix whose removal nothing
    detects) arriving inside AT-228's fix.

    So this watches the CALL rather than its effect: a spy in place of the real
    loader, driven through the shipped CLI, asserting nothing about credentials
    and touching no `.env`."""
    from typer.testing import CliRunner

    from autotester import cli

    called: list[str] = []
    monkeypatch.setattr(cli, "load_repo_env", lambda *a, **k: called.append("yes") or [])

    CliRunner().invoke(cli.app, ["doctor"])

    assert called == ["yes"], "the CLI ran a command without loading the repo .env"

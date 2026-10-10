"""hosting.md HO15: admin-set limits are strict, stored under the data root, and win at runtime.

Scenarios: an admin types a value into the settings page; a deploy script sets the env default;
someone hand-edits the settings file wrongly.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.server_settings import GIB, MIB, ServerSettings
from autotester.store.server_settings import (
    CONCURRENCY_ENV,
    UPLOAD_ENV,
    effective_max_concurrent_runs,
    effective_max_upload_bytes,
    load_server_settings,
    save_server_settings,
    settings_path,
)


def test_defaults_are_two_runs_and_two_gib() -> None:
    settings = ServerSettings()
    assert settings.max_concurrent_runs == 2 and settings.max_upload_bytes == 2147483648


@pytest.mark.parametrize("value", [1, 2, 64])
def test_concurrency_accepts_the_inclusive_bounds(value: int) -> None:
    assert ServerSettings(max_concurrent_runs=value).max_concurrent_runs == value


@pytest.mark.parametrize("value", [0, -1, 65, "2", "x", 2.0, 2.5, True, None, 2**63])
def test_concurrency_refuses_everything_else(value: object) -> None:
    """An admin form field is blank, 0, a typo, or an overflow."""
    with pytest.raises(ValidationError):
        ServerSettings(max_concurrent_runs=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [MIB, GIB, 64 * GIB])
def test_upload_limit_accepts_the_inclusive_bounds(value: int) -> None:
    assert ServerSettings(max_upload_bytes=value).max_upload_bytes == value


@pytest.mark.parametrize("value", [0, MIB - 1, 64 * GIB + 1, "5", -3, 1.5, 2**63])
def test_upload_limit_refuses_everything_else(value: object) -> None:
    with pytest.raises(ValidationError):
        ServerSettings(max_upload_bytes=value)  # type: ignore[arg-type]


def test_unknown_setting_is_refused() -> None:
    with pytest.raises(ValidationError):
        ServerSettings(max_concurrent_runs=2, admin_password="x")  # type: ignore[call-arg]


def test_saved_setting_wins_over_the_environment_and_applies_without_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CONCURRENCY_ENV, "4")
    assert effective_max_concurrent_runs(tmp_path) == 4          # env default, nothing saved
    save_server_settings(ServerSettings(max_concurrent_runs=1), tmp_path)
    assert effective_max_concurrent_runs(tmp_path) == 1          # the admin's choice wins
    save_server_settings(ServerSettings(max_concurrent_runs=3), tmp_path)
    assert effective_max_concurrent_runs(tmp_path) == 3          # next read, no restart


def test_nothing_saved_and_no_env_gives_the_documented_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CONCURRENCY_ENV, raising=False)
    monkeypatch.delenv(UPLOAD_ENV, raising=False)
    assert effective_max_concurrent_runs(tmp_path) == 2
    assert effective_max_upload_bytes(tmp_path) == 2 * GIB
    assert not (tmp_path / ".work").exists()                     # reading never creates files


@pytest.mark.parametrize(("raw", "expected"), [("", 2), ("many", 2), ("0", 1), ("-5", 1),
                                               (" 3 ", 3), ("999", 64)])
def test_a_typo_in_server_env_never_stops_the_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str, expected: int
) -> None:
    monkeypatch.setenv(CONCURRENCY_ENV, raw)
    assert effective_max_concurrent_runs(tmp_path) == expected


def test_upload_env_default_is_clamped_and_overridden_by_the_saved_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(UPLOAD_ENV, str(5 * MIB))
    assert effective_max_upload_bytes(tmp_path) == 5 * MIB
    monkeypatch.setenv(UPLOAD_ENV, "5")                           # below the 1 MiB floor
    assert effective_max_upload_bytes(tmp_path) == MIB
    save_server_settings(ServerSettings(max_upload_bytes=3 * GIB), tmp_path)
    assert effective_max_upload_bytes(tmp_path) == 3 * GIB


def test_a_hand_edited_corrupt_settings_file_falls_back_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CONCURRENCY_ENV, raising=False)
    path = settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"max_concurrent_runs": "lots"}', encoding="utf-8")
    settings, why = load_server_settings(tmp_path)
    assert settings is None and "defaults are in force" in why
    assert effective_max_concurrent_runs(tmp_path) == 2

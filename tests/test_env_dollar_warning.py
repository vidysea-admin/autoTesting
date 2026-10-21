"""AT-1389: a hand-written `${VAR}` in the repo-root `.env` is reported, never expanded.

After AT-1368 such a value is kept literally. Doctor and /settings/providers must say how many
values contain `${` and which KEYS, and never print a value. Every test uses a temp `.env`."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from autotester import cli
from autotester.core.env import dollar_value_keys, read_dotenv
from autotester.doctor import blocking, warning_summary
from autotester.ledger.env_warning import RULE, check_env_dollar
from autotester.ui.app import app

SECRET_A = "pa55-${HOME}-tail"
SECRET_B = "x${NOPE}y"


@pytest.fixture
def env_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(
        f"GEMINI_API_KEY={SECRET_A}\nPATHLYNKS_PASSWORD='{SECRET_B}'\nPLAIN=ok\nDOLLAR=cost$5\n",
        encoding="utf-8")
    return tmp_path


def test_keys_with_dollar_brace_are_listed_by_name_and_values_stay_literal(env_root: Path) -> None:
    assert dollar_value_keys(env_root) == ["GEMINI_API_KEY", "PATHLYNKS_PASSWORD"]
    assert read_dotenv(env_root / ".env")["GEMINI_API_KEY"] == SECRET_A  # still no expansion


def test_a_lone_dollar_sign_or_a_missing_file_gives_no_keys(tmp_path: Path) -> None:
    assert dollar_value_keys(tmp_path) == []
    (tmp_path / ".env").write_text("A=cost$5\nB=$HOME\n", encoding="utf-8")
    assert dollar_value_keys(tmp_path) == []


def test_doctor_warns_with_count_and_key_names_but_stays_green_and_prints_no_value(
        env_root: Path) -> None:
    rows = check_env_dollar(env_root)

    assert [r.rule for r in rows] == [RULE]
    assert blocking(rows) == []  # a warning, not a failure
    text = "\n".join(warning_summary(rows))
    assert "2 value(s)" in text and "GEMINI_API_KEY" in text and "PATHLYNKS_PASSWORD" in text
    for value in (SECRET_A, SECRET_B, "HOME", "NOPE", "pa55"):
        assert value not in text


def test_doctor_prints_no_env_line_when_no_value_contains_dollar_brace(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("A=plain\n", encoding="utf-8")
    assert check_env_dollar(tmp_path) == []
    assert warning_summary(check_env_dollar(tmp_path)) == []


def test_doctor_command_output_carries_the_warning_and_no_value(
        env_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("autotester.doctor.repo_root", lambda: env_root)
    monkeypatch.setattr("autotester.doctor.check_file_sizes", lambda root: [])
    result = CliRunner().invoke(cli.app, ["doctor"])
    assert "env-dollar-literal" in result.output and "GEMINI_API_KEY" in result.output
    assert SECRET_A not in result.output and SECRET_B not in result.output


def test_settings_page_shows_count_and_key_names_and_no_value(env_root: Path) -> None:
    page = TestClient(app).get("/settings/providers")

    assert page.status_code == 200
    assert "env-dollar-warning" in page.text
    assert "2 value(s)" in page.text and "PATHLYNKS_PASSWORD" in page.text
    assert SECRET_B not in page.text and "NOPE" not in page.text


def test_settings_page_has_no_warning_when_the_env_is_clean(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text("GEMINI_API_KEY=fine\n", encoding="utf-8")
    assert "env-dollar-warning" not in TestClient(app).get("/settings/providers").text

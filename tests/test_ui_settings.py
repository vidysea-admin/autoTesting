"""Global provider settings. Contract: qa/contracts/ui-settings.md US1-US4."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.browser.secrets import parse_env
from autotester.ui.app import app
from autotester.ui.env_editor import set_env_value


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_settings_page_shows_only_the_known_provider_keys(
    client: TestClient, scratch_root: Path
) -> None:
    response = client.get("/settings/providers")

    assert response.status_code == 200
    for key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OPENAI_API_KEY"):
        assert key in response.text
    assert "Not set" in response.text


def test_settings_page_shows_the_stored_value_masked(
    client: TestClient, scratch_root: Path
) -> None:
    """2026-09-21 UX amendment (Umesh, Approver): stored values render INTO the
    field so the operator can verify/edit them; *_KEY rows are masked inputs
    with a show/hide toggle. Owner-only display — never a prompt/log/screenshot."""
    set_env_value(scratch_root / ".env", "GEMINI_API_KEY", "s3cr3t-real-key")

    response = client.get("/settings/providers")

    assert response.status_code == 200
    assert "type='password' name='value' value='s3cr3t-real-key'" in response.text
    assert "i.type=i.type==='password'?'text':'password'" in response.text
    assert "Set" in response.text


def test_settings_submit_writes_via_env_editor(
    client: TestClient, scratch_root: Path
) -> None:
    response = client.post(
        "/settings/providers", data={"key": "OPENAI_API_KEY", "value": "new-real-key"}
    )

    assert response.status_code in (200, 303)
    written = (scratch_root / ".env").read_text(encoding="utf-8")
    assert parse_env(written)["OPENAI_API_KEY"] == "new-real-key"  # round-trip, not spelling


def test_settings_refuses_an_unknown_key(client: TestClient, scratch_root: Path) -> None:
    response = client.post(
        "/settings/providers", data={"key": "SOME_RANDOM_KEY", "value": "x"}
    )
    assert response.status_code == 400


def test_settings_refuses_a_value_with_a_newline(client: TestClient, scratch_root: Path) -> None:
    response = client.post("/settings/providers", data={
        "key": "OPENAI_API_KEY", "value": "real-value\nINJECTED_KEY=evil",
    })

    assert response.status_code == 400
    env_path = scratch_root / ".env"
    written = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    assert "INJECTED_KEY" not in written


def test_settings_link_is_reachable_from_the_shared_nav(
    client: TestClient, scratch_root: Path
) -> None:
    response = client.get("/")
    assert "/settings/providers" in response.text


def test_settings_page_lists_the_harness_login_keys_password_masked_and_never_prefilled(
    client: TestClient, scratch_root: Path
) -> None:
    """T-169 C1: an admin enters the acceptance-script login on the settings page; the
    password box is masked and write-only, so its stored value is in no page body."""
    set_env_value(scratch_root / ".env", "AUTOTESTER_HARNESS_EMAIL", "tester@example.test")
    set_env_value(scratch_root / ".env", "AUTOTESTER_HARNESS_PASSWORD", "hunter2-harness-pw")

    page = client.get("/settings/providers").text

    assert "AUTOTESTER_HARNESS_EMAIL" in page
    assert "AUTOTESTER_HARNESS_PASSWORD" in page
    assert "hunter2-harness-pw" not in page
    assert "type='password' name='value' value=''" in page
    assert "Value for AUTOTESTER_HARNESS_PASSWORD" in page


def test_settings_submit_saves_the_harness_password_to_dotenv_and_never_echoes_it(
    client: TestClient, scratch_root: Path
) -> None:
    response = client.post("/settings/providers", data={
        "key": "AUTOTESTER_HARNESS_PASSWORD", "value": "hunter2-harness-pw"},
        follow_redirects=False)

    assert response.status_code == 303
    assert "hunter2-harness-pw" not in response.text
    written = parse_env((scratch_root / ".env").read_text(encoding="utf-8"))
    assert written["AUTOTESTER_HARNESS_PASSWORD"] == "hunter2-harness-pw"
    assert "hunter2-harness-pw" not in client.get("/settings/providers").text

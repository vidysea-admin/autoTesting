"""T-206 TA15 checker findings F1/F2 on /projects/<slug>/env and /settings/providers.

F1: the "Add credential" Value box rendered as type=text, so a secret typed
there showed in clear on screen. F2: 15 controls on the credentials page and 7
on the provider settings page had no programmatic label.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ui_onboard_a11y import unlabelled_controls

from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return TestClient(app)


def _save(root: Path, production: bool = False) -> None:
    ProjectStore("demo", root).save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        production=production,
        secrets=[SecretRef(key="DEMO_EMAIL", domains=["demo.test"]),
                 SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    ))


def test_the_add_credential_value_box_is_masked_not_clear_text(
    client: TestClient, tmp_path: Path
) -> None:
    """A dev opens Credentials, scrolls to "Add a custom credential" and types a
    new API secret over a shared screen: the Value box must be a password
    input that browsers and password managers will not echo or autofill."""
    _save(tmp_path)
    page = client.get("/projects/demo/env").text
    form = page.split("/projects/demo/env/add'", 1)[1].split("</form>", 1)[0]
    value_box = re.search(r"<input\b[^>]*name='value'[^>]*>", form)
    assert value_box is not None
    assert "type='password'" in value_box.group(0)
    assert "autocomplete='new-password'" in value_box.group(0)


@pytest.mark.parametrize("production", [False, True])
def test_every_control_on_the_credentials_page_has_a_label(
    client: TestClient, tmp_path: Path, production: bool
) -> None:
    """A screen-reader user tabbing through Credentials (secret rows, platform
    URL, Add credential, crawl approval - including the production-forced
    checkbox) hears a name for every control, not "edit text"."""
    _save(tmp_path, production)
    page = client.get("/projects/demo/env").text
    assert page.count("<input") >= 15  # the whole page really rendered
    assert unlabelled_controls(page) == []


def test_every_control_on_provider_settings_has_a_label(client: TestClient) -> None:
    """The operator opens Settings > providers: each key row's value box is
    announced with its key name, so two rows are never both "new value"."""
    page = client.get("/settings/providers").text
    assert page.count("name='value'") >= 5
    assert unlabelled_controls(page) == []
    assert "aria-label='Value for " in page

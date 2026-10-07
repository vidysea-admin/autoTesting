"""U3, the credentials editor: display, write, and the empty-save wipe guard.

Split from `test_ui.py` for the 300-line cap (2026-09-21). Contract:
qa/contracts/ui.md U3 as amended 2026-09-21 by Umesh (Approver): the stored
value renders INTO the field (prefilled, editable); password-shaped keys are
masked with a show/hide toggle; an empty Save is refused and never wipes.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.store.project_store import ProjectStore
from autotester.ui.app import app
from autotester.ui.env_editor import set_env_value


@pytest.fixture()
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# -- U3 the env editor never renders a real value -----------------------------

def test_env_editor_shows_the_stored_value_to_the_operator(
    client: TestClient, scratch_root: Path
) -> None:
    """2026-09-21 UX amendment (Umesh, Approver): the write-only editor read as
    'everything wipes on Save'. The stored value is now rendered INTO the field
    (prefilled) so the operator sees what is saved and can edit it; password-
    shaped keys are masked inputs with a show/hide toggle. The value still
    never reaches a prompt, log, or screenshot — that boundary is unchanged."""
    from autotester.schema.project import Project as ProjectModel
    from autotester.schema.project import SecretRef

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_EMAIL", domains=["demo.test"]),
                 SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    )
    ProjectStore("demo", scratch_root).save_project(project)
    set_env_value(scratch_root / ".env", "DEMO_EMAIL", "ops@demo.test")
    set_env_value(scratch_root / ".env", "DEMO_PASSWORD", "s3cr3t-real-value")

    response = client.get("/projects/demo/env")

    assert response.status_code == 200
    # non-password key: the value is visible and editable
    assert "value='ops@demo.test'" in response.text
    # password key: masked input carrying the value, with a show/hide toggle
    assert "type='password' name='value' value='s3cr3t-real-value'" in response.text
    assert "i.type=i.type==='password'?'text':'password'" in response.text


def test_env_editor_writes_a_new_value_via_post(client: TestClient, scratch_root: Path) -> None:
    from autotester.schema.project import Project as ProjectModel
    from autotester.schema.project import SecretRef

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    )
    ProjectStore("demo", scratch_root).save_project(project)

    response = client.post(
        "/projects/demo/env", data={"key": "DEMO_PASSWORD", "value": "new-real-value"}
    )

    assert response.status_code in (200, 303)
    # Assert the ROUND-TRIP, not the on-disk spelling: AT-082 made the writer
    # quote values so one containing ` #`, edge whitespace or a quote survives
    # `parse_env`. What must hold is that the value reads back exactly.
    from autotester.browser.secrets import parse_env
    written = (scratch_root / ".env").read_text(encoding="utf-8")
    assert parse_env(written)["DEMO_PASSWORD"] == "new-real-value"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits don't apply on Windows")
def test_set_env_value_writes_owner_only_permissions(scratch_root: Path) -> None:
    import stat

    set_env_value(scratch_root / ".env", "DEMO_PASSWORD", "x")

    mode = stat.S_IMODE((scratch_root / ".env").stat().st_mode)
    assert mode == 0o600


def test_env_editor_refuses_an_undeclared_key(client: TestClient, scratch_root: Path) -> None:
    from autotester.schema.project import Project as ProjectModel

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
    )
    ProjectStore("demo", scratch_root).save_project(project)

    response = client.post(
        "/projects/demo/env", data={"key": "NOT_DECLARED", "value": "x"}
    )

    assert response.status_code == 400


def test_env_editor_refuses_a_value_with_a_newline(client: TestClient, scratch_root: Path) -> None:
    """A value containing a newline could inject a second .env line disguised
    as one value (e.g. a smuggled extra KEY=VALUE pair)."""
    from autotester.schema.project import Project as ProjectModel
    from autotester.schema.project import SecretRef

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    )
    ProjectStore("demo", scratch_root).save_project(project)

    response = client.post("/projects/demo/env", data={
        "key": "DEMO_PASSWORD", "value": "real-value\nINJECTED_KEY=evil",
    })

    assert response.status_code == 400
    env_path = scratch_root / ".env"
    written = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    assert "INJECTED_KEY" not in written


def test_an_empty_save_never_wipes_a_stored_value(
    client: TestClient, scratch_root: Path
) -> None:
    """2026-09-21 live wipe: pressing Save on an untouched (empty, masked)
    field overwrote the stored secret with '' — the password save was fine,
    but a stray Save on the email row blanked the stored email. An empty
    field means 'nothing typed', never 'erase': the submit must be refused
    and the stored value must survive byte-identically."""
    from autotester.browser.secrets import parse_env
    from autotester.schema.project import Project as ProjectModel
    from autotester.schema.project import SecretRef

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    )
    ProjectStore("demo", scratch_root).save_project(project)
    set_env_value(scratch_root / ".env", "DEMO_PASSWORD", "keep-me-real")

    response = client.post("/projects/demo/env", data={"key": "DEMO_PASSWORD", "value": ""})

    assert response.status_code == 400
    assert "keep-me-real" not in response.text  # never echoed, even on refusal
    written = (scratch_root / ".env").read_text(encoding="utf-8")
    assert parse_env(written)["DEMO_PASSWORD"] == "keep-me-real"

    whitespace = client.post("/projects/demo/env", data={"key": "DEMO_PASSWORD", "value": "   "})
    assert whitespace.status_code == 400
    written = (scratch_root / ".env").read_text(encoding="utf-8")
    assert parse_env(written)["DEMO_PASSWORD"] == "keep-me-real"



# -- custom credentials + platform URL on the credentials page (2026-09-21) ----

def _seed_demo_project(scratch_root: Path) -> None:
    from autotester.schema.project import Project as ProjectModel

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
    )
    ProjectStore("demo", scratch_root).save_project(project)


def test_add_a_custom_credential_declares_and_stores_in_one_step(
    client: TestClient, scratch_root: Path
) -> None:
    """Umesh, 2026-09-21: 'there should be a place to add custom values'. One
    submit declares the SecretRef (same validators as the settings page) and
    writes the value through the one legitimate .env write path."""
    from autotester.browser.secrets import parse_env

    _seed_demo_project(scratch_root)
    response = client.post("/projects/demo/env/add", data={
        "key": "ERP_TENANT_ID", "value": "tenant-42",
        "domains": "demo.test", "description": "the tenant id",
    })

    assert response.status_code in (200, 303)
    project = ProjectStore("demo", scratch_root).load_project()
    assert project.secret("ERP_TENANT_ID") is not None  # declared
    written = (scratch_root / ".env").read_text(encoding="utf-8")
    assert parse_env(written)["ERP_TENANT_ID"] == "tenant-42"  # and stored


def test_add_credential_refuses_a_duplicate_key(
    client: TestClient, scratch_root: Path
) -> None:
    from autotester.schema.project import Project as ProjectModel
    from autotester.schema.project import SecretRef

    project = ProjectModel(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="ERP_TENANT_ID", domains=["demo.test"])],
    )
    ProjectStore("demo", scratch_root).save_project(project)

    response = client.post("/projects/demo/env/add", data={
        "key": "ERP_TENANT_ID", "value": "x", "domains": "demo.test",
    })

    assert response.status_code == 400


def test_the_platform_url_is_editable_from_the_credentials_page(
    client: TestClient, scratch_root: Path
) -> None:
    """Umesh, 2026-09-21: 'url bhi add krr credentials mai'. The base_url and
    allowed domains render prefilled and save from the same page, reusing the
    project-edit guards (reachability, unsafe-submission scan)."""
    _seed_demo_project(scratch_root)
    response = client.post("/projects/demo/env/url", data={
        "base_url": "https://demo.test/signin", "allowed_domains": "demo.test, app.test",
    })

    assert response.status_code in (200, 303)
    project = ProjectStore("demo", scratch_root).load_project()
    assert project.base_url == "https://demo.test/signin"
    assert project.allowed_domains == ["demo.test", "app.test"]


def test_env_writer_normalizes_only_updated_keys(tmp_path: Path) -> None:
    from autotester.browser.secrets import parse_env
    from autotester.ui.env_editor import create_env_value_if_absent, set_env_values

    path = tmp_path / ".env"
    path.write_text("# keep\n export TARGET = 'old'\nTARGET='older'\n"
                    "OTHER='one'\nOTHER='two'\n", encoding="utf-8")
    assert set_env_values(path, {"TARGET": "new"}) is None
    written = path.read_text(encoding="utf-8")
    assert written.count("TARGET='new'") == 0  # renderer chooses double quotes
    assert parse_env(written)["TARGET"] == "new"
    assert "OTHER='one'\nOTHER='two'" in written and "# keep" in written
    assert create_env_value_if_absent(path, "TARGET", lambda: "wrong") == "new"
    assert path.read_text(encoding="utf-8") == written


def test_env_lock_timeout_and_replace_failure_leave_original(tmp_path: Path, monkeypatch) -> None:
    from autotester.ui.env_editor import _env_lock, create_env_value_if_absent, set_env_values

    path = tmp_path / ".env"
    set_env_values(path, {"ORIGINAL": "keep"})
    before = path.read_bytes()
    lock_path = Path(str(path.resolve()) + ".lock")
    with _env_lock(path), pytest.raises(TimeoutError):
        create_env_value_if_absent(path, "NEW", lambda: "value", timeout_s=0.03)
    assert path.read_bytes() == before and lock_path.exists()
    with monkeypatch.context() as patch:
        def fail_replace(*_args):
            raise OSError("synthetic replacement failure")
        patch.setattr("autotester.ui.env_editor.os.replace", fail_replace)
        with pytest.raises(OSError):
            set_env_values(path, {"NEW": "value"})
    assert path.read_bytes() == before and not list(tmp_path.glob(".env-*.tmp"))
    assert create_env_value_if_absent(path, "NEW", lambda: "value") == "value"
    assert lock_path.exists()

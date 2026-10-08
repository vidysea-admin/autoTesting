"""T-161: one no-CLI intake for a bare URL/account or richly taught project."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.browser.secrets import parse_env
from autotester.schema.enums import SourceKind
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app
from autotester.ui.env_editor import set_env_values


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _base(**extra):
    data = {
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    }
    data.update(extra)
    return data


def test_one_form_exposes_every_intake_input(client: TestClient) -> None:
    response = client.get("/onboard")
    assert response.status_code == 200
    for name in (
        "credential_key", "credential_value", "credential_domains", "evals",
        "conditions", "use_cases", "source_kind", "source_value",
    ):
        assert f"name='{name}'" in response.text or f'name="{name}"' in response.text
    assert "Add another credential" in response.text
    assert "Add another source" in response.text


def test_rich_intake_persists_refs_sources_and_secrets_only_in_env(
    client: TestClient, root: Path,
) -> None:
    secret = "real-password-4829"
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_EMAIL", "DEMO_PASSWORD"],
        credential_value=["tester@example.test", secret],
        credential_domains=["demo.test", "demo.test"],
        credential_description=["test account email", "test account password"],
        evals="Login succeeds\nDashboard loads",
        conditions="Account is active\nNo production writes",
        use_cases="Counsellor reviews a student",
        source_kind=["url", "video"],
        source_value=["https://drive.google.com/file/d/example", "D:/evidence/demo.mp4"],
        source_label=["Drive walkthrough", "Local recording"],
    ), follow_redirects=False)

    assert response.status_code == 303
    store = ProjectStore("demo", root)
    project = store.load_project()
    assert [ref.key for ref in project.secrets] == ["DEMO_EMAIL", "DEMO_PASSWORD"]
    assert all(ref.domains == ["demo.test"] for ref in project.secrets)
    sources = store.list_sources()
    assert {source.kind for source in sources} == {
        SourceKind.EVAL, SourceKind.CONDITION, SourceKind.USE_CASE,
        SourceKind.URL, SourceKind.VIDEO,
    }
    artifact_text = project.model_dump_json() + (root / "projects/demo/sources.jsonl").read_text()
    assert secret not in artifact_text
    assert "tester@example.test" not in artifact_text
    assert parse_env((root / ".env").read_text()) == {
        "DEMO_EMAIL": "tester@example.test", "DEMO_PASSWORD": secret,
    }


def test_url_only_and_legacy_onboarding_remain_valid(client: TestClient, root: Path) -> None:
    response = client.post("/onboard", data=_base(), follow_redirects=False)
    assert response.status_code == 303
    assert ProjectStore("demo", root).load_project().secrets == []
    assert ProjectStore("demo", root).list_sources() == []
    assert not (root / ".env").exists()


def test_invalid_second_credential_leaves_no_partial_project_or_env(
    client: TestClient, root: Path,
) -> None:
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_EMAIL", "bad-key"],
        credential_value=["tester@example.test", "password"],
        credential_domains=["demo.test", "demo.test"],
        credential_description=["email", "password"],
    ), follow_redirects=False)
    assert response.status_code == 400
    assert not (root / "projects/demo").exists()
    assert not (root / ".env").exists()
    assert "bad-key" not in response.text


def test_invalid_second_value_does_not_write_the_first_value(
    client: TestClient, root: Path,
) -> None:
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_EMAIL", "DEMO_PASSWORD"],
        credential_value=["tester@example.test", "line-one\nINJECTED_KEY=value"],
        credential_domains=["demo.test", "demo.test"],
        credential_description=["email", "password"],
    ), follow_redirects=False)
    assert response.status_code == 400
    assert not (root / "projects/demo").exists()
    assert not (root / ".env").exists()


def test_credential_scope_must_stay_inside_project_domains(
    client: TestClient, root: Path,
) -> None:
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_PASSWORD"], credential_value=["password-123"],
        credential_domains=["evil.test"], credential_description=["password"],
    ), follow_redirects=False)
    assert response.status_code == 400
    assert not (root / "projects/demo").exists()


def test_new_secret_cannot_be_smuggled_into_non_secret_inputs(
    client: TestClient, root: Path,
) -> None:
    secret = "very-private-password-123"
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_PASSWORD"], credential_value=[secret],
        credential_domains=["demo.test"], credential_description=["password"],
        evals=f"Login rejects {secret}",
    ), follow_redirects=False)
    assert response.status_code == 400
    assert secret not in response.text
    assert not (root / "projects/demo").exists()
    assert not (root / ".env").exists()


def test_new_hostname_shaped_secret_is_not_echoed_by_url_validation(
    client: TestClient, root: Path,
) -> None:
    secret = "dual-fake-secret.example"
    response = client.post("/onboard", data=_base(
        base_url="https://demo.test/login", allowed_domains=secret,
        credential_key=["DEMO_PASSWORD"], credential_value=[secret],
        credential_domains=[secret], credential_description=["password"],
    ), follow_redirects=False)
    assert response.status_code == 400
    assert secret not in response.text
    assert not (root / "projects/demo").exists()
    assert not (root / ".env").exists()


def test_existing_root_secret_key_cannot_be_reused_or_hidden(
    client: TestClient, root: Path,
) -> None:
    old_secret = "first-project-secret-91"
    (root / ".env").write_text(f"SHARED_PASSWORD={old_secret}\n", encoding="utf-8")
    response = client.post("/onboard", data=_base(
        credential_key=["SHARED_PASSWORD"], credential_value=["replacement-secret-22"],
        credential_domains=["demo.test"], credential_description=["password"],
        evals=f"The page must never show {old_secret}",
    ), follow_redirects=False)
    assert response.status_code == 400
    assert old_secret not in response.text
    assert not (root / "projects/demo").exists()
    assert parse_env((root / ".env").read_text()) == {"SHARED_PASSWORD": old_secret}


def test_unset_key_owned_by_another_project_cannot_be_redeclared(
    client: TestClient, root: Path,
) -> None:
    first = client.post("/onboard", data={
        **_base(), "slug": "alpha", "name": "Alpha",
        "credential_key": ["ALPHA_SHARED_PASSWORD"], "credential_value": [""],
        "credential_domains": ["demo.test"], "credential_description": ["password"],
    }, follow_redirects=False)
    second = client.post("/onboard", data={
        **_base(), "slug": "beta", "name": "Beta",
        "credential_key": ["ALPHA_SHARED_PASSWORD"], "credential_value": [""],
        "credential_domains": ["demo.test"], "credential_description": ["password"],
    }, follow_redirects=False)
    assert first.status_code == 303
    assert second.status_code == 400
    assert not (root / "projects/beta").exists()


def test_legacy_foreign_owner_is_refused_even_inside_target_namespace(
    client: TestClient, root: Path,
) -> None:
    """A synthetic old declaration cannot be stolen merely by matching the new prefix."""
    from autotester.schema.project import Project, SecretRef

    owner = ProjectStore("alpha", root)
    owner.save_project(Project(slug="alpha", name="Alpha", base_url="https://demo.test",
                               allowed_domains=["demo.test"], secrets=[
                                   SecretRef(key="DEMO_SHARED_PASSWORD", domains=["demo.test"])]))
    env = root / ".env"
    env.write_bytes(b"UNRELATED_KEY=synthetic-sentinel\n")
    before = {str(p): p.read_bytes() for p in (root / "projects").rglob("*") if p.is_file()}
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_SHARED_PASSWORD"], credential_value=[""],
        credential_domains=["demo.test"], credential_description=["password"],
    ), follow_redirects=False)
    assert response.status_code == 400
    assert "belongs to another project" in response.text
    assert not (root / "projects/demo").exists()
    assert {str(p): p.read_bytes() for p in (root / "projects").rglob("*") if p.is_file()} == before
    assert env.read_bytes() == b"UNRELATED_KEY=synthetic-sentinel\n"


def test_existing_project_cannot_be_overwritten_by_reonboarding(
    client: TestClient, root: Path,
) -> None:
    assert client.post("/onboard", data=_base(), follow_redirects=False).status_code == 303
    response = client.post("/onboard", data=_base(name="Replacement"), follow_redirects=False)
    assert response.status_code == 400
    assert ProjectStore("demo", root).load_project().name == "Demo"


def test_imbalanced_repeated_rows_fail_before_writes(client: TestClient, root: Path) -> None:
    response = client.post("/onboard", data=_base(
        credential_key=["DEMO_EMAIL", "DEMO_PASSWORD"],
        credential_value=["only-one-value"],
        credential_domains=["demo.test", "demo.test"],
        credential_description=["email", "password"],
    ), follow_redirects=False)
    assert response.status_code == 400
    assert not (root / "projects/demo").exists()


def test_env_batch_replace_failure_preserves_the_existing_file(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = root / ".env"
    original = "EXISTING_KEY=keep-me\n"
    env_path.write_text(original, encoding="utf-8")

    def fail_replace(_source, _target) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("autotester.ui.env_editor.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        set_env_values(env_path, {"NEW_KEY": "new-value"})
    assert env_path.read_text(encoding="utf-8") == original


def test_env_batch_replaces_every_duplicate_key(root: Path) -> None:
    env_path = root / ".env"
    env_path.write_text("DEMO_PASSWORD=old-first\nDEMO_PASSWORD=old-last\n", encoding="utf-8")
    set_env_values(env_path, {"DEMO_PASSWORD": "new-value"})
    assert parse_env(env_path.read_text()) == {"DEMO_PASSWORD": "new-value"}
    assert "old-" not in env_path.read_text()


def test_repeated_statements_are_content_addressed_once(client: TestClient, root: Path) -> None:
    response = client.post("/onboard", data=_base(
        evals="Dashboard loads\nDashboard loads",
        conditions="Account active\nAccount active",
    ), follow_redirects=False)
    assert response.status_code == 303
    sources = ProjectStore("demo", root).list_sources()
    assert [(source.kind, source.text) for source in sources] == [
        (SourceKind.EVAL, "Dashboard loads"),
        (SourceKind.CONDITION, "Account active"),
    ]

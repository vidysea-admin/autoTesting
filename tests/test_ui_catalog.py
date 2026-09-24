"""The test-catalog page. Contract: qa/contracts/catalog.md CT4, CT8."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    result = ProjectStore("demo", tmp_path)
    result.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test/signin",
        allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    ))
    return result


def _auth_flow() -> Flow:
    return Flow(
        id="flow_login", name="Login", entry_screen="scr_login",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
            Step(order=2, action=Action.FILL, target="Password", value="{{SECRET:DEMO_PASSWORD}}"),
            Step(order=3, action=Action.CLICK, target="Sign in"),
        ],
    )


# -- CT4: no FlowSpec -> the page renders the reason on every row -----------

def test_no_flowspec_page_renders_the_reason_on_every_row_not_a_generic_empty_state(
    store: ProjectStore,
) -> None:
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert response.text.count("no FlowSpec yet") >= 15  # one per CaseClass, none skipped
    assert "record a source" in response.text


def test_catalog_page_404s_for_an_unknown_project() -> None:
    response = TestClient(app).get("/projects/nope/catalog")
    assert response.status_code == 404


# -- CT8: a blocked row states the reason AND the specific action -----------

def test_missing_credential_row_names_the_key_not_the_bare_enum(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "DEMO_PASSWORD" in response.text
    # the bare enum literal alone is never the whole story on a blocked row --
    # the specific action text must accompany it.
    assert "set DEMO_PASSWORD in the repo-root .env" in response.text


def test_runnable_happy_path_renders_as_runnable(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "runnable" in response.text
    assert "happy" in response.text


def test_page_escapes_a_hostile_project_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(
        slug="demo", name="<script>alert(1)</script>", base_url="https://demo.test/signin",
        allowed_domains=["demo.test"],
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_page_reports_the_runnable_count(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    # 15 total case classes; blocked: 2 auth (no .env value set) + double_submit
    # (default write_policy=read_only) -> 12 runnable
    assert "12" in response.text
    assert "15" in response.text

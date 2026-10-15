"""Acceptance driver authentication and baseline isolation without live dependencies."""

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import SourceKind
from autotester.schema.flowspec import FlowSpec
from autotester.schema.project import Project, Source
from autotester.stages.generic_acceptance import ModeSeams, ModeSpec, enter_pipeline
from autotester.stages.real_acceptance import acceptance_client, require_fresh_baseline
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTOTESTER_TEST_NO_AUTO_LOGIN", "1")
    monkeypatch.setenv("AUTOTESTER_COOKIE_SECURE", "0")
    monkeypatch.delenv("AUTOTESTER_AUTH_DISABLED", raising=False)
    monkeypatch.delenv("AUTOTESTER_AUTH_DIR", raising=False)
    store = ProjectStore("fixture", tmp_path)
    store.save_project(Project(slug="fixture", name="Fixture", base_url="https://fixture.test",
                               allowed_domains=["fixture.test"]))
    return store


def _signup():
    with TestClient(app, base_url="http://127.0.0.1",
                    headers={"Origin": "http://127.0.0.1"}) as client:
        response = client.post("/auth/signup", data={"email": "acceptance@fixture.test",
                               "password": "Acceptance-only-strong-pass-329"},
                               follow_redirects=False)
        assert response.status_code == 303


def test_normal_login_retains_origin_and_reaches_protected_routes(isolated_store, monkeypatch):
    _signup()
    isolated_store.save_flowspec(FlowSpec(project="fixture"))
    for secure in ("0", "1"):
        monkeypatch.setenv("AUTOTESTER_COOKIE_SECURE", secure)
        with acceptance_client(app, "acceptance@fixture.test", "Acceptance-only-strong-pass-329",
                               isolated_store.paths.slug) as client:
            response = client.post("/projects/fixture/flowspec/approve",
                                   data={"by": "acceptance"}, follow_redirects=False)
            assert response.status_code == 303
            assert client.headers["origin"] == "https://127.0.0.1"


def test_bad_password_refuses_without_echoing_input(isolated_store):
    _signup()
    with (pytest.raises(ValueError, match="sign-in refused") as exc,
          acceptance_client(app, "acceptance@fixture.test", "wrong-private-password",
                            isolated_store.paths.slug)):
        pytest.fail("bad credentials reached execution")
    assert "wrong-private-password" not in str(exc.value)


def test_permissions_checked_before_yield(isolated_store):
    from autotester.auth import db
    _signup()
    with db.transaction() as conn:
        conn.execute("DELETE FROM group_permissions WHERE permission LIKE 'project.run%'")
    with (pytest.raises(ValueError, match="needs view, edit, run"),
          acceptance_client(app, "acceptance@fixture.test", "Acceptance-only-strong-pass-329",
                            isolated_store.paths.slug)):
        pytest.fail("missing run permission reached execution")


def test_url_only_refuses_teaching_sources_before_orchestration(isolated_store):
    isolated_store.add_source(Source(project="fixture", kind=SourceKind.TEXT,
                                    text="private teaching notes"))
    spec = ModeSpec(mode="url_only", slug="fixture", name="Fixture",
                    base_url="https://fixture.test", allowed_domains=["fixture.test"])
    with pytest.raises(ValueError, match="mode differs"):
        enter_pipeline(isolated_store, spec, ModeSeams())
    assert not isolated_store.paths.runs_dir.exists()


def test_prior_truth_refused_without_modification(isolated_store):
    isolated_store.save_flowspec(FlowSpec(project="fixture"))
    before = isolated_store.paths.flowspec.read_bytes()
    with pytest.raises(ValueError, match="without prior truth"):
        require_fresh_baseline(isolated_store, "url_only")
    assert isolated_store.paths.flowspec.read_bytes() == before


def test_baseline_mode_mismatch_refused(isolated_store):
    with pytest.raises(ValueError, match="mode differs"):
        require_fresh_baseline(isolated_store, "teaching")


def test_real_seams_use_configured_vision_role(isolated_store, monkeypatch):
    import run_real_acceptance as driver

    from autotester import providers
    from autotester.schema.crawl import CrawlBounds
    selected = object()
    calls = []
    monkeypatch.setattr(providers, "for_role", lambda project, role:
                        calls.append((project.slug, role)) or selected)
    seams = driver._real_seams(isolated_store, "teaching", CrawlBounds())
    assert seams.ingest_provider is selected
    assert calls == [("fixture", "vision")]


def test_cli_root_binds_ui_store_before_dry_run(isolated_store, monkeypatch):
    import run_real_acceptance as driver
    from run_approval_fixture import grant_live_case_approval

    from autotester.core.paths import repo_root
    from autotester.schema.enums import ApprovalKind
    grant_live_case_approval(isolated_store, project="fixture", target="https://fixture.test",
                             run_kind=ApprovalKind.CRAWL)
    grant_live_case_approval(isolated_store, project="fixture", target="https://fixture.test")
    monkeypatch.delenv("AUTOTESTER_ROOT")
    assert driver.main(["fixture", "--mode", "url_only", "--dry-run", "--root",
                        str(isolated_store.paths.root)]) == 0
    assert repo_root() == isolated_store.paths.root.resolve()

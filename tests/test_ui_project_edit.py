"""Onboarding validation + editing a project after the fact. Contract: qa/contracts/ui.md.

AT-058: Umesh typed "all" in Allowed domains meaning "allow everything". It was
stored verbatim as a literal domain named `all`, so the project was dead on
arrival — every run died at the first step with NavigationRefused, and there was
no route anywhere to fix it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from litellm_fake import install, reply
from litellm_fake import no_network as block_network

from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _onboard(client: TestClient, **overrides: str):
    data = {
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    }
    data.update(overrides)
    return client.post("/onboard", data=data, follow_redirects=False)


# -- AT-058a: refuse an unrunnable project at onboarding, not mid-run ---------

def test_onboarding_refuses_domains_that_exclude_the_projects_own_base_url(
    client: TestClient, scratch_root: Path
) -> None:
    """The exact shape of the real incident: "all" is not a wildcard, it is a
    literal domain, so the project could never reach its own base URL."""
    response = _onboard(client, allowed_domains="all")

    assert response.status_code == 400
    assert "could never run" in response.text
    assert ProjectStore("demo", scratch_root).load_project() is None


def test_onboarding_error_names_the_host_the_user_must_add(
    client: TestClient, scratch_root: Path
) -> None:
    """A 400 the user cannot act on is barely better than the mid-run failure it
    replaces — the message must name the missing host."""
    response = _onboard(client, allowed_domains="all")

    assert "demo.test" in response.text


def test_onboarding_refuses_a_base_url_that_is_not_openable(
    client: TestClient, scratch_root: Path
) -> None:
    response = _onboard(client, base_url="not a url", allowed_domains="demo.test")

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).load_project() is None


def test_onboarding_still_accepts_a_subdomain_of_an_allowed_domain(
    client: TestClient, scratch_root: Path
) -> None:
    """The validator must not be stricter than the boundary it guards:
    Project.allows_domain already accepts subdomains, so app.demo.test under
    demo.test is legitimate and must still onboard."""
    response = _onboard(
        client, base_url="https://app.demo.test/signin", allowed_domains="demo.test"
    )

    assert response.status_code == 303
    assert ProjectStore("demo", scratch_root).load_project() is not None


# -- AT-058b: a project's own settings are editable afterwards ----------------

def test_edit_form_shows_the_projects_current_values(
    client: TestClient, scratch_root: Path
) -> None:
    _onboard(client)

    response = client.get("/projects/demo/edit")

    assert response.status_code == 200
    assert "https://demo.test/signin" in response.text
    assert "demo.test" in response.text


def test_editing_persists_new_domains_through_the_store(
    client: TestClient, scratch_root: Path
) -> None:
    """The recovery path the real incident had no route for."""
    _onboard(client)

    response = client.post("/projects/demo/edit", data={
        "name": "Demo Renamed", "base_url": "https://other.test/app",
        "allowed_domains": "other.test, www.other.test",
    }, follow_redirects=False)

    assert response.status_code == 303
    project = ProjectStore("demo", scratch_root).load_project()
    assert project is not None
    assert project.name == "Demo Renamed"
    assert project.base_url == "https://other.test/app"
    assert project.allowed_domains == ["other.test", "www.other.test"]
    assert project.slug == "demo"  # identity never changes


def test_editing_refuses_domains_that_would_strand_the_base_url(
    client: TestClient, scratch_root: Path
) -> None:
    """Editing must not be a back door around the onboarding check."""
    _onboard(client)

    response = client.post("/projects/demo/edit", data={
        "name": "Demo", "base_url": "https://demo.test/signin", "allowed_domains": "all",
    })

    assert response.status_code == 400
    project = ProjectStore("demo", scratch_root).load_project()
    assert project is not None
    assert project.allowed_domains == ["demo.test"]  # unchanged on disk


def test_editing_refuses_an_empty_domain_list(
    client: TestClient, scratch_root: Path
) -> None:
    _onboard(client)

    response = client.post("/projects/demo/edit", data={
        "name": "Demo", "base_url": "https://demo.test/signin", "allowed_domains": " , ",
    })

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).load_project().allowed_domains == ["demo.test"]


def test_editing_an_unknown_project_is_404(client: TestClient, scratch_root: Path) -> None:
    response = client.post("/projects/nope/edit", data={
        "name": "x", "base_url": "https://x.test", "allowed_domains": "x.test",
    })

    assert response.status_code == 404


def test_project_page_links_to_its_settings(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)

    response = client.get("/projects/demo")

    assert "/projects/demo/edit" in response.text


def test_models_save_round_trips_with_vision_ensemble_and_named_controls(client, scratch_root):
    _onboard(client)
    response = client.post("/projects/demo/edit", data={"name": "Revised",
        "base_url": "https://demo.test", "allowed_domains": "demo.test",
        "provider_judge": "litellm:openai/gpt-4o", "provider_agent": "mock",
        "provider_vision": "gemini,anthropic"}, follow_redirects=False)
    assert response.status_code == 303
    project = ProjectStore("demo").load_project()
    assert project.name == "Revised" and project.providers.judge == "litellm:openai/gpt-4o"
    assert project.providers.vision_ensemble() == ["gemini", "anthropic"]
    page = client.get("/projects/demo/edit").text
    assert "Models" in page and "Test this model" in page and "screenshots" in page


@pytest.mark.parametrize("bad", ["litellm:https://u:model-canary@host/v1", "gemini,anthropic"])
def test_bad_model_saves_are_atomic_and_do_not_echo(client, scratch_root, bad):
    _onboard(client)
    before = (scratch_root / "projects/demo/project.json").read_bytes()
    response = client.post("/projects/demo/edit", data={"name": "Changed",
        "base_url": "https://demo.test", "allowed_domains": "demo.test", "provider_agent": bad})
    assert response.status_code == 400 and "model-canary" not in response.text
    assert (scratch_root / "projects/demo/project.json").read_bytes() == before


def test_probe_is_fixed_synthetic_and_never_saves_project_data(
        client, scratch_root, monkeypatch):
    _onboard(client, name="Private-project-name-canary")
    fake = install(monkeypatch, [reply('{"answer":7}')])
    before = (scratch_root / "projects/demo/project.json").read_bytes()
    with client:
        attempts = block_network.__wrapped__(monkeypatch)
        response = client.post("/projects/demo/models/probe", data={"role": "agent",
                               "spec": "litellm:openai/gpt-4o"})
    assert response.status_code == 200 and "answer 7" in response.text
    assert len(fake.calls) == 1 and "Private-project-name-canary" not in str(fake.calls)
    assert (scratch_root / "projects/demo/project.json").read_bytes() == before
    assert not (scratch_root / "projects/demo/runs").exists() and not attempts


@pytest.mark.parametrize("role,spec", [("vision", "litellm:openai/gpt-4o"),
                                      ("judge", "litellm:https://u:probe-canary@host/v1"),
                                      ("agent", "langchain-fallback")])
def test_probe_refusals_are_400_with_zero_physical_calls(
        client, scratch_root, monkeypatch, role, spec):
    _onboard(client)
    fake = install(monkeypatch, [])
    with client:
        attempts = block_network.__wrapped__(monkeypatch)
        response = client.post("/projects/demo/models/probe", data={"role": role, "spec": spec})
    assert response.status_code == 400 and "probe-canary" not in response.text
    assert fake.calls == [] and not attempts

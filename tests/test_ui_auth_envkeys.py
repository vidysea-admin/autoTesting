"""T-204 fix cycle 1, AU21: no value written through a project route can become a process
setting. Seat B's F1: a Developer picks the SLUG, the credential gate accepted any key inside
the slug's prefix, and `load_repo_env` copied every `.env` key into the server's environment, so
slug `http` + `HTTP_PROXY` (or `node`/`NODE_OPTIONS`, `ld`/`LD_PRELOAD`, `anthropic`/
`ANTHROPIC_BASE_URL`) steered the server. The fix is on both sides: a project's own keys are
never exported (the class), and a slug cannot swallow a variable the server already uses.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from auth_harness import gate_on, project, team, user_id
from fastapi import HTTPException
from fastapi.testclient import TestClient

from autotester.auth.access import set_owner
from autotester.browser.secrets import SecretStore, parse_env
from autotester.core.env import TEST_MARKER, load_repo_env
from autotester.store.project_store import ProjectStore
from autotester.ui.credential_guard import refuse_foreign_key, refuse_reserved_slug

ATTACKS = [("anthropic", "ANTHROPIC_BASE_URL"), ("http", "HTTP_PROXY"),
           ("node", "NODE_OPTIONS"), ("ld", "LD_PRELOAD"), ("pythonwarnings", "PYTHONWARNINGS_X"),
           ("ssl", "SSL_CERT_FILE"), ("aws", "AWS_ENDPOINT_URL")]


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _onboard(dev: TestClient, slug: str, key: str) -> int:
    return dev.post("/onboard", data={
        "slug": slug, "name": slug.title(), "base_url": f"https://{slug}.test",
        "allowed_domains": f"{slug}.test", "credential_key": key, "credential_value": "EVIL",
        "credential_domains": f"{slug}.test", "credential_description": ""}).status_code


def _restart(monkeypatch: pytest.MonkeyPatch, root: Path) -> list[str]:
    """What the next server start puts into the process environment (in a private copy)."""
    env = dict(os.environ)
    env.pop(TEST_MARKER, None)
    monkeypatch.setattr(os, "environ", env)
    return load_repo_env(root)


@pytest.mark.parametrize(("slug", "key"), ATTACKS)
def test_au21_no_onboarded_key_becomes_an_environment_variable(
        root: Path, monkeypatch: pytest.MonkeyPatch, slug: str, key: str) -> None:
    """The class, not four examples: whatever the Developer's slug and key, the value that
    lands in `.env` is never exported at the next start."""
    dev = team()["dev"]
    _onboard(dev, slug, key)
    _restart(monkeypatch, root)
    assert key not in os.environ and "EVIL" not in os.environ.values()


@pytest.mark.parametrize(("slug", "key"), ATTACKS[:4])
def test_au21_env_add_and_undeclare_leave_nothing_exported(
        root: Path, monkeypatch: pytest.MonkeyPatch, slug: str, key: str) -> None:
    """Declaring through `/env/add`, then removing the declaration (the value stays in `.env`),
    still exports nothing: the key sits in a project's namespace whether declared or not."""
    dev = team()["dev"]
    project(root, slug)  # a project that already exists (onboarding may now refuse the slug)
    set_owner(slug, user_id("dev@team.test"))
    resp = dev.post(f"/projects/{slug}/env/add", data={
        "key": key, "value": "EVIL", "domains": f"{slug}.test"})
    dev.post(f"/projects/{slug}/secrets/{key}/delete")
    assert resp.status_code in {303, 400, 403}
    _restart(monkeypatch, root)
    assert key not in os.environ and "EVIL" not in os.environ.values()


def test_au21_server_keys_still_load_next_to_a_project_with_a_colliding_slug(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A project named `anthropic` must not stop the operator's real provider key loading."""
    project(root, "anthropic")
    (root / ".env").write_text("ANTHROPIC_API_KEY=real\nAUTOTESTER_MAX_UPLOAD_BYTES=5\n"
                               "ANTHROPIC_BASE_URL=operator\nUNRELATED=1\n", encoding="utf-8")
    for name in ("ANTHROPIC_API_KEY", "AUTOTESTER_MAX_UPLOAD_BYTES", "UNRELATED"):
        monkeypatch.delenv(name, raising=False)
    loaded = _restart(monkeypatch, root)
    assert {"ANTHROPIC_API_KEY", "AUTOTESTER_MAX_UPLOAD_BYTES", "UNRELATED"} <= set(loaded)
    assert "ANTHROPIC_BASE_URL" not in loaded  # inside the project's namespace: never exported


def test_au21_legacy_declared_keys_still_resolve_but_are_not_exported(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`PATHLYNKS_*` keeps working for the browser (SecretStore reads the file); a declared
    key outside any namespace (legacy) is a project secret, not a process setting."""
    from autotester.schema.project import Project, SecretRef
    store = ProjectStore("pathlynks", root)
    store.save_project(Project(
        slug="pathlynks", name="P", base_url="https://p.test", allowed_domains=["p.test"],
        secrets=[SecretRef(key="PATHLYNKS_USER_PASSWORD", domains=["p.test"]),
                 SecretRef(key="LEGACY_LOGIN", domains=["p.test"])]))
    (root / ".env").write_text("PATHLYNKS_USER_PASSWORD=pw\nLEGACY_LOGIN=lg\n", encoding="utf-8")
    loaded = _restart(monkeypatch, root)
    assert loaded == []
    secrets = SecretStore.load(store.load_project(), root / ".env")
    assert secrets.resolve("{{SECRET:PATHLYNKS_USER_PASSWORD}}", "p.test") == "pw"
    assert secrets.resolve("{{SECRET:LEGACY_LOGIN}}", "p.test") == "lg"


@pytest.mark.parametrize("slug", ["anthropic", "autotester", "ollama", "openai", "gemini",
                                  "google"])
def test_au21_a_slug_that_swallows_a_server_key_is_refused_at_onboarding(
        root: Path, slug: str) -> None:
    """The slug's key prefix would cover a key the code reads (provider keys, AUTOTESTER_*)."""
    assert _onboard(team()["dev"], slug, f"{slug.upper()}_X") == 400
    assert ProjectStore(slug, root).load_project() is None


def test_au21_a_slug_that_swallows_a_variable_the_server_has_is_refused(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A set process variable (shell or `.env`) the new project's prefix would cover."""
    monkeypatch.setenv("HTTP_PROXY", "http://operator.test:3128")
    dev = team()["dev"]
    assert _onboard(dev, "http", "HTTP_USER") == 400
    (root / ".env").write_text("NODE_OPTIONS=--max-old-space-size=512\n", encoding="utf-8")
    assert _onboard(dev, "node", "NODE_USER") == 400
    assert _onboard(dev, "fresh", "FRESH_USER") == 303  # nothing collides: unchanged
    with pytest.raises(HTTPException):
        refuse_reserved_slug("http")


def test_au21_overlapping_namespaces_belong_to_the_longer_project(root: Path) -> None:
    """`alpha` must not claim `ALPHA_BETA_*`, which is the namespace of `alpha-beta`."""
    project(root, "alpha")
    project(root, "alpha-beta")
    with pytest.raises(HTTPException) as refused:
        refuse_foreign_key(ProjectStore("alpha", root).load_project(), "ALPHA_BETA_TOKEN")
    assert refused.value.status_code == 400
    refuse_foreign_key(ProjectStore("alpha-beta", root).load_project(), "ALPHA_BETA_TOKEN")
    refuse_foreign_key(ProjectStore("alpha", root).load_project(), "ALPHA_TOKEN")


def test_au21_env_editor_refuses_a_declared_server_key(root: Path) -> None:
    """`/projects/{slug}/env` writes only declared keys; one that names a server key is
    refused even if a legacy declaration holds it."""
    from autotester.schema.project import Project, SecretRef
    ProjectStore("legacy", root).save_project(Project(
        slug="legacy", name="L", base_url="https://l.test", allowed_domains=["l.test"],
        secrets=[SecretRef(key="AUTOTESTER_APPROVAL_KEY", domains=["l.test"])]))
    admin = team()["admin"]
    resp = admin.post("/projects/legacy/env", data={"key": "AUTOTESTER_APPROVAL_KEY",
                                                    "value": "EVIL"})
    assert resp.status_code == 403
    assert "EVIL" not in parse_env((root / ".env").read_text(encoding="utf-8")
                                   if (root / ".env").exists() else "").values()

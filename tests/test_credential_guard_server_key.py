"""E7.1-E7.2 (qa/contracts/e2e-fixes.md, AT-1416): the server's own Mongo URI is not a reason to
refuse the project name `pathlynks`, and because the exemption puts that name inside the
`pathlynks` namespace, a project may never declare it as one of its own credentials.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from auth_harness import gate_on, project, team
from fastapi import HTTPException

from autotester.core.env import MONGO_URI_ENV, mongo_uri
from autotester.store.project_store import ProjectStore
from autotester.ui.credential_guard import refuse_foreign_key, refuse_reserved_slug

URI = "mongodb://canary-user:canary-pass@db.example.test/"  # a fake value, never a real URI


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _onboard(slug: str) -> int:
    return team()["dev"].post("/onboard", data={
        "slug": slug, "name": slug.title(), "base_url": f"https://{slug}.test",
        "allowed_domains": f"{slug}.test", "credential_key": f"{slug.upper()}_USER",
        "credential_value": "pw-not-secret-xyz", "credential_domains": f"{slug}.test",
        "credential_description": ""}).status_code


def test_the_server_mongo_uri_does_not_block_the_slug_pathlynks(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    refuse_reserved_slug("pathlynks")  # before E7: HTTPException 400


def test_onboarding_pathlynks_succeeds_with_the_mongo_uri_in_the_environment(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    assert _onboard("pathlynks") == 303
    assert ProjectStore("pathlynks", root).load_project() is not None


def test_a_lower_case_spelling_of_the_name_does_not_block_either(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A case-sensitive environment may hold the name in any case (as `is_server_key` accepts);
    a plain dict stands in for it because Windows folds `os.environ` keys to upper case. The
    slug scan's own `startswith` is case-sensitive, so this is a characterisation, not a kill
    target: the `.upper()` in the filter is defensive and its removal is an equivalent mutant."""
    monkeypatch.setattr(os, "environ", {MONGO_URI_ENV.lower(): URI})
    refuse_reserved_slug("pathlynks")


def test_a_project_shaped_variable_still_blocks_the_slug(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """E7.2(a): ONE key is exempt, not the PATHLYNKS_ prefix."""
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    monkeypatch.setenv("PATHLYNKS_E2E_USER_PASSWORD", "x")
    with pytest.raises(HTTPException) as refused:
        refuse_reserved_slug("pathlynks")
    assert refused.value.status_code == 400


@pytest.mark.parametrize("slug", ["anthropic", "autotester", "ollama", "openai", "gemini"])
def test_a_slug_covering_a_server_key_is_still_refused_with_the_uri_set(
        monkeypatch: pytest.MonkeyPatch, slug: str) -> None:
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    with pytest.raises(HTTPException):
        refuse_reserved_slug(slug)


def test_a_slug_covering_another_held_variable_is_still_refused(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    monkeypatch.setenv("HTTP_PROXY", "http://operator.test:3128")
    with pytest.raises(HTTPException):
        refuse_reserved_slug("http")


@pytest.mark.parametrize("key", [MONGO_URI_ENV, MONGO_URI_ENV.lower(), f" {MONGO_URI_ENV} "])
def test_a_project_cannot_declare_the_store_uri_as_its_credential(
        root: Path, key: str) -> None:
    """E7.2(c): `refuse_foreign_key` answers 403, like `refuse_server_key`."""
    project(root, "pathlynks")
    loaded = ProjectStore("pathlynks", root).load_project()
    assert loaded is not None
    with pytest.raises(HTTPException) as refused:
        refuse_foreign_key(loaded, key)
    assert refused.value.status_code == 403


@pytest.mark.parametrize(("key", "status"), [(MONGO_URI_ENV, 403), (MONGO_URI_ENV.lower(), 400)])
def test_env_add_refuses_the_store_uri_with_no_write_and_no_declaration(
        root: Path, key: str, status: int) -> None:
    """The exact name answers 403 (`refuse_foreign_key`). A lower-case spelling never gets that
    far: `build_secret_ref`'s UPPER_SNAKE_CASE rule (E3.1, not E7's file) refuses it with 400
    first; its 403 spelling is pinned at the gate itself above. Either way nothing is written."""
    project(root, "pathlynks")
    resp = team()["admin"].post("/projects/pathlynks/env/add", data={
        "key": key, "value": "CANARY-OVERWRITE", "domains": "pathlynks.test",
        "description": ""})
    assert resp.status_code == status
    assert "CANARY-OVERWRITE" not in resp.text
    assert not (root / ".env").exists() or "CANARY-OVERWRITE" not in (root / ".env").read_text()
    stored = ProjectStore("pathlynks", root).load_project()
    assert stored is not None and stored.secrets == []


def test_other_pathlynks_keys_stay_claimable(root: Path) -> None:
    """The exemption names one key: a normal key in the namespace still passes the gate."""
    project(root, "pathlynks")
    loaded = ProjectStore("pathlynks", root).load_project()
    assert loaded is not None
    refuse_foreign_key(loaded, "PATHLYNKS_E2E_USER_PASSWORD")


def test_mongo_uri_still_resolves_after_a_pathlynks_project_exists(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """E7.2(d): from the process variable and from the repo-root `.env`."""
    project(root, "pathlynks")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    assert mongo_uri(root) == URI
    monkeypatch.delenv(MONGO_URI_ENV)
    (root / ".env").write_text(f"{MONGO_URI_ENV}={URI}\n", encoding="utf-8")
    assert mongo_uri(root) == URI

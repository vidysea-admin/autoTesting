"""AT-086/AT-087: the two exemption-scope residuals U9 left open on purpose,
now built per qa/gates/at086-at087-credential-exemption-scope.md ("go with the
best" -- AT-087 a, AT-086 a). Contract: qa/contracts/ui.md U9.

Split out from test_ui_credential_exemption.py rather than grown in place, at
doctor's 300-line cap -- same convention that file itself was split under.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import Action, CaseClass
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# -- AT-087: per-field, never a flat set --------------------------------------

def test_a_value_stored_under_one_field_does_not_exempt_a_different_field(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-087's second symptom: the flat exempt set let a value stored as one
    field (`name`) exempt a completely different field (`base_url`) it was
    never saved as, though U9 and the manifest both say 'that same field'.
    Per-field now: each field's exemption checks only what THAT field itself
    already holds."""
    shared = "https://demo.test/shared-collision-path"
    client.post("/onboard", data={
        "slug": "demo", "name": shared, "base_url": "https://demo.test/other",
        "allowed_domains": "demo.test",
    })
    # The .env entry appears AFTER onboarding -- same AT-078 pattern used
    # throughout test_ui_credential_exemption.py.
    (scratch_root / ".env").write_text(f"SHARED_TOKEN={shared}\n", encoding="utf-8")

    response = client.post("/projects/demo/edit", data={
        "name": shared,          # exempt for THIS field -- unchanged
        "base_url": shared,      # same text, but never stored AS base_url
        "allowed_domains": "demo.test",
    })

    assert response.status_code == 400
    assert (ProjectStore("demo", scratch_root).load_project().base_url
            == "https://demo.test/other")


# -- AT-087: an exempt field stays in the join as context --------------------

def test_a_credential_split_across_an_exempt_field_and_a_fresh_one_is_caught(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-087's primary symptom: dropping an exempt field from the join
    entirely hid a credential split across it and a fresh field. The checker
    isolated this against a control where the same split with a
    one-character-different (non-exempt) base_url was correctly refused."""
    secret = "ERP-TENANT-SPLIT-SECRET-VALUE"
    (scratch_root / ".env").write_text(f"SPLIT_SECRET={secret}\n", encoding="utf-8")
    half = len(secret) // 2
    base_url = "https://demo.test/" + secret[:half]
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": base_url,
        "allowed_domains": "demo.test",
    })

    # base_url resubmitted UNCHANGED (exempt on its own) + the rest of the
    # secret tacked onto allowed_domains -- still a valid domain list (it
    # keeps "demo.test", the reachability check's real requirement).
    response = client.post("/projects/demo/edit", data={
        "name": "Demo", "base_url": base_url,
        "allowed_domains": f"{secret[half:]},demo.test",
    })

    assert response.status_code == 400
    assert "split across" in response.text
    assert ProjectStore("demo", scratch_root).load_project().base_url == base_url


def test_resaving_a_projects_own_data_does_not_trip_the_join_check(
    client: TestClient, scratch_root: Path
) -> None:
    """The accepted risk in qa/gates/at086-at087-credential-exemption-scope.md:
    keeping an exempt field's OWN value in the join must not make its mere
    presence self-trigger the join's "does this contain a raw value" scan --
    only OTHER, non-exempt secrets reassembling across fields should. Also
    covers U9's "renamed while keeping a colliding base URL"."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })
    # The .env entry appears AFTER onboarding -- AT-078's own pattern: nothing
    # blocks onboarding itself, since nothing collides with .env yet.
    (scratch_root / ".env").write_text(
        "SOME_CONFIG_URL=https://demo.test/signin\n", encoding="utf-8")

    response = client.post("/projects/demo/edit", data={
        "name": "Demo Renamed", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert ProjectStore("demo", scratch_root).load_project().name == "Demo Renamed"


# -- AT-086: an explicitly declared-public .env key's value can be onboarded -

def test_onboarding_a_project_whose_base_url_is_a_declared_public_env_value(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-086: nothing is stored yet at onboarding time, so the AT-078
    already-stored exemption is empty for a brand-new project -- only an
    explicit, never-inferred declaration (core.env.PUBLIC_ENV_KEYS) can let a
    project whose own base_url matches a non-secret `.env` value onboard."""
    import autotester.core.env as core_env
    monkeypatch.setattr(core_env, "PUBLIC_ENV_KEYS", frozenset({"PUBLIC_PORTAL_URL"}))
    (scratch_root / ".env").write_text(
        "PUBLIC_PORTAL_URL=https://portal.test/login\n", encoding="utf-8")

    response = client.post("/onboard", data={
        "slug": "portal", "name": "Portal", "base_url": "https://portal.test/login",
        "allowed_domains": "portal.test",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert ProjectStore("portal", scratch_root).load_project() is not None


def test_a_key_not_on_the_declared_public_list_still_cannot_be_onboarded(
    client: TestClient, scratch_root: Path,
) -> None:
    """The exemption is an explicit list, never inferred: an ordinary,
    undeclared `.env` URL still blocks onboarding -- the residual AT-086
    deliberately leaves open (qa/gates/at086-at087-credential-exemption-scope.md)."""
    (scratch_root / ".env").write_text(
        "SOME_OTHER_URL=https://portal.test/login\n", encoding="utf-8")

    response = client.post("/onboard", data={
        "slug": "portal", "name": "Portal", "base_url": "https://portal.test/login",
        "allowed_domains": "portal.test",
    }, follow_redirects=False)

    assert response.status_code == 400
    assert not (scratch_root / "projects" / "portal").exists()


def test_declaring_a_key_public_does_not_exempt_a_different_key_with_the_same_value(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hard boundary: a declared-public key exempts only a value that appears
    EXCLUSIVELY under declared-public keys -- a different, undeclared key
    holding the identical string is still a credential and is still refused,
    even though its value collides with a declared-public one."""
    import autotester.core.env as core_env
    monkeypatch.setattr(core_env, "PUBLIC_ENV_KEYS", frozenset({"PUBLIC_PORTAL_URL"}))
    (scratch_root / ".env").write_text(
        "PUBLIC_PORTAL_URL=https://portal.test/login\n"
        "GEMINI_API_KEY=https://portal.test/login\n",  # same value, real secret key
        encoding="utf-8",
    )
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })

    response = client.post("/projects/demo/cases", data={
        "title": "https://portal.test/login", "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.NAVIGATE.value], "step_target": ["https://demo.test/"],
        "step_value": [""], "step_expected": [""],
    })

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_a_secret_declaration_cannot_widen_the_public_env_key_list(
    client: TestClient, scratch_root: Path,
) -> None:
    """The declared-public list lives in source (core.env.PUBLIC_ENV_KEYS), not
    anywhere an HTTP request can reach. Declaring a SecretRef -- the one
    Project field a request DOES control -- must not create a new exemption,
    even when its key name matches a real `.env` key byte-for-byte."""
    (scratch_root / ".env").write_text(
        "SOME_URL=https://portal.test/login\n", encoding="utf-8")
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    client.post("/projects/demo/secrets", data={
        "key": "SOME_URL", "domains": "demo.test",
    })

    response = client.post("/projects/demo/cases", data={
        "title": "https://portal.test/login", "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.NAVIGATE.value], "step_target": ["https://demo.test/"],
        "step_value": [""], "step_expected": [""],
    })

    assert response.status_code == 400

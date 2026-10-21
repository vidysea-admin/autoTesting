"""Credential safety on the routes that write `project.json`, and on the
encodings a pasted value can arrive in. Contract: qa/contracts/ui.md U8.

AT-073: the case-form guard stopped at the case form. A real credential typed
into a project NAME (onboarding or rename) or into a SecretRef's *description*
box went into git-tracked `project.json` in cleartext — and a name renders on
every page including the home index. The description box is one field from the
Key box on the same form, which is the likeliest place a hurried user pastes a
value. AT-074/AT-075 cover the trivially-recoverable encodings and the error
bodies that echoed raw input back.

Split from test_ui_credential_safety.py once that file passed doctor's 300-line cap.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import Action, CaseClass
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

REAL_PASSWORD = "hunter2-this-is-the-real-one"


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _project_with_credential(client: TestClient, scratch_root: Path, *, value: str = "") -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })
    client.post("/projects/demo/secrets", data={
        "key": "DEMO_PASSWORD", "domains": "demo.test", "mask_in_screenshot": "on",
    })
    if value:
        env_line = "DEMO_PASSWORD=" + value + chr(10)
        (scratch_root / ".env").write_text(env_line, encoding="utf-8")


def _add_case(client: TestClient, value: str):
    return client.post("/projects/demo/cases", data={
        "title": "Log in", "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.FILL.value], "step_target": ["input[type=password]"],
        "step_value": [value], "step_expected": [""],
    }, follow_redirects=False)


# -- AT-073: project.json is git-tracked too ---------------------------------

def test_a_credential_as_a_project_name_at_onboarding_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-073: a project NAME lands in git-tracked project.json AND renders on
    every page including the home index."""
    (scratch_root / ".env").write_text(f"DEMO_PASSWORD={REAL_PASSWORD}\n", encoding="utf-8")
    client.post("/onboard", data={
        "slug": "seed", "name": "Seed", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    client.post("/projects/seed/secrets", data={
        "key": "DEMO_PASSWORD", "domains": "demo.test", "mask_in_screenshot": "on",
    })

    response = client.post("/onboard", data={
        "slug": "leaky", "name": REAL_PASSWORD, "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code == 400
    assert not (scratch_root / "projects" / "leaky").exists()


def test_a_credential_in_the_secret_description_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """The description box sits one field from the Key box on the same form —
    the likeliest place a hurried user pastes the value."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = client.post("/projects/demo/secrets", data={
        "key": "SECOND_KEY", "domains": "demo.test", "description": REAL_PASSWORD,
    })

    assert response.status_code == 400
    project = ProjectStore("demo", scratch_root).load_project()
    assert REAL_PASSWORD not in project.model_dump_json()


def test_a_credential_shaped_slug_at_onboarding_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-079: `slug` becomes the directory name, every page's URL, and text on
    the home index — an ordinary credential shape (lowercase/digits/hyphens,
    which REAL_PASSWORD already is) was never checked, only its regex SHAPE."""
    (scratch_root / ".env").write_text(f"DEMO_PASSWORD={REAL_PASSWORD}\n", encoding="utf-8")
    client.post("/onboard", data={
        "slug": "seed2", "name": "Seed2", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    client.post("/projects/seed2/secrets", data={
        "key": "DEMO_PASSWORD", "domains": "demo.test", "mask_in_screenshot": "on",
    })

    response = client.post("/onboard", data={
        "slug": REAL_PASSWORD, "name": "Leaky", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code == 400
    assert not (scratch_root / "projects" / REAL_PASSWORD).exists()


def test_a_credential_in_a_project_rename_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = client.post("/projects/demo/edit", data={
        "name": REAL_PASSWORD, "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).load_project().name == "Demo"


def test_a_credential_shaped_key_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-080: `key` is the FIRST box on the secrets form and was never checked
    — an all-uppercase-with-underscores credential satisfies SecretRef's own
    key pattern, so only the description/scope boxes stood in the way."""
    key_shaped_password = "HUNTER2_THIS_IS_THE_REAL_ONE"
    _project_with_credential(client, scratch_root, value=key_shaped_password)

    response = client.post("/projects/demo/secrets", data={
        "key": key_shaped_password, "domains": "demo.test",
    })

    assert response.status_code == 400
    project = ProjectStore("demo", scratch_root).load_project()
    assert project.secret(key_shaped_password) is None


# -- AT-075: error bodies must not echo raw input ----------------------------

def test_an_unknown_case_class_is_not_echoed_back(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-075: `unknown case class '{x}'` put raw form input in the response
    body and the access log — the AT-068 pattern again."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = client.post("/projects/demo/cases", data={
        "title": "probe", "case_class": REAL_PASSWORD,
        "step_action": [Action.NAVIGATE.value], "step_target": ["https://demo.test/"],
        "step_value": [""], "step_expected": [""],
    })

    assert response.status_code == 400
    assert REAL_PASSWORD not in response.text


# -- AT-082: a stored credential must read back byte-for-byte ----------------

@pytest.mark.parametrize("value", [
    "p@ss #1",          # a whitespace-# was cut as a comment
    "  spaced  ",       # edge whitespace was stripped
    "'quoted'",         # a leading quote was unwrapped
    'has"double',
    "tab\there",
    "plain-ok",
])
def test_a_stored_credential_reads_back_exactly(scratch_root: Path, value: str) -> None:
    """AT-082: `set_env_value` wrote the value bare, so `parse_env`'s comment
    stripping, rstrip and unquoting silently mangled it — `p@ss #1` was stored
    as `p@ss` — while the Credentials page still reported "Set". The failure
    surfaced much later as a wrong-password login."""
    from autotester.browser.secrets import parse_env
    from autotester.ui.env_editor import set_env_value

    env = scratch_root / ".env"
    set_env_value(env, "DEMO_PASSWORD", value)

    assert parse_env(env.read_text(encoding="utf-8"))["DEMO_PASSWORD"] == value


def test_a_value_that_cannot_round_trip_is_refused_not_mangled(
    scratch_root: Path
) -> None:
    """Where no quoting makes both `.env` readers return the value, refusing is honest;
    storing something different from what the user typed is not. AT-1368 made `a"b'c`
    storable (single quotes hold it exactly), so this pins a value that still has no safe
    form: it needs quoting because of ` #` and holds both quote kinds."""
    from autotester.ui.env_editor import InvalidEnvValue, set_env_value

    env = scratch_root / ".env"
    before = env.read_bytes() if env.exists() else None
    value = "p@ss #1 \"q\" 'r'"
    with pytest.raises(InvalidEnvValue) as refused:
        set_env_value(env, "DEMO_PASSWORD", value)
    assert value not in str(refused.value)
    assert (env.read_bytes() if env.exists() else None) == before


def test_setting_one_value_leaves_the_others_intact(scratch_root: Path) -> None:
    from autotester.browser.secrets import parse_env
    from autotester.ui.env_editor import set_env_value

    env = scratch_root / ".env"
    set_env_value(env, "FIRST_KEY", "first #value")
    set_env_value(env, "SECOND_KEY", "  second  ")
    set_env_value(env, "FIRST_KEY", "changed #again")

    parsed = parse_env(env.read_text(encoding="utf-8"))
    assert parsed["FIRST_KEY"] == "changed #again"
    assert parsed["SECOND_KEY"] == "  second  "


# -- AT-339: the guard matched case-SENSITIVELY ------------------------------

UPPER_CREDENTIAL = "ZEBRA_QUILT_APIKEY_31"
"""A real `.env` value in the shape API keys actually take: upper snake case.
`REAL_PASSWORD` above is already lowercase-with-hyphens, so every test written
against it exercised the one casing where a plain substring test happens to
work -- which is why this class survived AT-073, AT-074 and AT-079."""

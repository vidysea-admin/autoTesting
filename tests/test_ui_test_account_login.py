"""E3 (qa/contracts/e2e-fixes.md, AT-1417 + AT-1418): one "Test account login" block on /onboard
and /projects/<slug>/env, generated keys, plain inline errors that keep the typed non-secret
fields, values never echoed, Save reachable at a narrow width. HTTP-level, no browser."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.browser.secrets import parse_env
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

SLUG = "pathlynks-e2e"
HOST = "pathlynks.vidysea.com"
EMAIL, PW, PW2 = "canary.user@example.invalid", "Canary-pw-7731", "Canary-pw-9902"
USER_KEY, PASS_KEY = "PATHLYNKS_E2E_USER_EMAIL", "PATHLYNKS_E2E_USER_PASSWORD"
LOGIN = {"block": "login", "login_email": EMAIL, "login_password": PW, "login_scope": HOST}


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _project(root: Path, slug: str = SLUG, **extra) -> ProjectStore:
    store = ProjectStore(slug, root)
    store.save_project(Project(slug=slug, name=slug, base_url=f"https://{HOST}/signin",
                               allowed_domains=[HOST], **extra))
    return store


def _everywhere(*responses) -> str:
    return "".join(f"{r.text}{r.headers}{r.url}" for r in responses)


# -- E3.1 a bad key is a plain inline message --------------------------------

@pytest.mark.parametrize("route,extra", [
    ("env/add", {"value": "CANARYVALUE-4471"}),
    ("secrets", {}),
])
def test_bad_key_rerenders_the_form_with_a_plain_message(
        client: TestClient, root: Path, route: str, extra: dict) -> None:
    store = _project(root)
    data = {"key": "pathlynks password", "domains": HOST, "description": "my note", **extra}
    resp = client.post(f"/projects/{SLUG}/{route}", data=data)
    assert resp.status_code in (200, 400)
    body = resp.text
    assert "Key must be UPPER_SNAKE_CASE and start with PATHLYNKS_E2E_" in body
    assert "for example PATHLYNKS_E2E_API_TOKEN" in body
    assert "String should match pattern" not in body
    assert "<main>" in body and "Back to projects" not in body  # site chrome, not the error page
    assert "pathlynks password" in body and "my note" in body  # typed fields kept
    assert "CANARYVALUE-4471" not in _everywhere(resp)
    assert store.load_project().secrets == []
    assert not (root / ".env").exists()


# -- E3.2 one block on both pages --------------------------------------------

def test_both_pages_offer_the_test_account_login_block(client: TestClient, root: Path) -> None:
    _project(root)
    for url in ("/onboard", f"/projects/{SLUG}/env"):
        body = client.get(url).text
        assert "Test account login" in body, url
        assert "Email or username" in body, url
        assert len(re.findall(r"name='login_password'", body)) == 1, url
        tag = re.search(r"<input[^>]*name='login_password'[^>]*>", body)
        assert tag and "type='password'" in tag.group(0), url
        assert "autocomplete='new-password'" in tag.group(0), url
        assert "name='login_email'" in body and "name='login_scope'" in body, url
    env_page = client.get(f"/projects/{SLUG}/env").text
    assert "custom credential" in env_page and "name='key'" in env_page  # extras remain
    assert f"value='{HOST}'" in env_page  # E3.4 prefilled scope


def test_one_definition_of_the_key_pair_helper() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "autotester"
    hits = [p for p in src.rglob("*.py") if "def login_keys" in p.read_text(encoding="utf-8")]
    literal = [p for p in src.rglob("*.py") if "USER_EMAIL" in p.read_text(encoding="utf-8")]
    assert len(hits) == 1 and len(literal) == 1 and hits == literal


# -- E3.3 keys generated, resubmit updates ------------------------------------

def test_onboarding_through_the_block_declares_exactly_two_generated_keys(
        client: TestClient, root: Path) -> None:
    resp = client.post("/onboard", follow_redirects=False, data={
        "slug": SLUG, "name": "E2E", "base_url": f"https://{HOST}/signin",
        "allowed_domains": HOST, "login_email": EMAIL, "login_password": PW,
        "login_scope": ""})  # blank scope defaults to the URL host (E3.4)
    assert resp.status_code == 303, resp.text
    project = ProjectStore(SLUG, root).load_project()
    assert [s.key for s in project.secrets] == [USER_KEY, PASS_KEY]
    by_key = {s.key: s for s in project.secrets}
    assert by_key[PASS_KEY].mask_in_screenshot is True
    assert all(s.domains == [HOST] for s in project.secrets)
    env = parse_env((root / ".env").read_text(encoding="utf-8"))
    assert env[USER_KEY] == EMAIL and env[PASS_KEY] == PW
    page = client.get(f"/projects/{SLUG}/env")
    assert EMAIL not in _everywhere(resp, page) and PW not in _everywhere(resp, page)


def test_resubmitting_updates_the_values_and_never_duplicates(
        client: TestClient, root: Path) -> None:
    store = _project(root)
    first = client.post(f"/projects/{SLUG}/env/add", data=LOGIN, follow_redirects=False)
    assert first.status_code == 303
    second = client.post(f"/projects/{SLUG}/env/add", follow_redirects=False,
                         data={**LOGIN, "login_password": PW2})
    assert second.status_code == 303
    assert [s.key for s in store.load_project().secrets] == [USER_KEY, PASS_KEY]
    assert parse_env((root / ".env").read_text(encoding="utf-8"))[PASS_KEY] == PW2


def test_a_project_cannot_claim_a_longer_neighbour_namespace(
        client: TestClient, root: Path) -> None:
    _project(root, "alpha")
    _project(root, "alpha-beta")
    resp = client.post("/projects/alpha/env/add", data={
        "key": "ALPHA_BETA_TOKEN", "value": "x", "domains": HOST})
    assert resp.status_code == 400
    assert ProjectStore("alpha", root).load_project().secrets == []


def test_role_account_project_keeps_its_own_keys(client: TestClient, root: Path) -> None:
    store = _project(root, secrets=[SecretRef(key="PATHLYNKS_E2E_ADMIN_USER", domains=[HOST])])
    client.post(f"/projects/{SLUG}/env/add", data=LOGIN, follow_redirects=False)
    assert [s.key for s in store.load_project().secrets] == [
        "PATHLYNKS_E2E_ADMIN_USER", USER_KEY, PASS_KEY]


# -- E3.4 scope never widens ---------------------------------------------------

def test_scope_outside_allowed_domains_is_refused_inline(
        client: TestClient, root: Path) -> None:
    store = _project(root)
    resp = client.post(f"/projects/{SLUG}/env/add", data={**LOGIN, "login_scope": "evil.example"})
    assert resp.status_code in (200, 400)
    assert "<main>" in resp.text and "allowed domains" in resp.text
    assert EMAIL not in _everywhere(resp) and PW not in _everywhere(resp)
    assert store.load_project().secrets == [] and not (root / ".env").exists()


def test_onboarding_with_a_foreign_scope_saves_nothing(client: TestClient, root: Path) -> None:
    resp = client.post("/onboard", data={
        "slug": SLUG, "name": "E2E", "base_url": f"https://{HOST}/signin",
        "allowed_domains": HOST, "login_email": EMAIL, "login_password": PW,
        "login_scope": "evil.example"})
    assert resp.status_code in (200, 400)
    assert "allowed domains" in resp.text and f"value='{SLUG}'" in resp.text
    assert EMAIL not in _everywhere(resp) and PW not in _everywhere(resp)
    assert ProjectStore(SLUG, root).load_project() is None


def test_half_a_login_is_refused(client: TestClient, root: Path) -> None:
    store = _project(root)
    resp = client.post(f"/projects/{SLUG}/env/add", data={**LOGIN, "login_password": ""})
    assert resp.status_code == 400 and "<main>" in resp.text
    assert store.load_project().secrets == [] and EMAIL not in resp.text


# -- E3.5 values never echoed; the guard is untouched --------------------------

def test_values_never_reach_a_response_or_a_log(
        client: TestClient, root: Path, caplog: pytest.LogCaptureFixture) -> None:
    _project(root)
    caplog.set_level(logging.DEBUG)
    seen = [client.post(f"/projects/{SLUG}/env/add", data=LOGIN, follow_redirects=False),
            client.get(f"/projects/{SLUG}/env"), client.get("/onboard")]
    assert EMAIL not in _everywhere(*seen) and PW not in _everywhere(*seen)
    assert EMAIL not in caplog.text and PW not in caplog.text


def test_pasted_secret_in_the_scope_box_is_still_refused(client: TestClient, root: Path) -> None:
    _project(root)
    client.post(f"/projects/{SLUG}/env/add", data=LOGIN, follow_redirects=False)
    resp = client.post(f"/projects/{SLUG}/env/add", data={**LOGIN, "login_scope": PW})
    assert resp.status_code == 400 and PW not in _everywhere(resp)


# -- E3.6 narrow-width layout (markup contract; the screenshot is the checker's) ----

def test_credential_table_stacks_on_a_narrow_screen(client: TestClient, root: Path) -> None:
    _project(root, secrets=[SecretRef(key=PASS_KEY, domains=[HOST])])
    body = client.get(f"/projects/{SLUG}/env").text
    assert "class='table-scroll'" in body and "class='cred-table'" in body
    assert "@media (max-width: 640px)" in body and ".cred-value" in body
    assert re.search(r"<td class='cred-save'><button[^>]*>Save</button>", body)

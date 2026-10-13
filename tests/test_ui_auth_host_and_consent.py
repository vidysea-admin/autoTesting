"""T-204 login composed with the Host allow-list and the consent gates
(qa/contracts/auth.md AU15, AU18, AU19, AU20): the guard runs before the login gate on
every route, AT-760/AT-761 hold on the auth routes, and a role never skips an approval."""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login, project, team, user_id
from fastapi.testclient import TestClient

from autotester.auth.access import set_owner
from autotester.auth.db import auth_db_path
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app
from autotester.ui.env_editor import set_env_value

JSON = {"accept": "application/json"}
SENTINEL = "Host-Guard-Sentinel-51c7"


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _at(host: str, scheme: str = "http", **kwargs: object) -> TestClient:
    return TestClient(app, base_url=f"{scheme}://{host}", follow_redirects=False, **kwargs)


def _sessions() -> int:
    import sqlite3
    return sqlite3.connect(auth_db_path()).execute("SELECT COUNT(*) FROM sessions").fetchone()[0]


# -- AU19: the Host allow-list answers before the login gate does -------------------------

@pytest.mark.parametrize("host", ["evil.example", "localhost.evil.com", "127.0.0.1.evil.io"])
def test_au19_a_foreign_host_gets_no_login_page_and_no_session(root: Path, host: str) -> None:
    account(ADMIN)
    before = _sessions()
    got = _at(host).get("/auth/login")
    assert got.status_code == 403 and got.content == b"" and "set-cookie" not in got.headers
    posted = _at(host).post("/auth/login", data={"email": ADMIN, "password": PASSWORD})
    assert posted.status_code == 403 and "set-cookie" not in posted.headers
    assert _at(host).get("/healthz").status_code == 403
    assert _sessions() == before


def test_au19_a_signed_in_admin_still_reads_no_credential_under_a_foreign_host(
        root: Path) -> None:
    """A rebinding page reaches the server under its own Host with the victim's cookie."""
    account(ADMIN)
    cookie = login(ADMIN).cookies["at_session"]
    ProjectStore("vault", root).save_project(Project(
        slug="vault", name="Vault", base_url="https://vault.test", allowed_domains=["vault.test"],
        secrets=[SecretRef(key="VAULT_PASSWORD", domains=["vault.test"])]))
    set_env_value(root / ".env", "VAULT_PASSWORD", SENTINEL)
    same = client(cookies={"at_session": cookie}).get("/projects/vault/env")
    assert same.status_code == 200 and SENTINEL in same.text  # the control: Admin sees it
    foreign = _at("evil.example", cookies={"at_session": cookie}).get("/projects/vault/env")
    assert foreign.status_code == 403 and SENTINEL not in foreign.text


def test_au19_a_listed_host_can_sign_in_and_reach_the_app(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "testserver login.team.test")
    c = _at("login.team.test")
    done = c.post("/auth/login", data={"email": ADMIN, "password": PASSWORD})
    assert done.status_code == 303 and "at_session=" in done.headers["set-cookie"]
    assert c.get("/", headers=JSON).status_code == 200


def test_au19_the_host_of_an_allowed_origin_is_enough_when_hosted(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)
    monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS")
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "https://at.team.test")
    c = _at("at.team.test", "https")
    done = c.post("/auth/login", data={"email": ADMIN, "password": PASSWORD},
                  headers={"origin": "https://at.team.test"})
    assert done.status_code == 303 and done.headers["set-cookie"].startswith("__Host-at_session=")
    assert c.get("/", headers=JSON).status_code == 200
    # the same server name under a different Host header is refused
    assert _at("elsewhere.team.test", "https").get("/auth/login").status_code == 403


# -- AU18: AT-760 and AT-761 on the auth routes -------------------------------------------

@pytest.mark.parametrize("path", ["/auth/login", "/auth/signup", "/auth/logout"])
def test_au18_a_non_numeric_origin_port_is_refused_on_auth_routes(root: Path, path: str) -> None:
    account(ADMIN)
    before = _sessions()
    resp = client().post(path, headers={"origin": "http://localhost:8000.evil.com"},
                         data={"email": ADMIN, "password": PASSWORD})
    assert resp.status_code == 403 and _sessions() == before


@pytest.mark.parametrize("header", ["origin", "host"])
def test_au18_a_repeated_origin_or_host_header_is_refused_on_login(
        root: Path, header: str) -> None:
    account(ADMIN)
    before = _sessions()
    pairs = [("origin", "http://testserver"), ("origin", "http://testserver")] \
        if header == "origin" else [("host", "testserver"), ("host", "testserver")]
    resp = client().post("/auth/login", headers=pairs,
                         data={"email": ADMIN, "password": PASSWORD})
    assert resp.status_code == 403 and _sessions() == before


def test_au18_a_wildcard_in_the_allowed_origins_allows_nothing(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "*")
    resp = client().post("/auth/login", headers={"origin": "https://evil.example"},
                         data={"email": ADMIN, "password": PASSWORD})
    assert resp.status_code == 403


# -- AU15: a role never skips an approval -------------------------------------------------

def test_au15_admin_and_developer_get_the_same_missing_approval_refusal(root: Path) -> None:
    users = team()
    project(root, "vault")
    set_owner("vault", user_id("dev@team.test"))
    admin = users["admin"].post("/projects/vault/explore")
    dev = users["dev"].post("/projects/vault/explore")
    assert admin.status_code == dev.status_code == 403
    assert "Crawl approval required" in admin.text and "Crawl approval required" in dev.text

"""T-204 unauthenticated surface, startup gate, guard layering, secrets display and
audit (qa/contracts/auth.md AU16, AU17/AU20, AU18, AU21, AU22)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from auth_harness import (
    ADMIN,
    PASSWORD,
    account,
    app_routes,
    client,
    gate_on,
    login,
    team,
    user_id,
)

from autotester.auth import accounts, groups
from autotester.auth.access import set_owner, set_relation
from autotester.auth.config import AuthConfigError, auth_disabled, check_startup
from autotester.schema.auth import ProjectRelation
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.env_editor import set_env_value

JSON = {"accept": "application/json"}
HTML = {"accept": "text/html"}
PUBLIC = {("GET", "/auth/login"), ("POST", "/auth/login"), ("GET", "/auth/signup"),
          ("POST", "/auth/signup"), ("GET", "/healthz")}
SENTINEL = "Sentinel-Value-93ad1c"


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}


# -- AU16 ---------------------------------------------------------------------------

def test_au16_only_the_public_set_answers_unsigned_in(root: Path) -> None:
    account(ADMIN)
    before = _tree(root)
    c = client()
    for method, template in app_routes():
        if (method, template) in PUBLIC:
            continue
        path = re.sub(r"\{[^}]+\}", "probe<x>", template)
        as_json = c.request(method, path, headers=JSON)
        assert as_json.status_code == 401, (method, template, as_json.status_code)
        assert "probe" not in as_json.text
        as_html = c.request(method, path, headers=HTML)
        assert as_html.status_code == 302, (method, template)
        assert as_html.headers["location"].startswith("/auth/login?next=/")
    assert _tree(root) == before


@pytest.mark.parametrize("path", ["/x?next=https://evil.example", "//evil.example/"])
def test_au16_redirect_never_points_off_site(root: Path, path: str) -> None:
    resp = client().get(path, headers=HTML)
    assert resp.status_code in {302, 401}
    location = resp.headers.get("location", "")
    assert "evil.example" not in location.split("?next=")[0]
    assert not location.split("?next=")[-1].startswith("//")


@pytest.mark.parametrize("given", ["https://evil.example/", "//evil.example",
                                   "javascript:alert(1)", "/\\evil.example"])
def test_au16_login_page_drops_unsafe_next(root: Path, given: str) -> None:
    page = client().get("/auth/login", params={"next": given}).text
    assert "evil.example" not in page and "javascript:" not in page


# -- AU17 / AU20 --------------------------------------------------------------------

def test_au17_disabled_flag_is_refused_when_hosted(root: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
    monkeypatch.setattr("sys.argv", ["uvicorn", "--host", "127.0.0.1"])
    assert auth_disabled()
    check_startup()
    monkeypatch.setattr("sys.argv", ["uvicorn", "--host", "0.0.0.0"])
    assert not auth_disabled()
    with pytest.raises(AuthConfigError):
        check_startup()
    monkeypatch.setattr("sys.argv", ["uvicorn"])
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "at.example")
    assert not auth_disabled()
    with pytest.raises(AuthConfigError):
        check_startup()


def test_au20_hosted_needs_an_allow_list(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS", raising=False)  # the harness lists testserver
    monkeypatch.delenv("AUTOTESTER_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(AuthConfigError):
        check_startup()
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", "https://at.example")
    check_startup()


def test_au17_gate_is_on_by_default(root: Path) -> None:
    assert not auth_disabled()
    assert client().get("/", headers=JSON).status_code == 401


# -- AU18 ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/auth/login", "/auth/signup", "/auth/logout",
                                  "/admin/groups", "/onboard"])
def test_au18_cross_origin_post_with_a_valid_cookie_is_403(root: Path, path: str) -> None:
    account(ADMIN)
    c = login(ADMIN)
    count = len(groups.list_groups())
    resp = c.post(path, headers={"origin": "https://evil.example"},
                  data={"email": ADMIN, "password": PASSWORD, "name": "Evil"})
    assert resp.status_code == 403
    assert len(groups.list_groups()) == count
    assert c.get("/", headers=JSON).status_code == 200


def test_au18_guard_runs_before_the_login_gate(root: Path) -> None:
    resp = client().post("/admin/groups", headers={"origin": "https://evil.example", **JSON})
    assert resp.status_code == 403  # the guard's refusal, not the gate's 401


# -- AU21 ---------------------------------------------------------------------------

def _secret_project(root: Path) -> None:
    ProjectStore("vault", root).save_project(Project(
        slug="vault", name="Vault", base_url="https://vault.test",
        allowed_domains=["vault.test"],
        secrets=[SecretRef(key="VAULT_PASSWORD", domains=["vault.test"]),
                 SecretRef(key="VAULT_EMAIL", domains=["vault.test"])]))
    set_env_value(root / ".env", "VAULT_PASSWORD", SENTINEL)
    set_env_value(root / ".env", "VAULT_EMAIL", SENTINEL + "-mail")


def test_au21_values_only_for_credentials_view(root: Path) -> None:
    _secret_project(root)
    users = team()
    set_owner("vault", user_id("dev@team.test"))
    set_relation("vault", user_id("sub@team.test"), ProjectRelation.ASSIGNED, True)
    set_relation("vault", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    for name, c in users.items():
        page = c.get("/projects/vault/env")
        assert page.status_code == 200, name
        assert (SENTINEL in page.text) == (name == "admin"), name
        if name != "admin":
            assert "Set" in page.text or "set" in page.text


def test_au21_write_without_view_is_not_echoed(root: Path) -> None:
    _secret_project(root)
    users = team()
    set_owner("vault", user_id("dev@team.test"))
    resp = users["dev"].post("/projects/vault/env",
                             data={"key": "VAULT_PASSWORD", "value": "fresh-" + SENTINEL})
    assert resp.status_code in {200, 303}
    assert "fresh-" not in resp.text and "fresh-" not in resp.headers.get("location", "")
    assert "fresh-" + SENTINEL in (root / ".env").read_text(encoding="utf-8")
    assert "fresh-" not in users["dev"].get("/projects/vault/env").text


def test_au21_settings_page_hides_values_and_counts_env_keys(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)
    ops = groups.create_group("Ops", ["settings.manage"])
    uid = account("ops@team.test")
    accounts.set_user_groups(uid, [ops.id])
    set_env_value(root / ".env", "ANTHROPIC_API_KEY", SENTINEL)
    monkeypatch.setenv("OPENAI_API_KEY", "env-only-" + SENTINEL)
    page = login("ops@team.test").get("/settings/providers").text
    assert SENTINEL not in page
    row = page.split("OPENAI_API_KEY")[1].split("</tr>")[0]
    assert "● Set" in row
    assert SENTINEL in login(ADMIN).get("/settings/providers").text


# -- AU22 ---------------------------------------------------------------------------

def test_au22_audit_lines_hold_no_secret(root: Path) -> None:
    canary = "Audit-Canary-Pw-55"
    client().post("/auth/signup", data={"email": ADMIN, "password": canary})
    client().post("/auth/login", data={"email": ADMIN, "password": "wrong-" + canary})
    c = login(ADMIN, canary)
    cookie = c.cookies["at_session"]
    uid = account("t@team.test")
    c.post(f"/admin/users/{uid}/password", data={"password": "Reset-" + canary})
    audit = (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")
    for needle in (canary, cookie, "$argon2"):
        assert needle not in audit
    assert '"action": "login-failed"' in audit or '"action":"login-failed"' in audit
    assert "/admin/users/{user_id}/{action}" in audit and "user.password" in audit

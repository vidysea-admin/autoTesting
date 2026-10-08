"""T-204 fix cycle 1: the findings of the two blind checkers, each pinned by a test that
fails on the defect (qa/manifests/t204-auth.md "Fix cycle 1"). Credential key namespace
(AU21), `__Host-` cookie (AU3), escaped titles (AU16), no-store (AU25), signup and limiter
bounds (AU5), and the dummy-hash survivor E2. The survivors x1, x2, E22 and the audit-file
redirect are in test_ui_auth_survivors.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login, project, team, user_id
from fastapi import HTTPException
from fastapi.testclient import TestClient

from autotester.auth import passwords, ratelimit
from autotester.auth.access import set_owner
from autotester.auth.ratelimit import LoginRateLimiter, signup_limiter
from autotester.browser.secrets import parse_env
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.credential_guard import refuse_foreign_key

JSON = {"accept": "application/json"}
HTML = {"accept": "text/html"}


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _env(root: Path) -> dict[str, str]:
    path = root / ".env"
    return parse_env(path.read_text(encoding="utf-8")) if path.exists() else {}


def _dev_project(root: Path, slug: str = "devproj") -> TestClient:
    """A Developer who owns `slug` (credentials.edit@own on it)."""
    users = team()
    project(root, slug)
    set_owner(slug, user_id("dev@team.test"))
    return users["dev"]


# -- F1 / AU21: a project route writes only the project's own namespaced keys -------------

@pytest.mark.parametrize("key", ["ANTHROPIC_API_KEY", "AUTOTESTER_APPROVAL_KEY",
                                 "AUTOTESTER_AUTH_DISABLED", "VICTIM_PASSWORD",
                                 "LITELLM_API_BASE", "LITELLM_API_KEY", "AUTOTESTER_MODEL"])
def test_au21_developer_cannot_write_a_foreign_key_through_env_add(root: Path, key: str) -> None:
    """A Developer who owns a project posts /env/add with a provider key, a control key or
    another project's key: refused, `.env` and the project's declarations untouched."""
    dev = _dev_project(root)
    resp = dev.post("/projects/devproj/env/add", data={
        "key": key, "value": "ATTACKER", "domains": "devproj.test"})
    assert resp.status_code in {400, 403}
    assert "ATTACKER" not in _env(root).values()
    assert ProjectStore("devproj", root).load_project().secrets == []


def test_au21_developer_writes_a_key_in_the_projects_own_namespace(root: Path) -> None:
    dev = _dev_project(root)
    resp = dev.post("/projects/devproj/env/add", data={
        "key": "DEVPROJ_TENANT_ID", "value": "t-42", "domains": "devproj.test"})
    assert resp.status_code == 303
    assert _env(root)["DEVPROJ_TENANT_ID"] == "t-42"


@pytest.mark.parametrize(("slug", "key"), [("anthropic", "ANTHROPIC_API_KEY"),
                                           ("autotester", "AUTOTESTER_APPROVAL_KEY"),
                                           ("litellm", "LITELLM_API_BASE"),
                                           ("litellm", "LITELLM_API_KEY"),
                                           ("autotester", "AUTOTESTER_MODEL")])
def test_au21_server_wide_keys_are_403_even_inside_the_namespace(
        root: Path, slug: str, key: str) -> None:
    """A slug that happens to match the key's prefix still cannot declare a provider key or
    an AUTOTESTER_* key: those are `settings.manage` and go through Settings."""
    dev = _dev_project(root, slug)
    for route in ("env/add", "secrets"):
        resp = dev.post(f"/projects/{slug}/{route}", data={
            "key": key, "value": "ATTACKER", "domains": f"{slug}.test"})
        assert resp.status_code == 403, route
    assert ProjectStore(slug, root).load_project().secrets == []
    assert "ATTACKER" not in _env(root).values()


def test_au21_secrets_route_refuses_another_projects_key(root: Path) -> None:
    """The second path B found: declaring `VICTIM_PASSWORD` on the developer's own project
    would type the victim's value into the developer's site."""
    dev = _dev_project(root)
    ProjectStore("victim", root).save_project(Project(
        slug="victim", name="Victim", base_url="https://victim.test",
        allowed_domains=["victim.test"],
        secrets=[SecretRef(key="VICTIM_PASSWORD", domains=["victim.test"])]))
    resp = dev.post("/projects/devproj/secrets", data={
        "key": "VICTIM_PASSWORD", "domains": "devproj.test"})
    assert resp.status_code in {400, 403}
    assert ProjectStore("devproj", root).load_project().secrets == []


def test_au21_a_key_another_project_declares_inside_my_prefix_is_refused(root: Path) -> None:
    """`devproj` owns the prefix DEVPROJ_, but `devproj-x` declared DEVPROJ_X_TOKEN first."""
    _dev_project(root)
    ProjectStore("devproj-x", root).save_project(Project(
        slug="devproj-x", name="X", base_url="https://x.test", allowed_domains=["x.test"],
        secrets=[SecretRef(key="DEVPROJ_X_TOKEN", domains=["x.test"])]))
    mine = ProjectStore("devproj", root).load_project()
    with pytest.raises(HTTPException) as refused:
        refuse_foreign_key(mine, "DEVPROJ_X_TOKEN")
    assert refused.value.status_code == 400
    refuse_foreign_key(mine, "DEVPROJ_OWN_TOKEN")  # a fresh key in the namespace is fine


def test_au21_admin_gets_the_same_refusal_and_uses_settings_instead(root: Path) -> None:
    team()
    project(root, "devproj")
    admin = login(ADMIN)
    refused = admin.post("/projects/devproj/env/add", data={
        "key": "GEMINI_API_KEY", "value": "ADMIN-VIA-SETTINGS", "domains": "devproj.test"})
    assert refused.status_code == 403 and "GEMINI_API_KEY" not in _env(root)
    ok = admin.post("/settings/providers", data={"key": "GEMINI_API_KEY",
                                                 "value": "ADMIN-VIA-SETTINGS"})
    assert ok.status_code == 303 and _env(root)["GEMINI_API_KEY"] == "ADMIN-VIA-SETTINGS"


@pytest.mark.parametrize("key", ["AUTOTESTER_AUTH_DISABLED", "ANTHROPIC_API_KEY",
                                 "DEVPROJ_FOREIGN_PASSWORD", "HISTORIC_PASSWORD"])
def test_au21_existing_secret_refs_cannot_write_server_or_foreign_keys(
    root: Path, key: str,
) -> None:
    """Persisted refs are not write authority; target-prefixed collisions also refuse."""
    dev = _dev_project(root)
    store = ProjectStore("devproj", root)
    model = store.load_project()
    model.secrets.append(SecretRef(key=key, domains=["devproj.test"]))
    store.save_project(model)
    if key in {"DEVPROJ_FOREIGN_PASSWORD", "HISTORIC_PASSWORD"}:
        ProjectStore("victim", root).save_project(Project(
            slug="victim", name="Victim", base_url="https://victim.test",
            secrets=[SecretRef(key=key, domains=["victim.test"])]))
    env = root / ".env"
    env.write_bytes(f"{key}=old-fixture-secret\n".encode())
    before = (root / "projects/devproj/project.json").read_bytes()
    reply = dev.post("/projects/devproj/env", data={"key": key, "value": "ATTACKER-CANARY"},
                     follow_redirects=False)
    assert reply.status_code in {400, 403}
    assert "ATTACKER-CANARY" not in reply.text and "old-fixture-secret" not in reply.text
    assert env.read_bytes() == f"{key}=old-fixture-secret\n".encode()
    assert (root / "projects/devproj/project.json").read_bytes() == before


def test_au21_own_existing_unprefixed_key_remains_editable_without_migration(root: Path) -> None:
    dev = _dev_project(root)
    store = ProjectStore("devproj", root)
    model = store.load_project()
    model.secrets.append(SecretRef(key="HISTORIC_PASSWORD", domains=["devproj.test"]))
    store.save_project(model)
    before = (root / "projects/devproj/project.json").read_bytes()
    reply = dev.post("/projects/devproj/env", data={
        "key": "HISTORIC_PASSWORD", "value": "owned-fixture-value"}, follow_redirects=False)
    assert reply.status_code == 303
    assert "owned-fixture-value" not in reply.text
    assert _env(root)["HISTORIC_PASSWORD"] == "owned-fixture-value"
    assert (root / "projects/devproj/project.json").read_bytes() == before


# -- F2 / AU3: with the Secure cookie, only the `__Host-` name is a session ---------------

def _hosted_token(monkeypatch: pytest.MonkeyPatch) -> str:
    account(ADMIN)
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    resp = client().post("/auth/login", data={"email": ADMIN, "password": PASSWORD})
    header = resp.headers["set-cookie"]
    assert header.startswith("__Host-at_session=")
    return header.split("=", 1)[1].split(";", 1)[0]


def test_au3_hosted_accepts_only_the_host_prefixed_cookie(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cookie tossing: a sibling subdomain or a plain-HTTP response can plant `at_session`
    but never a `__Host-` cookie, so the plain name must not log anyone in when hosted."""
    token = _hosted_token(monkeypatch)
    assert client(cookies={"__Host-at_session": token}).get("/", headers=JSON).status_code == 200
    assert client(cookies={"at_session": token}).get("/", headers=JSON).status_code == 401


def test_au3_plain_http_dev_still_uses_the_plain_cookie(root: Path) -> None:
    account(ADMIN)
    token = login(ADMIN).cookies["at_session"]
    assert client(cookies={"at_session": token}).get("/", headers=JSON).status_code == 200


# -- F3 / AU16: user-controlled names are escaped wherever they render --------------------

HOSTILE = "</title><script>alert(1)</script>"


def test_au16_group_name_is_escaped_in_every_admin_page(root: Path) -> None:
    """A groups.manage holder names a group `</title><script>`; an Admin opens it."""
    account(ADMIN)
    admin = login(ADMIN)
    made = admin.post("/admin/groups", data={"name": HOSTILE, "permission": "project.view@all"})
    assert made.status_code == 303
    page = made.headers["location"]
    pages = [admin.get(page), admin.get("/admin/groups"), admin.get("/admin/users"),
             admin.post(page, data={"name": HOSTILE, "permission": "bogus"}),  # 400 page
             admin.post(page + "/delete", data={})]  # the confirm page
    for resp in pages:
        assert "<script>alert(1)" not in resp.text, resp.request.url
        assert "&lt;script&gt;" in resp.text or "&lt;/title&gt;" in resp.text


def test_au16_display_name_and_project_name_are_escaped(root: Path) -> None:
    account(ADMIN)
    admin = login(ADMIN)
    uid = user_id(ADMIN)
    admin.post(f"/admin/users/{uid}/name", data={"display_name": "<img src=x onerror=1>"})
    project(root, "pwn")
    ProjectStore("pwn", root).save_project(Project(
        slug="pwn", name="<b onmouseover=1>", base_url="https://pwn.test",
        allowed_domains=["pwn.test"]))
    for path in ("/", "/admin/users", "/projects/pwn/access"):
        text = admin.get(path).text
        assert "<img src=x" not in text and "<b onmouseover" not in text, path


# -- P8: signed-in pages are not cached ---------------------------------------------------

def test_au25_authenticated_pages_are_no_store(root: Path) -> None:
    account(ADMIN)
    admin = login(ADMIN)
    for path in ("/", "/admin/users"):
        assert admin.get(path).headers["cache-control"] == "no-store", path
    assert admin.post("/auth/logout").headers["cache-control"] == "no-store"


# -- P9 / AU5: signup is limited, the limiter is bounded, the dummy hash is precomputed ----

def test_au5_signup_is_rate_limited_per_address(root: Path) -> None:
    """A bot posting sign-ups: each costs a 64 MiB hash, so the 11th from one address is 429."""
    codes = [client().post("/auth/signup", data={"email": f"bot{i}@team.test",
                                                 "password": PASSWORD}).status_code
             for i in range(ratelimit.MAX_SIGNUPS_PER_ADDRESS + 1)]
    assert codes[:-1] == [303] * ratelimit.MAX_SIGNUPS_PER_ADDRESS and codes[-1] == 429
    signup_limiter.reset()


def test_au5_limiter_table_is_bounded_and_forgets_expired_keys(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown-email login floods: 20,000 unique emails must not leave 20,000 entries."""
    monkeypatch.setattr(ratelimit, "MAX_TRACKED_KEYS", 50)
    now = [0.0]
    limiter = LoginRateLimiter(clock=lambda: now[0])
    for i in range(500):
        limiter.record_failure(f"u{i}@x.test", f"10.0.{i // 250}.{i % 250}")
    assert len(limiter._failures) <= 50
    now[0] = ratelimit.WINDOW_SECONDS + 1
    limiter.record_failure("late@x.test", "10.9.9.9")
    assert len(limiter._failures) == 2  # the expired ones were dropped, not kept empty
    assert not limiter.blocked("u1@x.test", "10.0.0.1") and len(limiter._failures) == 2


def test_au2_the_dummy_hash_exists_before_any_login(monkeypatch: pytest.MonkeyPatch) -> None:
    assert passwords._DUMMY_HASH.startswith("$argon2id$")
    real = passwords._HASHER

    class _NoHash:
        def __getattr__(self, name: str):
            raise AssertionError("hashing the dummy lazily on the first unknown login")

        def verify(self, stored: str, password: str) -> bool:
            return real.verify(stored, password)

    monkeypatch.setattr(passwords, "_HASHER", _NoHash())
    assert passwords.verify_password(None, "whatever-password") is False


def test_au2_an_unknown_email_still_pays_one_verification(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Timing: the unknown-email login must verify against the dummy hash, exactly once."""
    account(ADMIN)
    calls: list[str] = []
    real = passwords._HASHER

    class _Counting:
        def verify(self, stored: str, password: str) -> bool:
            calls.append(stored)
            return real.verify(stored, password)

        def __getattr__(self, name: str):
            return getattr(real, name)

    monkeypatch.setattr(passwords, "_HASHER", _Counting())
    assert client().post("/auth/login", data={"email": "nobody@team.test",
                                              "password": "irrelevant-pass"}).status_code == 401
    assert calls == [passwords._DUMMY_HASH]

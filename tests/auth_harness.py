"""Shared setup for the T-204 auth tests (qa/contracts/auth.md): the login gate ON, a
scratch data root, no suite auto-login, and helpers that create accounts in a given
default group and sign them in through the real login route.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.auth import accounts, groups
from autotester.auth.ratelimit import login_limiter, signup_limiter
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

PASSWORD = "correct-horse-battery"
ADMIN = "admin@team.test"
_CLEARED = ("AUTOTESTER_AUTH_DIR", "AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED",
            "AUTOTESTER_FIRST_ADMIN_EMAIL", "AUTOTESTER_COOKIE_SECURE",
            "AUTOTESTER_ALLOWED_ORIGINS", "AUTOTESTER_SESSION_HOURS", "UVICORN_HOST",
            "AUTOTESTER_PUBLIC_ORIGIN")


def gate_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh data root with the gate ON and the suite admin switched off."""
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.setenv("AUTOTESTER_TEST_NO_AUTO_LOGIN", "1")
    for name in _CLEARED:
        monkeypatch.delenv(name, raising=False)
    # The Host allow-list (AT-758, `ui/helpers.py::_host_allowed`) refuses a Host outside it,
    # and TestClient names its host `testserver`: list it.
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "testserver")
    login_limiter.reset()
    signup_limiter.reset()
    return root


def client(**kwargs: object) -> TestClient:
    return TestClient(app, follow_redirects=False, **kwargs)


def login(email: str, password: str = PASSWORD) -> TestClient:
    c = client()
    resp = c.post("/auth/login", data={"email": email, "password": password})
    assert resp.status_code == 303, resp.text
    return c


def group_id(seed: str) -> int:
    return next(g.id for g in groups.list_groups() if g.seed == seed)


def account(email: str, seed: str | None = None) -> int:
    """Create an account (the first one ever becomes admin) and put it in `seed`."""
    user = accounts.signup(email, PASSWORD)
    if seed is not None:
        accounts.set_user_groups(user.id, [group_id(seed)])
    return user.id


def team() -> dict[str, TestClient]:
    """Admin plus one signed-in account per other default group."""
    account(ADMIN)
    roles = {"sub": "sub-admin", "dev": "developer", "tester": "tester"}
    for name, seed in roles.items():
        account(f"{name}@team.test", seed)
    return {name: login(f"{name}@team.test") for name in ("admin", *roles)}


def project(root: Path, slug: str) -> None:
    ProjectStore(slug, root).save_project(Project(
        slug=slug, name=slug.title(), base_url=f"https://{slug}.test",
        allowed_domains=[f"{slug}.test"]))


def app_routes() -> list[tuple[str, str]]:
    """Every (method, path template) the app serves, through included routers too."""
    out: list[tuple[str, str]] = []
    pending = list(app.routes)
    while pending:
        route = pending.pop()
        inner = getattr(route, "original_router", None)
        if inner is not None:
            pending.extend(inner.routes)
            continue
        out += [(m, route.path) for m in sorted(getattr(route, "methods", None) or ())
                if m != "HEAD"]
    return sorted(set(out))


def user_id(email: str) -> int:
    found = accounts.find_user(email)
    assert found is not None
    return found.id

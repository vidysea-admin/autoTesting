"""T-204 sign-in: hashing, identical failures, cookies and sessions, logout and the
rate limit (qa/contracts/auth.md AU1-AU5), with the login gate ON."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login

from autotester.auth import accounts
from autotester.auth.db import auth_db_path
from autotester.auth.ratelimit import (
    MAX_FAILURES_PER_ACCOUNT,
    WINDOW_SECONDS,
    LoginRateLimiter,
    login_limiter,
)
from autotester.auth.sessions import session_hours

JSON = {"accept": "application/json"}


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _db() -> sqlite3.Connection:
    return sqlite3.connect(auth_db_path())


def test_au1_password_is_argon2id_and_never_stored(root: Path,
                                                   caplog: pytest.LogCaptureFixture) -> None:
    canary = "Canary-Pw-7f3e91ab"
    caplog.set_level(logging.DEBUG)
    resp = client().post("/auth/signup", data={"email": ADMIN, "password": canary})
    assert resp.status_code == 303
    login(ADMIN, canary)
    stored = _db().execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored.startswith("$argon2id$")
    params = dict(p.split("=") for p in re.search(r"\$(m=[^$]+)\$", stored)[1].split(","))
    assert int(params["m"]) >= 19 * 1024 and int(params["t"]) >= 2
    for path in [*root.rglob("*"), *auth_db_path().parent.rglob("*")]:
        if path.is_file():
            assert canary.encode() not in path.read_bytes(), path
    assert canary not in caplog.text


def test_au2_failures_are_identical(root: Path) -> None:
    account(ADMIN)
    gone = account("gone@team.test", "tester")
    accounts.set_disabled(gone, True)
    tries = [(ADMIN, "wrong-password-123"), ("nobody@team.test", PASSWORD),
             ("gone@team.test", PASSWORD)]
    answers = [client().post("/auth/login", data={"email": e, "password": p})
               for e, p in tries]
    assert {a.status_code for a in answers} == {401}
    assert len({a.content for a in answers}) == 1


@pytest.mark.parametrize(("given", "lands"), [
    ("/projects/x", "/projects/x"), ("https://evil.example/", "/"),
    ("//evil.example", "/"), ("javascript:alert(1)", "/")])
def test_au2_success_redirects_to_a_same_site_next(root: Path, given: str, lands: str) -> None:
    account(ADMIN)
    resp = client().post("/auth/login",
                         data={"email": ADMIN, "password": PASSWORD, "next": given})
    assert resp.status_code == 303 and resp.headers["location"] == lands


def _cookie_header(**kwargs: object) -> str:
    resp = client(**kwargs).post("/auth/login", data={"email": ADMIN, "password": PASSWORD})
    assert resp.status_code == 303
    return resp.headers["set-cookie"]


def test_au3_cookie_flags_plain_http(root: Path) -> None:
    account(ADMIN)
    header = _cookie_header().lower()
    assert header.startswith("at_session=")
    assert "httponly" in header and "samesite=lax" in header and "path=/" in header
    assert "domain=" not in header and "secure" not in header


def test_au3_cookie_secure_over_https_and_hosted(root: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)
    header = _cookie_header(base_url="https://testserver").lower()
    assert header.startswith("__host-at_session=") and "secure" in header
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    assert "secure" in _cookie_header().lower()
    monkeypatch.setenv("AUTOTESTER_COOKIE_SECURE", "0")
    assert "secure" not in _cookie_header().lower()


def test_au3_new_session_id_every_login(root: Path) -> None:
    account(ADMIN)
    first = login(ADMIN).cookies.get("at_session")
    second = login(ADMIN).cookies.get("at_session")
    assert first and second and first != second and len(first) >= 22


def _expire_all() -> None:
    with _db() as conn:
        conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")


@pytest.mark.parametrize("damage", ["tampered", "truncated", "unknown", "expired"])
def test_au3_bad_cookie_is_refused_and_creates_nothing(root: Path, damage: str) -> None:
    account(ADMIN)
    good = login(ADMIN).cookies["at_session"]
    value = {"tampered": good[:-1] + ("A" if good[-1] != "A" else "B"),
             "truncated": good[:10], "unknown": "x" * 43, "expired": good}[damage]
    if damage == "expired":
        _expire_all()
    before = _db().execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    c = client(cookies={"at_session": value})
    assert c.get("/", headers=JSON).status_code == 401
    assert c.get("/", headers={"accept": "text/html"}).status_code == 302
    # a refused cookie creates nothing; the purge of an expired row may shrink the table
    assert _db().execute("SELECT COUNT(*) FROM sessions").fetchone()[0] <= before


def test_au3_disable_takes_effect_on_the_next_request(root: Path) -> None:
    account(ADMIN)
    tester = account("t@team.test", "tester")
    c = login("t@team.test")
    assert c.get("/", headers=JSON).status_code == 200
    accounts.set_disabled(tester, True)
    assert c.get("/", headers=JSON).status_code == 401


def test_au3_session_lookup_itself_refuses_a_disabled_account(root: Path) -> None:
    """The store flag alone (sessions left in place) still ends access: the lookup
    joins on an enabled account, not only the disable action's session purge."""
    account(ADMIN)
    account("t@team.test", "tester")
    c = login("t@team.test")
    with _db() as conn:
        conn.execute("UPDATE users SET disabled = 1 WHERE email = 't@team.test'")
    assert c.get("/", headers=JSON).status_code == 401


def test_au3_lifetime_is_bounded(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    assert session_hours() == 12
    monkeypatch.setenv("AUTOTESTER_SESSION_HOURS", "100000")
    assert session_hours() <= 168
    monkeypatch.setenv("AUTOTESTER_SESSION_HOURS", "0")
    assert session_hours() >= 1


def test_au4_logout_ends_the_session(root: Path) -> None:
    account(ADMIN)
    c = login(ADMIN)
    old = c.cookies["at_session"]
    assert c.get("/auth/logout").status_code in {403, 404, 405}  # GET changes nothing
    assert c.get("/", headers=JSON).status_code == 200
    resp = c.post("/auth/logout")
    assert resp.status_code == 303 and "at_session=" in resp.headers["set-cookie"]
    assert client(cookies={"at_session": old}).get("/", headers=JSON).status_code == 401


def test_au4_logout_is_origin_guarded(root: Path) -> None:
    account(ADMIN)
    c = login(ADMIN)
    assert c.post("/auth/logout", headers={"origin": "https://evil.example"}).status_code == 403
    assert c.get("/", headers=JSON).status_code == 200


def test_au5_lock_after_failures_even_with_the_right_password(root: Path) -> None:
    account(ADMIN)
    for _ in range(MAX_FAILURES_PER_ACCOUNT + 1):
        client().post("/auth/login", data={"email": ADMIN, "password": "wrong-password-1"})
    locked = client().post("/auth/login", data={"email": ADMIN, "password": PASSWORD})
    assert locked.status_code == 429
    assert "exist" not in locked.text.lower()
    login_limiter.reset()
    assert client().post("/auth/login",
                         data={"email": ADMIN, "password": PASSWORD}).status_code == 303


def test_au5_the_window_passes() -> None:
    now = [0.0]
    limiter = LoginRateLimiter(clock=lambda: now[0])
    for _ in range(MAX_FAILURES_PER_ACCOUNT):
        limiter.record_failure("a@x.test", "1.2.3.4")
    assert limiter.blocked("a@x.test", "5.6.7.8")
    assert not limiter.blocked("b@x.test", "5.6.7.8")
    now[0] += WINDOW_SECONDS
    assert not limiter.blocked("a@x.test", "5.6.7.8")


def test_au5_per_address_limit() -> None:
    limiter = LoginRateLimiter(clock=lambda: 0.0)
    for i in range(20):
        limiter.record_failure(f"u{i}@x.test", "9.9.9.9")
    assert limiter.blocked("fresh@x.test", "9.9.9.9")

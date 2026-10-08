"""T-204 fix cycle 1: tests that kill the surviving mutants x1, x2 and E22 (checker A/B
cycle 0) and pin the suite's auto-login away from the real repository's audit file (P7).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from auth_harness import ADMIN, account, client, gate_on, login, user_id
from fastapi.testclient import TestClient

from autotester.auth import ratelimit
from autotester.auth.db import auth_db_path
from autotester.ui.app import app

JSON = {"accept": "application/json"}


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


# -- P11: survivors x1, x2, E22 -----------------------------------------------------------

def test_au3_the_stored_token_hash_is_not_a_cookie(root: Path) -> None:
    """x1: if the store leaks (a backup, a SQL injection), the digest must not log anyone in."""
    account(ADMIN)
    login(ADMIN)
    digest = sqlite3.connect(auth_db_path()).execute(
        "SELECT token_hash FROM sessions").fetchone()[0]
    assert client(cookies={"at_session": digest}).get("/", headers=JSON).status_code == 401


def test_au5_the_address_limit_ignores_x_forwarded_for(root: Path) -> None:
    """x2: one client rotating a spoofed X-Forwarded-For (and a new email each time to dodge
    the per-account limit) is still one address: the 21st attempt is 429."""
    codes = [client().post("/auth/login", headers={"x-forwarded-for": f"9.9.9.{i}"},
                           data={"email": f"n{i}@team.test", "password": "wrong-pass-12"}
                           ).status_code
             for i in range(ratelimit.MAX_FAILURES_PER_ADDRESS + 1)]
    assert codes[:-1] == [401] * ratelimit.MAX_FAILURES_PER_ADDRESS and codes[-1] == 429


def test_au22_audit_line_holds_the_template_not_the_query_string(root: Path) -> None:
    """E22: a state-changing request with `?token=...` leaves no query text in the audit."""
    account(ADMIN)
    admin = login(ADMIN)
    uid = user_id(ADMIN)
    admin.post(f"/admin/users/{uid}/name?token=Query-Canary-77", data={"display_name": "A"})
    audit = (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")
    assert "Query-Canary-77" not in audit and "/admin/users/{user_id}/{action}" in audit


# -- P7: the suite's auto-login never writes the real repository's audit file -------------

def test_suite_auto_login_leaves_the_real_audit_file_alone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    import autotester.core.paths as paths

    monkeypatch.delenv("AUTOTESTER_ROOT", raising=False)
    monkeypatch.delenv("AUTOTESTER_AUTH_DIR", raising=False)
    monkeypatch.delenv("AUTOTESTER_TEST_NO_AUTO_LOGIN", raising=False)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "testserver")  # at758 allow-list or not
    real = Path(paths.__file__).resolve().parents[3] / ".work" / "audit.jsonl"
    before = real.stat().st_size if real.exists() else 0
    resp = TestClient(app, follow_redirects=False).post("/admin/users/999999/name",
                                                        data={"display_name": "x"})
    assert resp.status_code == 404
    assert (real.stat().st_size if real.exists() else 0) == before

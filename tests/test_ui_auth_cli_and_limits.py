"""T-204 fix cycle 1, late blind sub-check: unbounded limiter growth on blocked() (AU5), a
length cap on `next` (AU16), an audit row and a non-TTY refusal for the break-glass CLI
(AU22, AU8), and purging the expired session row a refused cookie names (AU3).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on
from typer.testing import CliRunner

from autotester.auth import accounts, sessions
from autotester.auth.db import auth_db_path
from autotester.auth.ratelimit import LoginRateLimiter
from autotester.cli import app as cli_app
from autotester.ui.auth_middleware import MAX_NEXT_LENGTH, safe_next


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _audit(root: Path) -> list[dict]:
    path = root / ".work" / "audit.jsonl"
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]


def test_au5_checking_a_limit_never_creates_an_entry() -> None:
    """20,000 unauthenticated unknown emails: blocked() alone must not grow the table."""
    limiter = LoginRateLimiter(clock=lambda: 0.0)
    for i in range(20_000):
        assert not limiter.blocked(f"u{i}@x.test", "10.0.0.1")
    assert len(limiter._failures) == 0


def test_au16_next_is_capped_and_falls_back_to_the_root(root: Path) -> None:
    assert safe_next("/" + "a" * (MAX_NEXT_LENGTH - 1)) != "/"
    assert safe_next("/" + "a" * MAX_NEXT_LENGTH) == "/"
    account(ADMIN)
    resp = client().post("/auth/login", data={"email": ADMIN, "password": PASSWORD,
                                              "next": "/" + "a" * 100_000})
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    page = client().get("/auth/login?next=/" + "b" * 5_000).text
    assert "b" * 100 not in page  # an over-long next is dropped, not echoed back


def test_au22_bootstrap_admin_leaves_an_audit_row_without_the_password(root: Path) -> None:
    runner = CliRunner()
    secret = "Canary-Pass-91827"
    args = ["auth", "bootstrap-admin", "--email", "ops@team.test", "--password-stdin"]
    assert runner.invoke(cli_app, args, input=secret + "\n").exit_code == 0
    assert runner.invoke(cli_app, args, input=secret + "\n").exit_code == 0
    account("plain@team.test")
    plain = ["auth", "bootstrap-admin", "--email", "plain@team.test", "--password-stdin"]
    assert runner.invoke(cli_app, plain, input=secret + "\n").exit_code == 0
    rows = [r for r in _audit(root) if r.get("actor") == "cli"]
    assert [(r["target"], r["action"]) for r in rows] == [
        ("ops@team.test", "admin.create"), ("ops@team.test", "admin.reset"),
        ("plain@team.test", "admin.promote")]
    assert secret not in (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")


def test_au1_bootstrap_without_a_tty_or_password_stdin_is_refused_not_hung(root: Path) -> None:
    made = CliRunner().invoke(cli_app, ["auth", "bootstrap-admin", "--email", "ops@team.test"])
    assert made.exit_code == 2 and "--password-stdin" in made.output
    assert accounts.find_user("ops@team.test") is None


def test_au3_a_refused_expired_cookie_purges_its_session_row(root: Path) -> None:
    account(ADMIN)
    token = sessions.create_session(accounts.find_user(ADMIN).id)
    with sqlite3.connect(auth_db_path()) as conn:
        conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
    assert sessions.resolve_session(token) is None
    assert sqlite3.connect(auth_db_path()).execute(
        "SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_au3_unknown_cookies_cause_no_writes(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    account(ADMIN)
    writes: list[str] = []
    monkeypatch.setattr(sessions, "_drop_expired", lambda digest, now: writes.append(digest))
    for i in range(20):
        assert sessions.resolve_session(f"unknown-{i}") is None
    assert writes == []

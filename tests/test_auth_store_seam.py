"""The auth store seam (mongo-store U6a, M29/M30): the SQLite store sits behind the
`AuthStore` Protocol, the business modules hold no SQL, first-admin and last-admin still
hold under threads, and no password hash escapes a list, a model or an error."""

from __future__ import annotations

import ast
import hashlib
import inspect
import sqlite3
import threading
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, gate_on

from autotester.auth import accounts, db, groups, sessions
from autotester.auth import store as store_mod
from autotester.auth.db import LastAdmin
from autotester.auth.store_sqlite import SqliteAuthStore, SqliteAuthTx
from autotester.schema.auth import Group, User

BUSINESS = ("accounts", "groups", "sessions", "access")
LOGIN_ONLY = {"login_record", "insert_user", "set_password_hash", "enable_with_password_hash"}


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return gate_on(tmp_path, monkeypatch)


def _protocol_methods(proto: type) -> dict[str, object]:
    return {n: v for n, v in vars(proto).items() if not n.startswith("_") and callable(v)}


@pytest.mark.parametrize(("proto", "impl"), [(store_mod.AuthTx, SqliteAuthTx),
                                             (store_mod.AuthStore, SqliteAuthStore)])
def test_sqlite_store_implements_every_protocol_method(proto: type, impl: type) -> None:
    wanted = _protocol_methods(proto)
    assert len(wanted) >= 3
    for name, declared in wanted.items():
        actual = getattr(impl, name, None)
        assert actual is not None, f"{impl.__name__} lacks {name}"
        want = list(inspect.signature(declared).parameters)
        got = list(inspect.signature(actual).parameters)
        assert got == want, (name, got, want)


def test_business_modules_hold_no_sql() -> None:
    base = Path(store_mod.__file__).parent
    for name in BUSINESS:
        tree = ast.parse((base / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name != "sqlite3" for a in node.names), name
            if isinstance(node, ast.ImportFrom):
                assert node.module != "sqlite3", name
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"execute", "executemany", "executescript"}, name
                assert not (isinstance(node.value, ast.Name) and node.value.id == "db"
                            and node.attr in {"transaction", "reading", "connect"}), name


def test_factory_returns_the_sqlite_store() -> None:
    assert isinstance(store_mod.auth_store(), SqliteAuthStore)


def test_reading_a_missing_store_creates_nothing(root: Path) -> None:
    assert sessions.resolve_session("a" * 40) is None
    sessions.end_session("a" * 40)
    assert not db.store_exists() and not db.auth_db_path().exists()


def test_seam_round_trip_users_groups_sessions(root: Path) -> None:
    admin = accounts.signup(ADMIN, PASSWORD)
    other = accounts.signup("dev@team.test", PASSWORD)
    assert admin.groups == ["Admin/CEO"] and other.groups == []
    seed_ids = {g.seed: g.id for g in groups.list_groups()}
    accounts.set_user_groups(other.id, [seed_ids["developer"]])
    token = sessions.create_session(other.id)
    with sqlite3.connect(db.auth_db_path()) as raw:  # only the sha256 of the token is stored
        digests = [d for (d,) in raw.execute("SELECT token_hash FROM sessions")]
    assert digests == [hashlib.sha256(token.encode()).hexdigest()] and token not in digests
    principal = sessions.resolve_session(token)
    assert principal is not None and principal.email == "dev@team.test"
    assert "project.create" in principal.permissions
    accounts.set_disabled(other.id, True)
    assert sessions.resolve_session(token) is None
    assert accounts.authenticate("dev@team.test", PASSWORD) is None
    assert accounts.authenticate(ADMIN, PASSWORD).id == admin.id
    sessions.end_session(token)


def test_password_hash_never_leaves_the_store(root: Path) -> None:
    assert "password_hash" not in User.model_fields and "password_hash" not in Group.model_fields
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup("dev@team.test", PASSWORD)
    with sqlite3.connect(db.auth_db_path()) as raw:
        stored = raw.execute("SELECT password_hash FROM users").fetchall()
        assert stored and all(h.startswith("$argon2") for (h,) in stored)
        for table in ("meta", "groups", "group_permissions", "memberships", "sessions",
                      "project_grants"):
            dump = repr(raw.execute(f"SELECT * FROM {table}").fetchall())
            assert "$argon2" not in dump, table
    surfaces = [repr(accounts.list_users()), repr(accounts.get_user(user.id)),
                repr(accounts.find_user("dev@team.test")), repr(groups.list_groups()),
                repr(sessions.resolve_session(sessions.create_session(user.id))),
                repr(accounts.user_managers()), repr(accounts.list_waiting())]
    with pytest.raises(accounts.AccountError) as dup:
        accounts.signup("dev@team.test", PASSWORD)
    surfaces.append(str(dup.value))
    for text in surfaces:
        assert "argon2" not in text and "password_hash" not in text


def test_only_login_paths_of_the_protocol_mention_a_hash() -> None:
    for name, fn in _protocol_methods(store_mod.AuthTx).items():
        mentions = "hash" in name or "hash" in str(inspect.signature(fn).return_annotation)
        digest_only = name in {"insert_session", "delete_session", "has_session",
                               "delete_session_if_expired", "live_principal"}
        if mentions and not digest_only:
            assert name in LOGIN_ONLY | {"login_record"}, name


def _fresh_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tag: str) -> None:
    monkeypatch.setenv("AUTOTESTER_AUTH_DIR", str(tmp_path / f"auth-{tag}"))


def _race(jobs: list) -> list:
    barrier = threading.Barrier(len(jobs))
    out: list = [None] * len(jobs)

    def go(i: int, job) -> None:
        barrier.wait()
        try:
            out[i] = ("ok", job())
        except Exception as exc:
            out[i] = ("err", exc)

    threads = [threading.Thread(target=go, args=(i, j)) for i, j in enumerate(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


def test_m29_concurrent_first_signups_yield_exactly_one_admin(
        root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rep in range(5):
        _fresh_store(tmp_path, monkeypatch, f"signup{rep}")
        made = _race([lambda i=i: accounts.signup(f"u{i}@team.test", PASSWORD)
                      for i in range(6)])
        assert all(kind == "ok" for kind, _ in made), made
        admins = [u for _, u in made if "Admin/CEO" in u.groups]
        assert len(admins) == 1, (rep, [u.email for u in admins])


def test_m29_concurrent_claims_yield_exactly_one_admin(
        root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rep in range(5):
        _fresh_store(tmp_path, monkeypatch, f"claim{rep}")
        users = [accounts.signup(f"c{i}@team.test", PASSWORD, secure_cookie=True)
                 for i in range(4)]
        assert all(not u.groups for u in users)
        outcome = _race([lambda u=u: accounts.claim_admin(u.id) for u in users])
        assert sum(kind == "ok" for kind, _ in outcome) == 1, outcome
        assert all(isinstance(v, accounts.AccountError) for kind, v in outcome if kind == "err")
        admin = next(g for g in groups.list_groups() if g.seed == "admin")
        assert len(admin.member_ids) == 1


def test_m29_disabling_the_last_two_admins_leaves_one_enabled(
        root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rep in range(15):
        _fresh_store(tmp_path, monkeypatch, f"last{rep}")
        a, _ = accounts.bootstrap_admin("a@team.test", PASSWORD)
        b, _ = accounts.bootstrap_admin("b@team.test", PASSWORD)
        outcome = _race([lambda uid=a.id: accounts.set_disabled(uid, True),
                         lambda uid=b.id: accounts.set_disabled(uid, True)])
        enabled = [u for u in accounts.list_users() if not u.disabled]
        assert len(enabled) >= 1, (rep, outcome)
        assert any(isinstance(v, LastAdmin) for kind, v in outcome if kind == "err")


def test_last_admin_guard_survives_delete_and_regroup(root: Path) -> None:
    only, _ = accounts.bootstrap_admin(ADMIN, PASSWORD)
    with pytest.raises(LastAdmin):
        accounts.delete_user(only.id)
    with pytest.raises(LastAdmin):
        accounts.set_user_groups(only.id, [])
    admin_group = next(g for g in groups.list_groups() if g.seed == "admin")
    with pytest.raises(LastAdmin):
        groups.delete_group(admin_group.id)
    assert accounts.get_user(only.id) is not None


def test_a_disabled_account_or_expired_session_never_resolves(root: Path) -> None:
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup("dev@team.test", PASSWORD)
    live, stale = sessions.create_session(user.id), sessions.create_session(user.id)
    assert sessions.resolve_session(live) is not None
    with sqlite3.connect(db.auth_db_path()) as raw:  # an expiry no code path sets here
        raw.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00' "
                    "WHERE token_hash = ?", (hashlib.sha256(stale.encode()).hexdigest(),))
    assert sessions.resolve_session(stale) is None
    with sqlite3.connect(db.auth_db_path()) as raw:
        left = raw.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        raw.execute("UPDATE users SET disabled = 1 WHERE id = ?", (user.id,))  # session kept
    assert left == 1  # the refused expired id was dropped, the live one stays
    assert sessions.resolve_session(live) is None

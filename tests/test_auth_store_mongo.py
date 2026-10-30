"""The Mongo auth store alone (mongo-store U6b, M2/M5/M9/M29/M30): what the shared contract suite
(`tests/test_auth_store_contract.py`) cannot say because it is true of Mongo only: the write fence,
selection, the lease and the undo log, id allocation, fail-closed behaviour, and containment of
hashes, tokens and the URI.
"""

from __future__ import annotations

import ast
import inspect
import logging
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD
from auth_store_backends import DATABASE, AuthEnv, auth_env
from fake_mongo import CANARY, assert_no_canary

from autotester.auth import accounts, groups, sessions
from autotester.auth import store as store_mod
from autotester.auth import store_mongo as sm
from autotester.auth import store_mongo_tx as tx_mod
from autotester.auth.store import auth_store
from autotester.auth.store_sqlite import SqliteAuthStore
from autotester.store.mongo_backend import reset_default_backend
from autotester.store.mongo_guard import StoreDuplicateKey, StoreUnavailable
from autotester.store.mongo_routes import StoreSelectionError

OTHER = "dev@team.test"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


def _methods(proto: type) -> dict[str, object]:
    return {n: v for n, v in vars(proto).items() if not n.startswith("_") and callable(v)}


@pytest.mark.parametrize(("proto", "impl"), [(store_mod.AuthTx, sm.MongoAuthTx),
                                             (store_mod.AuthStore, sm.MongoAuthStore)])
def test_mongo_store_implements_every_protocol_method(proto: type, impl: type) -> None:
    wanted = _methods(proto)
    assert len(wanted) >= 3
    for name, declared in wanted.items():
        actual = getattr(impl, name, None)
        assert actual is not None, f"{impl.__name__} lacks {name}"
        assert list(inspect.signature(actual).parameters) == list(
            inspect.signature(declared).parameters), name


def test_the_module_holds_no_sql_no_driver_and_names_no_database() -> None:
    nodes = [n for m in (sm, tx_mod)
             for n in ast.walk(ast.parse(Path(m.__file__).read_text(encoding="utf-8")))]
    for node in nodes:
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert not any(n.split(".")[0] in {"sqlite3", "pymongo", "gridfs"} for n in names)
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args + node.args.kwonlyargs]
            assert not {"db", "database", "db_name"} & set(args), node.name  # M2
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"MongoClient", "get_database", "list_database_names",
                                     "execute", "aggregate", "command"}


def test_every_write_lands_in_the_configured_database_only(env: AuthEnv) -> None:
    env.server.seed_foreign("scratch")
    env.server.seed_foreign("admin", "system.users")
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    accounts.set_user_groups(user.id, [groups.list_groups()[2].id])
    sessions.end_session(sessions.create_session(user.id))
    accounts.delete_user(user.id)
    assert {database for database, _ in env.server.log} == {DATABASE}
    for name in ("scratch", "admin"):
        assert [d["_id"] for c in env.server.databases[name].collections.values()
                for d in c.docs] == ["foreign"]
    kinds = {n for n, c in env.server.database(DATABASE).collections.items() if c.docs}
    assert kinds <= {"auth_users", "auth_groups", "auth_sessions", "auth_grants", "auth_meta",
                     "server_state"}


def test_argon2_strings_live_only_in_auth_users(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    accounts.signup(OTHER, PASSWORD)
    sessions.create_session(accounts.find_user(OTHER).id)
    holders = {n for n, c in env.server.database(DATABASE).collections.items()
               if "$argon2" in repr(c.docs)}
    assert holders == {"auth_users"}


def test_nothing_secret_reaches_a_log(env: AuthEnv, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    token = sessions.create_session(user.id)
    assert accounts.authenticate(OTHER, "wrong-password-xyz") is None
    with pytest.raises(accounts.AccountError):
        accounts.signup(OTHER, PASSWORD)
    for secret in ("$argon2", token, PASSWORD, "wrong-password-xyz"):
        assert secret not in caplog.text


# -- selection --------------------------------------------------------------------------
def test_sqlite_is_the_default_and_mongo_only_by_selection(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS", "PATHLYNKS_MONGO_URI"):
        monkeypatch.delenv(name, raising=False)
    assert isinstance(auth_store(), SqliteAuthStore)
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "settings=mongo")
    assert isinstance(auth_store(), SqliteAuthStore)  # another area on mongo leaves auth alone
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "auth=file")
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    assert isinstance(auth_store(), SqliteAuthStore)  # an explicit area wins over the default


def test_auth_on_mongo_needs_the_uri_named_without_a_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "auth=mongo")
    monkeypatch.delenv("PATHLYNKS_MONGO_URI", raising=False)
    reset_default_backend()  # the auth store follows the process's one client
    with pytest.raises(StoreSelectionError, match="PATHLYNKS_MONGO_URI is not set"):
        auth_store()


def test_a_mongo_selection_yields_the_mongo_store(env: AuthEnv,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(auth_store(), sm.MongoAuthStore)
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS")
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    assert isinstance(auth_store(), sm.MongoAuthStore)


def test_a_file_mode_process_never_imports_the_driver(tmp_path: Path) -> None:
    code = ("import sys; from autotester.auth import accounts, groups, sessions, access; "
            "from autotester.auth.store import auth_store; "
            "assert type(auth_store()).__name__ == 'SqliteAuthStore'; "
            "assert 'pymongo' not in sys.modules and 'gridfs' not in sys.modules")
    env = {k: v for k, v in __import__("os").environ.items()
           if not k.startswith("AUTOTESTER_STORE")}
    done = subprocess.run([sys.executable, "-c", code], env=env, cwd=tmp_path,
                          capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr[-800:]


# -- the lease and the undo log -------------------------------------------------------------
def _lock_doc(env: AuthEnv) -> dict | None:
    return next((d for d in env._coll("auth_meta").docs if d["_id"] == tx_mod.LOCK_ID), None)


def test_the_lease_is_released_after_success_and_after_failure(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    assert _lock_doc(env) is None
    with pytest.raises(RuntimeError, match="boom"), auth_store().transaction():
        raise RuntimeError("boom")
    assert _lock_doc(env) is None


def _state(env: AuthEnv) -> dict[str, list]:
    """Every collection but the lease/allocator one, each as documents sorted by `_id` (a
    document store promises no order, so a re-inserted document may land last)."""
    return {n: sorted((dict(d) for d in c.docs), key=lambda d: str(d["_id"]))
            for n, c in env.server.database(DATABASE).collections.items() if n != "auth_meta"}


def test_an_exception_rolls_every_write_back(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    other = accounts.signup(OTHER, PASSWORD)
    token = sessions.create_session(other.id)
    before = _state(env)
    with pytest.raises(RuntimeError, match="boom"), auth_store().transaction() as tx:
        tx.insert_user("ghost@team.test", "h")
        tx.set_disabled(other.id, True)
        tx.delete_user_sessions(other.id)
        tx.insert_group("Ghosts")
        tx.set_user_groups(other.id, {1, 2})
        tx.delete_group(3)
        tx.replace_project_owner("p", other.id)
        raise RuntimeError("boom")
    after = _state(env)
    assert after == before
    assert sessions.resolve_session(token) is not None


def test_an_expired_lease_is_taken_over_by_compare_and_set(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    env._coll("auth_meta").docs.append({"_id": tx_mod.LOCK_ID, "owner": "dead", "expires": 1.0})
    accounts.signup(OTHER, PASSWORD)
    assert accounts.find_user(OTHER) is not None and _lock_doc(env) is None


def test_a_live_lease_held_elsewhere_refuses_with_no_write(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    accounts.signup(ADMIN, PASSWORD)
    monkeypatch.setattr(tx_mod, "WAIT_SECONDS", 0.1)
    env._coll("auth_meta").docs.append({"_id": tx_mod.LOCK_ID, "owner": "busy", "expires": 9e12})
    with pytest.raises(sm.AuthStoreBusy, match="busy; try again"):
        accounts.signup(OTHER, PASSWORD)
    assert _lock_doc(env)["owner"] == "busy"  # never released by a stranger
    assert accounts.find_user(OTHER) is None


def test_a_lease_lost_mid_transaction_rolls_the_transaction_back(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    with pytest.raises(sm.AuthStoreBusy, match="expired mid-transaction"), \
            auth_store().transaction() as tx:
        tx.insert_user("late@team.test", "h")
        _lock_doc(env)["owner"] = "someone-else"  # the lease expired and another writer took it
    assert accounts.find_user("late@team.test") is None


def test_a_reader_cannot_write(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    with auth_store().reading() as tx:
        with pytest.raises(RuntimeError, match="opened for reading"):
            tx.set_disabled(1, True)
        with pytest.raises(RuntimeError, match="opened for reading"):
            tx.purge_sessions_before("2999-01-01")


def test_unique_indexes_are_the_second_line(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    with pytest.raises(StoreDuplicateKey), auth_store().transaction() as tx:
        tx.insert_user(ADMIN, "h")
    with pytest.raises(StoreDuplicateKey), auth_store().transaction() as tx:
        tx.insert_group("Admin/CEO")
    with pytest.raises(StoreDuplicateKey), auth_store().transaction() as tx:
        tx.add_membership(accounts.find_user(ADMIN).id, tx.admin_group_id())


def test_a_second_pass_creates_the_same_indexes_and_a_crashed_seed_resumes(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    first = {n: dict(c.indexes) for n, c in env.server.database(DATABASE).collections.items()}
    sm.reset_auth_store()
    groups.list_groups()
    again = {n: dict(c.indexes) for n, c in env.server.database(DATABASE).collections.items()}
    assert first == again
    env.fresh()  # an interrupted seed: one default group exists, the marker does not
    env._coll("server_state").docs.append(
        {"_id": "marker", "database": DATABASE, "created_at": "x", "schema_version": 1})
    env._coll("auth_groups").docs.append(
        {"_id": 1, "name": "Admin/CEO", "seed": "admin", "permissions": ["users.manage"]})
    seeds = sorted(g.seed for g in groups.list_groups())
    assert seeds == ["admin", "developer", "sub-admin", "tester"]


# -- ids ----------------------------------------------------------------------------------------
def test_ids_are_never_reused_after_a_delete(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    last = accounts.signup(OTHER, PASSWORD)
    accounts.delete_user(last.id)
    assert accounts.signup(OTHER, PASSWORD).id > last.id
    made = groups.create_group("Temp", [])
    groups.delete_group(made.id)
    assert groups.create_group("Temp", []).id > made.id


def test_concurrent_allocation_hands_out_distinct_ids(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    ids: list[int] = []

    def take() -> None:
        with auth_store().transaction() as tx:
            ids.append(tx._allocate(sm.USERS))

    threads = [threading.Thread(target=take) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ids) == len(set(ids)) == 8


# -- fail closed --------------------------------------------------------------------------------
def test_an_unreachable_store_denies_and_leaks_nothing(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture) -> None:
    accounts.signup(ADMIN, PASSWORD)
    token = sessions.create_session(accounts.find_user(ADMIN).id)
    env.server.down = True
    failures: list[BaseException] = []
    for call in (lambda: sessions.resolve_session(token),
                 lambda: accounts.authenticate(ADMIN, PASSWORD),
                 lambda: accounts.signup(OTHER, PASSWORD),
                 lambda: sessions.create_session(1)):
        with pytest.raises(StoreUnavailable) as caught:
            call()  # an error, never a principal or a user: the caller is denied
        failures.append(caught.value)
    env.server.down = False
    for exc in failures:
        text = str(exc) + repr(exc)
        assert token not in text and "$argon2" not in text and "mongodb://" not in text
        assert_no_canary(exc, capsys, caplog)
    assert sessions.resolve_session(token) is not None and _lock_doc(env) is None
    assert CANARY not in caplog.text

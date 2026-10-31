"""Crash safety of the Mongo auth store (mongo-store U6b, M29, fix cycle 2). The store dies at
EVERY database call of the sole admin's risky operations; the dead holder's lease is then aged
out and another account tries to claim admin. Whatever happened, no refused or half-done change
may survive, an enabled Admin/CEO member must remain and no permission may have been granted.
Also: a stalled holder never undoes a successor's work, a password reset revokes sessions
before it writes the hash, and a global AUTOTESTER_STORE=mongo does not move auth."""

from __future__ import annotations

import contextlib
import itertools
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD
from auth_store_backends import AuthEnv, auth_env

from autotester.auth import accounts, groups, sessions
from autotester.auth import store_mongo_tx as tx_mod
from autotester.auth.passwords import hash_password
from autotester.auth.store import auth_store
from autotester.auth.store_mongo import AuthStoreBusy, MongoAuthStore

OTHER, THIRD, NEW_PASSWORD = "dev@team.test", "third@team.test", "another-long-password-1"
HASH = hash_password(PASSWORD)
Scenario = Callable[[AuthEnv], tuple[Callable[[], object], Callable[[], None]]]


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


def _seed(admin_member: bool = True) -> tuple[int, int, int]:
    """Three enabled accounts: A (sole Admin/CEO member unless told otherwise), B (developer),
    C (no group). Built through the store, so no password is hashed per scenario."""
    developer = next(g.id for g in groups.list_groups() if g.seed == "developer")
    with auth_store().transaction() as tx:
        a, b, c = (tx.insert_user(e, HASH) for e in (ADMIN, OTHER, THIRD))
        if admin_member:
            tx.add_membership(a, tx.admin_group_id())
        tx.add_membership(b, developer)
    return a, b, c


def _shape() -> dict[str, object]:
    """Everything a refused change must leave exactly as it was."""
    return {"users": sorted((u.email, u.disabled, tuple(u.groups)) for u in accounts.list_users()),
            "groups": sorted((g.name, tuple(g.permissions)) for g in groups.list_groups())}


def _admins() -> list[object]:
    return [u for u in accounts.list_users() if "Admin/CEO" in u.groups]


def _kill_at(env: AuthEnv, k: int, op: Callable[[], object]) -> bool:
    """Run `op`; the store dies for good at its k-th database call (the rollback and the lease
    release included, so nothing undoes anything). True if that call was reached."""
    server, real, calls = env.server, env.server.check_up, [0]

    def counted() -> None:
        calls[0] += 1
        server.down = server.down or calls[0] >= k
        real()

    server.check_up = counted  # type: ignore[method-assign]
    try:
        with contextlib.suppress(Exception):
            op()
    finally:
        del server.check_up
        server.down = False
    return calls[0] >= k


def _age_out_lease(env: AuthEnv) -> None:
    for doc in env._coll("auth_meta").docs:
        if doc["_id"] == tx_mod.LOCK_ID:
            doc["expires"] = 1.0


def _sweep(env: AuthEnv, scenario: Scenario, age_out: bool = True) -> int:
    """Run `scenario` with the store dying at call 1, 2, 3 ... until the operation needs no
    more calls; after each death age out the lease (when asked) and run its check."""
    for k in itertools.count(1):
        env.fresh()
        op, check = scenario(env)
        if not _kill_at(env, k, op):
            return k - 1
        if age_out:
            _age_out_lease(env)
        check()
    raise AssertionError("unreachable")


def _refused(build: Callable[[int, int], Callable[[], object]]) -> Scenario:
    """An operation the last-admin guard (or a validity check) refuses: afterwards nothing at all
    differs from before, and a claim by another account is refused."""
    def scenario(env: AuthEnv) -> tuple[Callable[[], object], Callable[[], None]]:
        a, b, c = _seed()
        before = _shape()

        def check() -> None:
            with pytest.raises(accounts.AccountError):
                accounts.claim_admin(c)
            assert _shape() == before
            assert any(not u.disabled for u in _admins())  # type: ignore[attr-defined]
        return build(a, b), check
    return scenario


def _raise_developer(a: int, b: int) -> Callable[[], object]:
    def op() -> object:
        dev = next(g for g in groups.list_groups() if g.seed == "developer")
        return groups.update_group(dev.id, dev.name, [*dev.permissions, "users.manage"],
                                   member_ids=[b, 99999])  # refused: unknown member
    return op


REFUSED = {
    "set_user_groups": lambda a, b: lambda: accounts.set_user_groups(a, []),
    "delete_user": lambda a, b: lambda: accounts.delete_user(a),
    "set_disabled": lambda a, b: lambda: accounts.set_disabled(a, True),
    "update_group": _raise_developer,
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_refused_change_survives_a_kill_at_every_call_point(env: AuthEnv, name: str) -> None:
    assert _sweep(env, _refused(REFUSED[name])) >= 8  # not vacuous: a real number of call points


def _claim_scenario(env: AuthEnv) -> tuple[Callable[[], object], Callable[[], None]]:
    a, _b, c = _seed(admin_member=False)
    before = _shape()["groups"]

    def check() -> None:
        with contextlib.suppress(accounts.AccountError):
            accounts.claim_admin(c)  # refused when the killed claim of A had landed
        assert len(_admins()) == 1 and not _admins()[0].disabled  # type: ignore[attr-defined]
        assert _shape()["groups"] == before  # no permission was handed out on the way
    return lambda: accounts.claim_admin(a), check


def test_a_claim_killed_anywhere_leaves_exactly_one_admin(env: AuthEnv) -> None:
    assert _sweep(env, _claim_scenario) >= 5


def _password_scenario(change: Callable[[], object]) -> Scenario:
    def scenario(env: AuthEnv) -> tuple[Callable[[], object], Callable[[], None]]:
        a, _b, c = _seed()
        token, before = sessions.create_session(a), _shape()

        def check() -> None:
            with pytest.raises(accounts.AccountError):
                accounts.claim_admin(c)
            old, new = accounts.authenticate(ADMIN, PASSWORD), accounts.authenticate(
                ADMIN, NEW_PASSWORD)
            assert (old is None) != (new is None)  # exactly one password works, never both
            assert (sessions.resolve_session(token) is not None) == (old is not None)
            assert _shape() == before and any(not u.disabled for u in _admins())  # type: ignore
        return change, check
    return scenario


def _reset() -> object: return accounts.reset_password(1, NEW_PASSWORD)
def _bootstrap() -> object: return accounts.bootstrap_admin(ADMIN, NEW_PASSWORD)


@pytest.mark.parametrize("change", [_reset, _bootstrap], ids=["reset_password", "bootstrap_admin"])
def test_a_password_change_killed_anywhere_is_whole_or_absent(env: AuthEnv,
                                                              change: Callable[[], object]) -> None:
    assert _sweep(env, _password_scenario(change)) >= 8


@pytest.mark.parametrize("change", [_reset, _bootstrap], ids=["reset_password", "bootstrap_admin"])
def test_sessions_are_revoked_before_the_new_hash_is_written(env: AuthEnv,
                                                             change: Callable[[], object]) -> None:
    def scenario(env: AuthEnv) -> tuple[Callable[[], object], Callable[[], None]]:
        a, _b, _c = _seed()
        sessions.create_session(a)

        def check() -> None:  # no recovery has run: the raw state, right after the death
            user = next(d for d in env._coll("auth_users").docs if d.get("_id") == a)
            live = [d for d in env._coll("auth_sessions").docs if d["user_id"] == a]
            assert user["password_hash"] == HASH or not live, "new hash, old sessions still valid"
        return change, check
    assert _sweep(env, scenario, age_out=False) >= 5


# -- a holder that stalls past its lease (A-W2) -----------------------------------------------
def _journal_left(env: AuthEnv) -> bool:
    return any(d["_id"] == tx_mod.JOURNAL_ID for d in env._coll("auth_meta").docs) or any(
        d.get("kind") == tx_mod.UNDO for d in env._coll("auth_users").docs)


def test_a_stalled_holder_never_undoes_a_successors_commit(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with pytest.raises(AuthStoreBusy, match="expired mid-transaction"), \
            auth_store().transaction() as tx:
        tx.set_display_name(b, "stalled")  # A writes, then stalls past the 30 s lease
        _age_out_lease(env)
        accounts.set_display_name(b, "successor")  # B takes over (A's write is undone), commits
    assert accounts.get_user(b).display_name == "successor" and not _journal_left(env)


def test_a_stalled_holders_rollback_leaves_a_live_successor_alone(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    stalled, live = auth_store().transaction(), auth_store().transaction()
    stalled.__enter__().set_display_name(b, "stalled")
    _age_out_lease(env)
    live.__enter__().set_display_name(b, "live")  # B holds the lease with uncommitted work
    assert stalled.__exit__(RuntimeError, RuntimeError("late failure"), None) is False
    live.__exit__(None, None, None)
    assert accounts.get_user(b).display_name == "live" and not _journal_left(env)


def test_a_stalled_holder_writes_nothing_once_the_lease_is_gone(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with pytest.raises(AuthStoreBusy, match="lease was lost"), auth_store().transaction() as tx:
        _age_out_lease(env)
        accounts.set_display_name(b, "successor")
        tx.set_display_name(b, "zombie")  # refused before it writes
    assert accounts.get_user(b).display_name == "successor"


def test_a_lease_lost_mid_transaction_is_undone_by_the_next_holder(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with pytest.raises(AuthStoreBusy, match="expired mid-transaction"), \
            auth_store().transaction() as tx:
        tx.insert_user("late@team.test", "h")
        for doc in env._coll("auth_meta").docs:
            if doc["_id"] == tx_mod.LOCK_ID:
                doc.update(owner="someone-else", expires=1.0)  # expired and taken by another
    accounts.set_display_name(b, "next")  # the next holder first undoes the dead one's journal
    assert accounts.find_user("late@team.test") is None and not _journal_left(env)


# -- selection (A-W1) -------------------------------------------------------------------------
def test_a_global_mongo_selection_does_not_move_auth(env: AuthEnv,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS")
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    assert type(auth_store()).__name__ == "SqliteAuthStore"  # the global value alone: not auth
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "settings=mongo,auth=file")
    assert type(auth_store()).__name__ == "SqliteAuthStore"
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "auth=mongo")  # only its own entry (the G1 flip)
    assert isinstance(auth_store(), MongoAuthStore)


# -- the journal itself ------------------------------------------------------------------------
def test_several_writes_to_one_document_are_undone_newest_first(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with pytest.raises(RuntimeError, match="boom"), auth_store().transaction() as tx:
        tx.set_disabled(b, True)
        tx.set_disabled(b, False)
        tx.set_display_name(b, "x")
        raise RuntimeError("boom")
    assert accounts.get_user(b).disabled is False and accounts.get_user(b).display_name == ""


def test_an_undo_never_overwrites_a_newer_value(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with pytest.raises(RuntimeError, match="boom"), auth_store().transaction() as tx:
        tx.set_display_name(b, "mine")
        next(d for d in env._coll("auth_users").docs if d.get("_id") == b)["display_name"] = "newer"
        raise RuntimeError("boom")  # the compare-and-set sees a value it did not write: leaves it
    assert accounts.get_user(b).display_name == "newer"


def test_a_commit_whose_journal_was_undone_underneath_it_fails(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with pytest.raises(AuthStoreBusy, match="the change was undone"), \
            auth_store().transaction() as tx:
        tx.set_display_name(b, "mine")
        env._coll("auth_meta").docs[:] = [d for d in env._coll("auth_meta").docs
                                          if d["_id"] != tx_mod.JOURNAL_ID]


def test_the_journal_holds_hashes_only_beside_the_users(env: AuthEnv) -> None:
    a, _b, _c = _seed()
    with pytest.raises(RuntimeError, match="boom"), auth_store().transaction() as tx:
        tx.set_password_hash(a, "$argon2id$replacement")
        holders = {n for n, c in env.server.database("autotester").collections.items()
                   if "$argon2" in repr(c.docs)}
        assert holders == {"auth_users"}  # the entry that can undo it sits there too (M30)
        raise RuntimeError("boom")

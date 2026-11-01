"""Fencing of the Mongo auth store (mongo-store U6bf, M29/M30): a holder that stalls past its lease
can land NO write once a successor has run (the checker reproductions, deterministic here: the
successor runs at the exact call where the stalled holder resumes), a reader undoes a dead
holder's journal before it reads, a failed post-commit sweep is cleaned by the next holder, and a
login-time rehash keeps sessions on both backends while a reset revokes them."""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from auth_harness import ADMIN, PASSWORD
from auth_store_backends import BACKENDS, AuthEnv, auth_env
from fake_mongo import FakeCollection
from pymongo.errors import AutoReconnect
from test_auth_store_recovery import (
    HASH,
    NEW_PASSWORD,
    OTHER,
    THIRD,
    _age_out_lease,
    _journal_left,
    _kill_at,
    _seed,
    _shape,
)

from autotester.auth import accounts, groups, sessions
from autotester.auth import store_mongo_tx as tx_mod
from autotester.auth.passwords import needs_rehash
from autotester.auth.store import auth_store
from autotester.auth.store_mongo import AuthStoreBusy

Predicate = Callable[[FakeCollection, tuple[Any, ...]], bool]


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


def _at_call(mp: pytest.MonkeyPatch, method: str, when: Predicate,
             event: Callable[[], None]) -> None:
    """The first FakeCollection call of `method` that satisfies `when` is preceded by `event`:
    the stalled holder is paused exactly there while `event` (the successor) runs."""
    real, fired = getattr(FakeCollection, method), []

    def wrapper(self: FakeCollection, *args: Any, **kwargs: Any) -> Any:
        if not fired and when(self, args):
            fired.append(1)
            event()
        return real(self, *args, **kwargs)
    mp.setattr(FakeCollection, method, wrapper)


def _is(name: str, **want: Any) -> Predicate:
    return lambda coll, args: coll.name == name and all(
        args[0].get(k) == v for k, v in want.items())


def _successor(env: AuthEnv, b: int) -> Callable[[], None]:
    def run() -> None:  # the lease expires, a successor takes over, recovers and commits
        _age_out_lease(env)
        accounts.set_display_name(b, "successor")
    return run


def _nth_entry(n: int) -> Predicate:
    seen = [0]

    def when(coll: FakeCollection, args: tuple[Any, ...]) -> bool:
        if coll.name == "auth_users" and args[0].get("kind") == "undo":
            seen[0] += 1
        return seen[0] == n
    return when


def _two_names(a: int) -> None:
    with auth_store().transaction() as tx:
        tx.set_display_name(a, "one")
        tx.set_display_name(a, "two")


def _late_user() -> None:
    with auth_store().transaction() as tx:
        tx.insert_user("late@team.test", HASH)


CASES = {  # where the stalled holder resumes: (operation, FakeCollection method, predicate)
    "before-its-marker": (lambda a: accounts.set_user_groups(a, []), "insert_one",
                          _is("auth_meta", kind="tx")),
    "before-its-entry": (lambda a: accounts.set_user_groups(a, []), "insert_one",
                         _is("auth_users", kind="undo")),
    "before-its-second-entry": (_two_names, "insert_one", _nth_entry(2)),
    "before-a-patch": (lambda a: accounts.set_user_groups(a, []), "update_one",
                       lambda c, a: c.name == "auth_users" and "group_ids" in a[1]["$set"]),
    "before-a-delete": (lambda a: accounts.delete_user(a), "delete_one",
                        lambda c, a: c.name == "auth_users" and "_e" in a[0]
                        and a[0].get("_id") == 1),
    "before-an-insert": (lambda a: _late_user(), "insert_one",
                         _is("auth_users", email="late@team.test")),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_a_stalled_holder_lands_no_write_once_a_successor_ran(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    a, b, c = _seed()
    before = _shape()
    op, method, where = CASES[case]
    _at_call(monkeypatch, method, where, _successor(env, b))
    with pytest.raises((AuthStoreBusy, tx_mod.StoreDuplicateKey)):
        op(a)
    assert accounts.get_user(b).display_name == "successor"  # the successor's commit stands
    assert accounts.find_user("late@team.test") is None
    assert accounts.get_user(a).display_name == ""  # nothing of the stalled holder's landed
    assert _shape() == before
    assert len([u for u in accounts.list_users() if "Admin/CEO" in u.groups]) == 1
    with pytest.raises(accounts.AccountError):  # the privilege escalation of the reproduction
        accounts.claim_admin(c)
    accounts.set_display_name(b, "after")  # the next holder leaves nothing of the stalled one
    assert not _journal_left(env)
    assert all(d.get("kind") != tx_mod.UNDO for d in env._coll("auth_users").docs)


def test_a_stalled_holder_cannot_commit_while_its_journal_is_being_undone(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    _a, b, _c = _seed()
    outcome: list[str] = []
    with pytest.raises(AuthStoreBusy, match="expired mid-transaction"), \
            auth_store().transaction() as tx:
        tx.set_display_name(b, "stalled")

        def late_commit() -> None:  # the stalled holder wakes up while the successor replays
            with pytest.raises(AuthStoreBusy):
                tx.commit()
            outcome.append("refused")
        _at_call(monkeypatch, "find", lambda c, a: c.name == "auth_users" and "epoch" in a[0],
                 late_commit)
        _age_out_lease(env)
        accounts.set_display_name(b, "successor")
    assert outcome == ["refused"] and accounts.get_user(b).display_name == "successor"
    assert not _journal_left(env)


def test_the_stalled_holders_late_insert_meets_a_tombstone_only_a_later_epoch_may_clear(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    _a, b, _c = _seed()

    def stalled() -> None:
        with auth_store().transaction() as tx:
            tx.add_project_relation("proj", b, "viewer")
    _at_call(monkeypatch, "insert_one", lambda c, a: c.name == "auth_grants", _successor(env, b))
    with pytest.raises(AuthStoreBusy, match="refused"):  # refused, not "a duplicate"
        stalled()
    assert any(d.get("kind") == tx_mod.FENCE for d in env._coll("auth_grants").docs)
    with auth_store().transaction() as tx:  # a legitimate later holder can grant the same thing
        tx.add_project_relation("proj", b, "viewer")
    with auth_store().reading() as tx:
        assert tx.project_people("proj") == {"viewer": {OTHER}}


def test_the_epoch_only_grows_and_every_write_carries_it(env: AuthEnv) -> None:
    _seed()
    seen: list[int] = []
    for _ in range(3):
        with tx_mod.lease(auth_store()._s) as held:  # type: ignore[attr-defined]
            seen.append(held.epoch)
    assert seen == sorted(set(seen)) and seen[0] >= 2
    users = [d for d in env._coll("auth_users").docs if d.get("kind") != tx_mod.UNDO]
    assert users and all(isinstance(d.get("_e"), str) and d["_e"] for d in users)


def test_a_reader_undoes_a_dead_holders_journal_before_any_session_resolves(env: AuthEnv) -> None:
    visible, points = [0], [0]
    for k in range(1, 60):
        env.fresh()
        _a, b, _c = _seed()
        before, token = _shape(), sessions.create_session(b)

        def refused(b: int = b) -> object:
            dev = next(g for g in groups.list_groups() if g.seed == "developer")
            return groups.update_group(dev.id, dev.name, [*dev.permissions, "users.manage"],
                                       member_ids=[b, 99999])
        if not _kill_at(env, k, refused):
            break
        _age_out_lease(env)
        if k % 2:  # the successor itself dies part way through its recovery: its marker is aborted
            _kill_at(env, 3 + k % 5, lambda who=b: accounts.set_display_name(who, "next"))
            _age_out_lease(env)
        points[0] += 1
        raw = next(d for d in env._coll("auth_groups").docs if d.get("seed") == "developer")
        visible[0] += "users.manage" in raw["permissions"]
        seen = sessions.resolve_session(token)  # the FIRST thing that touches the store: a read
        assert seen is not None and "users.manage" not in seen.permissions
        assert _shape() == before
    assert points[0] >= 20 and visible[0] >= 3  # users.manage really was granted at some points


@pytest.mark.parametrize("what", ["reset", "delete"])
def test_a_committed_journal_whose_sweep_failed_is_swept_by_the_next_holder(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch, what: str) -> None:
    _a, b, c = _seed()
    real, failing = FakeCollection.delete_one, [True]

    def flaky(self: FakeCollection, flt: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        if failing[0] and self.name == "auth_users" and str(flt.get("_id", "")).startswith("undo:"):
            raise AutoReconnect("down")  # the post-commit sweep cannot reach the entries
        return real(self, flt, *args, **kwargs)
    monkeypatch.setattr(FakeCollection, "delete_one", flaky)
    if what == "reset":
        accounts.reset_password(b, NEW_PASSWORD)
    else:
        accounts.delete_user(c)
    failing[0] = False
    leftovers = repr([d for d in env._coll("auth_users").docs if d.get("kind") == tx_mod.UNDO])
    assert (HASH if what == "reset" else THIRD) in leftovers  # the old hash / the deleted account
    accounts.set_display_name(b, "next")  # the next lease holder sweeps them
    assert not _journal_left(env)
    assert not any(str(d["_id"]).startswith("undo:") for d in env._coll("auth_users").docs)
    if what == "reset":  # the committed change stands: the new password works, the old one does not
        assert accounts.authenticate(OTHER, NEW_PASSWORD) is not None
        assert accounts.authenticate(OTHER, PASSWORD) is None
    else:
        assert accounts.find_user(THIRD) is None
        assert THIRD not in repr(env._coll("auth_users").docs)  # no copy of the deleted account


@pytest.mark.parametrize("backend", BACKENDS)
def test_a_login_time_rehash_keeps_sessions_but_a_reset_revokes_them(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str) -> None:
    from argon2 import PasswordHasher
    gen = auth_env(backend, tmp_path, monkeypatch)
    next(gen)
    try:
        user = accounts.signup(ADMIN, PASSWORD)
        weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)
        assert needs_rehash(weak)
        with auth_store().transaction() as tx:
            tx.set_password_hash(user.id, weak)
        first, second = sessions.create_session(user.id), sessions.create_session(user.id)
        assert accounts.authenticate(ADMIN, PASSWORD) is not None  # triggers the rehash
        with auth_store().reading() as tx:
            record = tx.login_record(ADMIN)
        assert record is not None and not needs_rehash(record[1])  # it did happen
        assert sessions.resolve_session(first) and sessions.resolve_session(second)
        accounts.reset_password(user.id, NEW_PASSWORD)  # a reset does revoke
        assert sessions.resolve_session(first) is None and sessions.resolve_session(second) is None
    finally:
        with contextlib.suppress(StopIteration):
            next(gen)

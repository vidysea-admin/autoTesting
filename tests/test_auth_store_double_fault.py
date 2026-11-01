"""Second faults in the Mongo auth store (mongo-store U6bf fix cycle 1): a recovery that is itself
killed at every call (B1: the grant of a refused transaction must still be undone), a replay that
resumes after a later holder moved on (B2: a deleted account never comes back), a rollback that
lost its lease (writes nothing), an insert then a patch of one document killed anywhere (f10),
and two stalled creations in one collection, each fenced by its own tombstone (A3/B4)."""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from auth_store_backends import AuthEnv, auth_env
from fake_mongo import FakeCollection
from test_auth_store_fencing import _at_call
from test_auth_store_recovery import (
    NEW_PASSWORD,
    OTHER,
    THIRD,
    _age_out_lease,
    _journal_left,
    _kill_at,
    _seed,
    _shape,
    _sweep,
)

from autotester.auth import accounts, groups
from autotester.auth import store_mongo_tx as tx_mod
from autotester.auth.store import auth_store
from autotester.auth.store_mongo import AuthStoreBusy, StoreDuplicateKey

NEW_ACCOUNT = "fresh@team.test"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


def _developer() -> Any:
    return next(g for g in groups.list_groups() if g.seed == "developer")


def _grant_rename_refuse() -> None:
    """Two writes to ONE group, then a refusal: the grant must not survive anywhere."""
    dev = _developer()
    with auth_store().transaction() as tx:
        tx.set_group_permissions(dev.id, {*dev.permissions, "users.manage"})
        tx.rename_group(dev.id, "Renamed")
        raise RuntimeError("refused")


def _raw_developer(env: AuthEnv) -> dict[str, Any]:
    return next(d for d in env._coll("auth_groups").docs if d.get("seed") == "developer")


def _killed_twice(env: AuthEnv, first: int, second: int) -> tuple[bool, bool, int]:
    """Kill the refused transaction at call `first`, age out its lease, then kill the recovery (a
    plain write that takes the lease) at call `second`: (first reached, second reached, B)."""
    env.fresh()
    _a, b, _c = _seed()
    if not _kill_at(env, first, _grant_rename_refuse):
        return False, False, b
    _age_out_lease(env)
    reached = _kill_at(env, second, lambda: accounts.set_display_name(b, "next"))
    _age_out_lease(env)
    return True, reached, b


def test_a_recovery_killed_at_any_call_is_finished_by_the_next_one(env: AuthEnv) -> None:
    """B1: the refused transaction is killed at every call point, then its recovery is killed at
    every call point, then a last holder runs: nothing of the refusal may remain (31 of 917
    such points kept the grant when a second recoverer could not match the first's stamp)."""
    env.fresh()
    _seed()
    before, points, pending, first = _shape(), 0, 0, 0
    while True:
        first, second = first + 1, 0
        while True:
            second += 1
            began, reached, b = _killed_twice(env, first, second)
            if not (began and reached):
                break
            points += 1
            raw = _raw_developer(env)
            pending += "users.manage" in raw["permissions"] or raw["name"] == "Renamed"
            accounts.set_display_name(b, "last")  # the last holder finishes whatever is left
            assert _shape() == before and not _journal_left(env), (first, second)
        if not began:
            break
    assert points >= 500 and pending >= 100, (points, pending)  # many nested points, many mid-undo


def _refuses_after_deleting(account: int) -> Callable[[], None]:
    def refuse() -> None:
        with auth_store().transaction() as tx:
            tx.delete_user(account)
            raise RuntimeError("refused")
    return refuse


@pytest.mark.parametrize("who", ["recovery", "rollback"])
def test_a_replay_that_resumes_late_does_not_bring_back_an_account_deleted_since(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch, who: str) -> None:
    """B2: a replay paused at its write while the lease passes on, the journal is finished by a
    successor and a later holder deletes the account for good: it must stay deleted."""
    _a, b, c = _seed()
    refuse = _refuses_after_deleting(c)

    def later_holder_deletes_it() -> None:
        _age_out_lease(env)
        accounts.delete_user(c)

    def at_the_replay(coll: FakeCollection, args: tuple[Any, ...]) -> bool:
        flt = args[0]
        return (coll.name == "auth_users" and flt.get("_id") == c
                and isinstance(flt.get("_e"), dict) == (who == "rollback"))
    if who == "recovery":
        with monkeypatch.context() as died, pytest.raises(RuntimeError):
            died.setattr(tx_mod.MongoTxBase, "rollback", lambda self: None)  # the holder dies
            refuse()
        _at_call(monkeypatch, "update_one", at_the_replay, later_holder_deletes_it)
        with contextlib.suppress(AuthStoreBusy):  # this recoverer lost its lease while paused
            accounts.set_display_name(b, "recoverer")
    else:
        _at_call(monkeypatch, "update_one", at_the_replay, later_holder_deletes_it)
        with pytest.raises(RuntimeError, match="refused"):
            refuse()
    assert accounts.find_user(THIRD) is None
    assert not any(d.get("_id") == c for d in env._coll("auth_users").docs)  # not even hidden


def test_a_rollback_that_lost_its_lease_writes_nothing(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    _a, b, _c = _seed()
    seen: list[tuple[str, str]] = []

    def watch(method: str) -> None:
        real = getattr(FakeCollection, method)

        def wrapper(self: FakeCollection, flt: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
            if flt.get("_id") != tx_mod.LOCK_ID:  # releasing its own (absent) lease is not a write
                seen.append((method, self.name))
            return real(self, flt, *args, **kwargs)
        monkeypatch.setattr(FakeCollection, method, wrapper)
    with pytest.raises(RuntimeError, match="late"), auth_store().transaction() as tx:
        tx.set_display_name(b, "stalled")
        _age_out_lease(env)
        accounts.set_display_name(b, "successor")  # takes over and undoes the stalled write
        for method in ("insert_one", "update_one", "delete_one"):
            watch(method)
        raise RuntimeError("late failure")
    assert seen == [] and accounts.get_user(b).display_name == "successor"


def _bootstrap_new(env: AuthEnv) -> tuple[Callable[[], object], Callable[[], None]]:
    """A new account is inserted, then patched (its membership) in one transaction; whatever
    call it dies at, a reader recovers it: whole, or not there at all."""
    _seed()

    def check() -> None:
        found = accounts.find_user(NEW_ACCOUNT)  # a read: it recovers the dead holder first
        if found is None:
            assert not any(NEW_ACCOUNT in repr(d) for d in env._coll("auth_users").docs)
        else:
            assert "Admin/CEO" in found.groups and accounts.authenticate(
                NEW_ACCOUNT, NEW_PASSWORD) is not None
    return lambda: accounts.bootstrap_admin(NEW_ACCOUNT, NEW_PASSWORD), check


def test_an_insert_then_a_patch_of_one_document_is_recovered_whole_or_absent(
        env: AuthEnv) -> None:
    """f10: the recovery undoes the patch before the insert; oldest first leaves a half-built
    account behind (kill points 25-28)."""
    assert _sweep(env, _bootstrap_new) >= 28


def _inserting(group: str) -> Callable[[FakeCollection, tuple[Any, ...]], bool]:
    return lambda coll, args: coll.name == "auth_groups" and args[0].get("name") == group


def test_two_stalled_creations_in_one_collection_are_both_refused(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """A3/B4: the second tombstone of a collection must not collide with the first on the unique
    `name` index (a missing field is null, and null is one value), or its insert goes unfenced."""
    _a, b, _c = _seed()
    names = []

    def create(name: str) -> None:
        names.append(name)
        with auth_store().transaction() as tx:
            tx.insert_group(name)

    def second_stalls_too() -> None:
        _age_out_lease(env)
        _at_call(monkeypatch, "insert_one", _inserting("G2"),
                 lambda: (_age_out_lease(env), accounts.set_display_name(b, "successor")))
        with pytest.raises(AuthStoreBusy, match="refused"):
            create("G2")
    _at_call(monkeypatch, "insert_one", _inserting("G1"), second_stalls_too)
    with pytest.raises(AuthStoreBusy, match="refused"):
        create("G1")
    assert names == ["G1", "G2"] and not {"G1", "G2"} & {g.name for g in groups.list_groups()}
    assert sum(d.get("kind") == tx_mod.FENCE for d in env._coll("auth_groups").docs) == 2
    assert accounts.get_user(b).display_name == "successor"


def test_a_holder_that_fenced_an_undone_insert_may_make_the_same_insert_itself(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tombstone a recoverer leaves carries ITS epoch; only a LATER epoch used to clear it, so
    the recoverer's own grant of the same id was refused. The stalled holder is still refused."""
    _a, b, _c = _seed()
    outcome: list[str] = []

    def grant() -> None:
        with auth_store().transaction() as tx:
            tx.add_project_relation("proj", b, "viewer")

    def holder_grants_it() -> None:
        _age_out_lease(env)
        try:
            grant()
            outcome.append("landed")
        except AuthStoreBusy:
            outcome.append("refused")
    _at_call(monkeypatch, "insert_one", lambda c, a: c.name == "auth_grants", holder_grants_it)
    with pytest.raises((AuthStoreBusy, StoreDuplicateKey)):
        grant()
    assert outcome == ["landed"]
    with auth_store().reading() as tx:
        assert tx.project_people("proj") == {"viewer": {OTHER}}

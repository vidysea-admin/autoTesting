"""AT-1431 and AT-1432 (mongo-store U6c, M29/M30): the id slot of a re-creatable document is never
empty again, so a stalled holder's late insert cannot resurrect a revoked grant however many
holders came and went; a late committed sweep never deletes a recreated document; the abort
compare-and-set comes before the marker read; a recovery resolves only EARLIER epochs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from auth_store_backends import AuthEnv, auth_env
from fake_mongo import FakeCollection
from pymongo.errors import AutoReconnect
from test_auth_store_fencing import _at_call, _is
from test_auth_store_recovery import OTHER, _age_out_lease, _journal_left, _seed

from autotester.auth import accounts
from autotester.auth import store_mongo_fence as fence
from autotester.auth.store import auth_store
from autotester.auth.store_mongo import AuthStoreBusy


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


def _write(env: AuthEnv, user: int, name: str) -> Callable[[], None]:
    def run() -> None:
        _age_out_lease(env)
        accounts.set_display_name(user, name)
    return run


def _grant(b: int) -> None:
    with auth_store().transaction() as tx:
        tx.add_project_relation("proj", b, "viewer")


def _revoke(b: int) -> None:
    with auth_store().transaction() as tx:
        tx.remove_project_relation("proj", b, "viewer")


def _people() -> dict[str, set[str]]:
    with auth_store().reading() as tx:
        return tx.project_people("proj")


def _slots(env: AuthEnv, name: str = "auth_grants") -> list[dict[str, Any]]:
    return list(env._coll(name).docs)


def test_a_zombie_insert_after_the_slot_was_re_granted_and_revoked_lands_nothing(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """The checker's P1 reproduction: Z paused before its insert; S1 recovers Z; S2 re-grants;
    S3 revokes. The revoked grant must stay revoked when Z resumes."""
    _a, b, _c = _seed()

    def successors() -> None:
        _age_out_lease(env)
        accounts.set_display_name(b, "s1")  # recovers the zombie
        _grant(b)  # s2: the same grant again
        _revoke(b)  # s3: and revoked
        assert _people() == {}
    _at_call(monkeypatch, "insert_one", _is("auth_grants"), successors)
    with pytest.raises(AuthStoreBusy):
        _grant(b)
    assert _people() == {}  # the revoked grant did not come back
    assert _slots(env) and all(str(d["_e"]).startswith("G:") for d in _slots(env))
    _grant(b)  # a legitimate later holder can still grant it
    assert _people() == {"viewer": {OTHER}}
    assert not _journal_left(env)


def test_a_committed_delete_leaves_the_slot_hidden_and_blank_not_absent(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    _grant(b)
    _revoke(b)
    docs = _slots(env)
    assert len(docs) == 1 and str(docs[0]["_e"]).startswith("G:")  # hidden, never removed
    assert docs[0]["slug"] is None and docs[0]["user_id"] is None  # nothing of the grant stays
    assert _people() == {}


def test_a_recoverer_raises_an_older_hidden_stamp_past_the_dead_holders_epoch(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hidden since an early epoch; Z (later) stalls before inserting; S recovers Z. If S left
    the old stamp, Z's compare-and-set over it would pass and resurrect the grant."""
    _a, b, _c = _seed()
    _grant(b)
    _revoke(b)
    old = _slots(env)[0]["_e"]
    _at_call(monkeypatch, "insert_one", _is("auth_grants"), _write(env, b, "successor"))
    with pytest.raises(AuthStoreBusy):
        _grant(b)
    assert _people() == {}
    assert fence.stamp_epoch(_slots(env)[0]["_e"]) > fence.stamp_epoch(old)


def test_the_stamp_epoch_orders_every_stamp_the_fence_writes() -> None:
    assert fence.stamp_epoch("00000007.000003") == 7 == fence.stamp_epoch("G:00000007.000003")
    assert fence.stamp_epoch(fence.hide_stamp(9)) == 9 == fence.stamp_epoch("F:00000009.000001")
    assert fence.stamp_epoch("nonsense") > 10**9  # a stamp with no epoch sorts after every epoch


def test_a_late_committed_sweep_does_not_delete_a_recreated_document(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """Z deleted a session and committed; its sweep stalls before the physical delete. A
    successor sweeps it and the id is created again. Z's late delete must match nothing."""
    _a, b, _c = _seed()
    with auth_store().transaction() as tx:
        tx.insert_session("d1", b, "2000-01-01", "2999-01-01")

    def successor() -> None:
        _age_out_lease(env)
        with auth_store().transaction() as tx:  # sweeps Z's leftovers, then creates d1 again
            tx.insert_session("d1", b, "2000-01-02", "2999-01-01")
    _at_call(monkeypatch, "delete_one",
             lambda c, a: c.name == "auth_sessions" and a[0].get("_id") == "d1", successor)
    with auth_store().transaction() as tx:
        tx.delete_session("d1")
    with auth_store().reading() as tx:
        assert tx.has_session("d1")  # the recreated session stands
    assert [d["created_at"] for d in _slots(env, "auth_sessions")] == ["2000-01-02"]


def test_a_commit_that_lands_between_the_abort_cas_and_the_marker_read_stands(
        env: AuthEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """The checker's p5: a successor aborts the marker with a compare-and-set and THEN reads it.
    A commit that lands in between makes the CAS a no-op; the marker reads committed and the
    entries are swept, not replayed (which would undo a committed change)."""
    _a, b, c = _seed()
    real = FakeCollection.delete_one

    def sweep_fails(self: FakeCollection, flt: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        if self.name == "auth_users" and str(flt.get("_id", "")).startswith("undo:"):
            raise AutoReconnect("down")  # the committer's own sweep cannot delete its entries
        return real(self, flt, *args, **kwargs)
    with pytest.raises(AuthStoreBusy), auth_store().transaction() as tx:
        tx.set_display_name(b, "committed")

        def late_commit() -> None:
            monkeypatch.setattr(FakeCollection, "delete_one", sweep_fails)
            tx.commit()  # lands right after the successor's CAS was about to run
            monkeypatch.setattr(FakeCollection, "delete_one", real)
        _at_call(monkeypatch, "update_one",
                 lambda c, a: c.name == "auth_meta" and a[1].get("$set") == {"state": "aborted"},
                 late_commit)
        _age_out_lease(env)
        accounts.set_display_name(c, "successor")
    assert accounts.get_user(b).display_name == "committed"  # not undone by the replay
    assert accounts.get_user(c).display_name == "successor"
    assert not _journal_left(env)


def test_a_recovery_resolves_only_earlier_epochs(env: AuthEnv) -> None:
    """A journal of a LATER epoch belongs to a live holder that took over a lease the recoverer
    lost; resolving it would undo that holder's work."""
    _a, b, _c = _seed()
    store = auth_store()._s  # type: ignore[attr-defined]
    meta, users = env._coll("auth_meta"), env._coll("auth_users")
    meta.docs.append({"_id": fence.tx_id(99), "kind": "tx", "state": "open", "epoch": 99,
                      "owner": "x"})
    users.docs.append({"_id": "undo:00000099.000001", "email": "u", "generation": "u",
                       "kind": "undo", "epoch": 99, "owner": "x", "me": "00000099.000001",
                       "op": "set", "coll": "auth_users", "doc_id": b, "pre": "p", "prior": {},
                       "gone": False})
    fence.recover(store, 5)
    assert any(d["_id"] == fence.tx_id(99) and d["state"] == "open" for d in meta.docs)
    assert any(d["_id"] == "undo:00000099.000001" for d in users.docs)
    fence.recover(store, 100)  # an earlier epoch IS resolved
    assert not any(d["_id"] == fence.tx_id(99) for d in meta.docs)


def test_an_undone_insert_leaves_a_hidden_slot_with_none_of_its_data(env: AuthEnv) -> None:
    """A refused change that had inserted a share must not leave the address behind (M30)."""
    _seed()
    with pytest.raises(RuntimeError, match="refused"), auth_store().transaction() as tx:
        tx.set_share("p", "v1", "person@example.test", True, "admin", "2000-01-01")  # type: ignore[attr-defined]
        raise RuntimeError("refused")
    docs = _slots(env, "video_shares")
    assert len(docs) == 1 and str(docs[0]["_e"]).startswith("G:")
    assert all(v is None for k, v in docs[0].items() if k not in ("_id", "_e"))
    assert "person@example.test" not in env.dump()

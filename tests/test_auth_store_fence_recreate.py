"""E10.3 (e2e-fixes, mongo-store U6c checker B finding 1): delete, then re-create, of ONE slotted
id (a grant, a share) inside a single transaction is undone whole. A refused transaction and a
holder that died before committing both leave the ORIGINAL document present; the newest-first
replay used to hide the re-inserted slot and the earlier delete's restore then matched nothing."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from auth_store_backends import AuthEnv, auth_env
from test_auth_store_recovery import OTHER, _age_out_lease, _journal_left, _seed, _sweep

from autotester.auth import accounts
from autotester.auth.store import auth_store
from autotester.auth.store_mongo import AuthStoreBusy

SLUG, VID, MAIL = "proj", "v1", "person@example.test"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env("mongo", tmp_path, monkeypatch)


def _share_in_place(tx: object, by: str) -> None:
    tx.set_share(SLUG, VID, MAIL, True, by, "2026-01-01")  # type: ignore[attr-defined]


def _recreate_share(tx: object) -> None:
    tx.set_share(SLUG, VID, MAIL, False, "x", "2026-01-02")  # type: ignore[attr-defined]
    tx.set_share(SLUG, VID, MAIL, True, "second", "2026-01-03")  # type: ignore[attr-defined]


def _recreate_grant(b: int) -> Callable[[object], None]:
    def run(tx: object) -> None:
        tx.remove_project_relation(SLUG, b, "viewer")  # type: ignore[attr-defined]
        tx.add_project_relation(SLUG, b, "viewer")  # type: ignore[attr-defined]
    return run


def _seen_share() -> frozenset[str]:
    with auth_store().reading() as tx:
        return tx.share_emails(SLUG, VID)  # type: ignore[attr-defined,no-any-return]


def _seen_grant() -> dict[str, set[str]]:
    with auth_store().reading() as tx:
        return tx.project_people(SLUG)


def _held(env: AuthEnv, name: str) -> list[dict[str, object]]:
    return [d for d in env._coll(name).docs if not str(d["_e"]).startswith("G:")]


def test_a_refused_transaction_restores_the_original_share(env: AuthEnv) -> None:
    _seed()
    with auth_store().transaction() as tx:
        _share_in_place(tx, "original")
    with pytest.raises(ValueError, match="declined"), auth_store().transaction() as tx:
        _recreate_share(tx)
        raise ValueError("declined")
    assert _seen_share() == {MAIL}
    assert [d["granted_by"] for d in _held(env, "video_shares")] == ["original"]
    assert not _journal_left(env)


def test_a_refused_transaction_restores_the_original_grant(env: AuthEnv) -> None:
    _a, b, _c = _seed()
    with auth_store().transaction() as tx:
        tx.add_project_relation(SLUG, b, "viewer")
    with pytest.raises(ValueError, match="declined"), auth_store().transaction() as tx:
        _recreate_grant(b)(tx)
        raise ValueError("declined")
    assert _seen_grant() == {"viewer": {OTHER}}
    assert not _journal_left(env)


@pytest.mark.parametrize("kind", ["share", "grant"])
def test_a_holder_that_died_before_committing_leaves_the_original_present(
        env: AuthEnv, kind: str) -> None:
    """The lease expires mid-transaction and a successor recovers it (the recoverer's replay)."""
    _a, b, _c = _seed()
    with auth_store().transaction() as tx:
        if kind == "share":
            _share_in_place(tx, "original")
        else:
            tx.add_project_relation(SLUG, b, "viewer")
    with pytest.raises(AuthStoreBusy), auth_store().transaction() as tx:
        (_recreate_share if kind == "share" else _recreate_grant(b))(tx)
        _age_out_lease(env)
        accounts.set_display_name(b, "successor")  # takes the lease and undoes the dead journal
    assert (_seen_share() == {MAIL}) if kind == "share" else (
        _seen_grant() == {"viewer": {OTHER}})
    assert not _journal_left(env)
    if kind == "share":
        assert [d["granted_by"] for d in _held(env, "video_shares")] == ["original"]


def _scenario(kind: str) -> Callable[[AuthEnv], tuple[Callable[[], object], Callable[[], None]]]:
    def scenario(env: AuthEnv) -> tuple[Callable[[], object], Callable[[], None]]:
        _a, b, _c = _seed()
        with auth_store().transaction() as tx:
            if kind == "share":
                _share_in_place(tx, "original")
            else:
                tx.add_project_relation(SLUG, b, "viewer")

        def op() -> None:
            with auth_store().transaction() as tx:
                (_recreate_share if kind == "share" else _recreate_grant(b))(tx)

        def check() -> None:  # whole or absent: the document is there with either its first
            # value or the re-created one, never gone
            assert (_seen_share() == {MAIL}) if kind == "share" else (
                _seen_grant() == {"viewer": {OTHER}})
        return op, check
    return scenario


@pytest.mark.parametrize("kind", ["share", "grant"])
def test_a_kill_at_every_call_point_never_loses_the_document(env: AuthEnv, kind: str) -> None:
    assert _sweep(env, _scenario(kind)) >= 10  # not vacuous: a real number of call points

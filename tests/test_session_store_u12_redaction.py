"""mongo-store U12: a session never leaves the door (M40), the store off or down, and the
role-account wiring. Fake Mongo and fake browser contexts only; planted canaries."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from credential_store_support import CredRig, make_rig
from session_store_support import (
    BLOB_LEAF,
    NOW,
    PROJECT,
    SID,
    TOK,
    RoleFake,
    cookie,
    docs,
    elsewhere,
    make_session,
    sample,
)

from autotester.browser import profiles
from autotester.browser.profiles import (
    capture_session,
    forget_session,
    load_session,
    restore_session,
    save_session,
    session_values,
)
from autotester.browser.secrets import SecretStore
from autotester.stages.multi_role_session import RoleSessions
from autotester.store.mongo_backend import default_backend
from autotester.store.mongo_routes import StoreSecretRefused, repo_redactor


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[CredRig]:
    with make_rig(tmp_path, monkeypatch).live() as live:
        yield live


# ---- M40: a session never leaves the door ------------------------------------------------------


def test_a_captured_session_joins_the_redactor_and_the_prompt_gate(rig: CredRig) -> None:
    session = make_session(rig.root)
    capture_session(session, PROJECT, "t1")
    scrub = session.secrets.redactor().scrub
    line = f"trace {SID} body {TOK} err {BLOB_LEAF} lang en n 1"
    clean = scrub(line)
    assert not {SID, TOK, BLOB_LEAF} & set(clean.split()) and "lang en n 1" in clean
    for value in (SID, TOK, BLOB_LEAF):
        with pytest.raises(ValueError):
            session.secrets.guard_prompt(f"prompt {value}")
        assert value not in scrub(f"{type(KeyError).__name__}: {value!r}")


def test_a_restored_session_joins_the_redactor(rig: CredRig) -> None:
    fresh = {"cookies": [cookie("sid", SID, expires=-1)],
             "origins": [{"origin": "https://app.pl.test", "localStorage": [
                 {"name": "tok", "value": TOK}]}]}
    save_session(PROJECT, "t1", fresh)
    session = make_session(rig.root, state={"cookies": [], "origins": []})
    assert restore_session(session, PROJECT, "t1")
    assert SID not in session.secrets.redactor().scrub(f"x {SID} {TOK}")
    assert TOK not in session.secrets.redactor().scrub(f"x {SID} {TOK}")


def test_the_run_wide_redactor_and_the_write_gate_cover_stored_sessions(rig: CredRig) -> None:
    default_backend().put("projects/p/x.json", "{}")  # the write gate is built and cached now
    save_session(PROJECT, "t1", sample(), now=NOW)
    scrubbed = repo_redactor().scrub(f"x {SID} {TOK}")
    assert SID not in scrubbed and TOK not in scrubbed
    for value in (SID, TOK, BLOB_LEAF):
        with pytest.raises(StoreSecretRefused):  # rebuilt after the session write
            default_backend().put("projects/p/leak.json", json.dumps({"v": value}))
    assert SID not in elsewhere(rig)


def test_short_values_are_not_masked_and_the_set_is_capped() -> None:
    values = session_values(sample())
    assert "en" not in values.values() and "1" not in values.values()
    many = {"cookies": [cookie(f"c{i}", f"Zk9-bulk-value-{i:04d}") for i in range(300)],
            "origins": []}
    assert len(session_values(many)) == profiles.MAX_MASKED


# ---- the store down, the store off, the role-account wiring -----------------------------------


def test_an_unreachable_store_raises_and_changes_no_file(rig: CredRig) -> None:
    from autotester.store.mongo_guard import StoreUnavailable

    before, rig.server.down = rig.tree(), True
    with pytest.raises(StoreUnavailable):
        capture_session(make_session(rig.root), PROJECT, "t1")
    with pytest.raises(StoreUnavailable):
        restore_session(make_session(rig.root), PROJECT, "t1")
    assert rig.tree() == before


def test_with_the_store_off_nothing_is_read_written_or_touched(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rig = make_rig(tmp_path, monkeypatch, area=False)
    session = make_session(rig.root)
    ctx = session._context
    before = rig.tree()
    assert capture_session(session, PROJECT, "t1") is False
    assert restore_session(session, PROJECT, "t1") is False
    assert save_session(PROJECT, "t1", sample()) is None and load_session(PROJECT, "t1") is None
    assert forget_session(PROJECT, "t1") is False and profiles.stored_session_values() == {}
    assert ctx.cookies == [] and ctx.scripts == [] and rig.tree() == before


def test_role_sessions_save_after_sign_in_and_restore_per_account(rig: CredRig) -> None:
    secrets = SecretStore(PROJECT, {})
    kwargs = dict(paths_root=rig.root, session_cls=RoleFake)
    sign_in = dict(user_locator="#u", password_locator="#p", submit_locator="#s")
    with RoleSessions(PROJECT, secrets, rig.root / "runs", **kwargs) as roles:
        roles.sign_in("t1", "https://app.pl.test/login", **sign_in)
        assert docs(rig) == []  # U12f (W2): signing in alone saves nothing; the proof comes first
        assert roles.save_login("t1")
    assert [d["_id"] for d in docs(rig)] == ["pl|t1"]
    assert SID not in secrets.redactor().scrub(f"x {SID}")  # masked from sign-in on
    RoleFake.made.clear()
    live = {"cookies": [cookie("sid", SID, expires=-1)], "origins": []}
    save_session(PROJECT, "t1", live)
    with RoleSessions(PROJECT, SecretStore(PROJECT, {}), rig.root / "runs", **kwargs):
        assert [c["name"] for c in RoleFake.made["pl-role-t1"]._context.cookies] == ["sid"]
        assert RoleFake.made["pl-role-t2"]._context.cookies == []

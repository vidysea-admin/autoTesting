"""mongo-store U8: the auth importer (M45) and the credential importer (M36, M46).

Fake Mongo and tmp dirs only; every account and credential value is synthetic.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fake_mongo import CANARY
from store_migrate_support import (
    PASS_VALUE,
    STRAY_VALUE,
    URI,
    USER_VALUE,
    Rig,
    make_rig,
    seed_auth,
    seed_state,
)

from autotester.auth import accounts, db
from autotester.auth import migrate_auth as ma
from autotester.auth.store_mongo_tx import JOURNAL_COLL, JOURNAL_ID, META
from autotester.store import migrate_creds as mc


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rig:
    return make_rig(tmp_path, monkeypatch)


def _sql(query: str) -> list[tuple]:
    with sqlite3.connect(db.auth_db_path()) as con:
        return con.execute(query).fetchall()


def _users(rig: Rig) -> dict[int, dict]:
    return {d["_id"]: d for d in rig.docs("auth_users")}


def test_users_come_across_with_their_ids_hashes_generations_and_groups(rig: Rig) -> None:
    ids = seed_auth(rig)
    accounts.delete_user(ids["b"])  # a gap: ids 1 and 3 must stay 1 and 3
    before = rig.tree()
    assert rig.invoke("migrate", "--apply", "--only", "auth").exit_code == 0
    assert rig.tree() == before  # the SQLite file is read-only to the importer
    source = {r[0]: r for r in _sql("SELECT id, email, password_hash, generation FROM users")}
    got = _users(rig)
    assert set(got) == set(source) == {ids["a"], ids["c"]}
    for uid, (_, email, pw, gen) in source.items():
        assert (got[uid]["email"], got[uid]["password_hash"], got[uid]["generation"]) == (
            email, pw, gen)
    admin = next(g for g in rig.docs("auth_groups") if g.get("seed") == "admin")
    assert admin["_id"] in got[ids["a"]]["group_ids"]
    alloc = next(d for d in rig.docs(META) if d["_id"] == "alloc:auth_users")
    assert alloc["next"] == max(got) + 1


def test_sessions_are_excluded_by_default_and_expired_ones_never_copy(rig: Rig) -> None:
    seed_auth(rig)
    done = rig.invoke("migrate", "--apply", "--only", "auth")
    assert "NOT copied" in done.output and rig.docs("auth_sessions") == []
    _sql("SELECT 1")
    with sqlite3.connect(db.auth_db_path()) as con:
        con.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00' "
                    "WHERE user_id = 1")
    done = rig.invoke("migrate", "--apply", "--only", "auth", "--include-sessions")
    assert done.exit_code == 0 and "copied (unexpired only)" in done.output
    digests = {d["_id"] for d in rig.docs("auth_sessions")}
    live = {r[0] for r in _sql("SELECT token_hash FROM sessions WHERE user_id != 1")}
    assert digests == live and len(live) == 2


def test_a_second_apply_writes_nothing_and_keeps_the_allocator(rig: Rig) -> None:
    seed_auth(rig)
    rig.invoke("migrate", "--apply", "--only", "auth")
    before = rig.everywhere()
    again = rig.invoke("migrate", "--apply", "--only", "auth")
    assert again.exit_code == 0 and "written: 0" in again.output
    assert rig.everywhere() == before


def test_the_import_goes_through_the_lease_and_leaves_no_journal(rig: Rig) -> None:
    seed_auth(rig)
    rig.invoke("migrate", "--apply", "--only", "auth")
    assert not any(d["_id"] == JOURNAL_ID for d in rig.docs(META))
    assert [d for d in rig.docs(JOURNAL_COLL) if d.get("kind") == "undo"] == []
    assert ("autotester", META) in rig.server.log  # the lease is taken in auth_meta


def test_a_failed_import_is_undone_whole(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    seed_auth(rig)

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError(f"disk on fire {URI}")

    monkeypatch.setattr(ma, "_import_users", boom)
    done = rig.invoke("migrate", "--apply", "--only", "auth")
    assert done.exit_code == 1 and "RuntimeError" in done.output and CANARY not in done.output
    assert rig.docs("auth_users") == []


def test_an_existing_account_is_never_overwritten(rig: Rig) -> None:
    ids = seed_auth(rig)
    rig.invoke("migrate", "--apply", "--only", "auth")
    mine = _users(rig)[ids["a"]]
    kept = mine["password_hash"]
    mine["password_hash"] = "changed-in-mongo"
    mine_c = _users(rig)[ids["c"]]
    mine_c["email"] = "someone-else@team.test"
    done = rig.invoke("migrate", "--apply", "--only", "auth")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output
    assert _users(rig)[ids["a"]]["password_hash"] == "changed-in-mongo" != kept
    assert _users(rig)[ids["c"]]["email"] == "someone-else@team.test"


def test_verify_reports_an_altered_account(rig: Rig) -> None:
    ids = seed_auth(rig)
    rig.invoke("migrate", "--apply", "--only", "auth")
    assert rig.invoke("verify", "--only", "auth").exit_code == 0
    _users(rig)[ids["a"]]["password_hash"] = "x"
    done = rig.invoke("verify", "--only", "auth")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output
    assert "$argon" not in done.output and "x" * 10 not in done.output


def test_dry_run_with_auth_opens_no_connection(rig: Rig) -> None:
    seed_auth(rig)
    done = rig.invoke("migrate", "--only", "auth")
    assert done.exit_code == 0 and rig.opened == 0 and "to_insert=3" in done.output


def _secret_docs(rig: Rig) -> dict[str, dict]:
    return {d["_id"]: d for d in rig.docs("secrets")}


def test_only_declared_keys_reach_the_door_and_the_secrets_collection(
        rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.ui import env_editor

    seed_state(rig)
    calls: list[tuple[str, tuple[str, ...]]] = []
    real = env_editor.put_credentials

    def spy(slug: str, values: dict[str, str]) -> None:
        calls.append((slug, tuple(values)))
        real(slug, values)

    monkeypatch.setattr(env_editor, "put_credentials", spy)
    done = rig.invoke("migrate", "--apply", "--only", "credentials")
    assert done.exit_code == 0, done.output
    assert sorted(calls) == [("demo", ("DEMO_PASS",)), ("demo", ("DEMO_USER",))]
    held = _secret_docs(rig)
    assert set(held) == {"DEMO_USER", "DEMO_PASS"} and held["DEMO_USER"]["p"] == "demo"
    assert held["DEMO_USER"]["value"] == USER_VALUE
    elsewhere = repr([(n, c.docs) for d in rig.server.databases.values()
                      for n, c in d.collections.items() if n != "secrets"])
    assert not {USER_VALUE, PASS_VALUE, STRAY_VALUE} & set(elsewhere.split("'"))
    assert STRAY_VALUE not in rig.everywhere()


def test_the_report_has_counts_never_a_value_a_key_or_a_deployment_secret(
        rig: Rig, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    seed_state(rig)
    shown = ""
    for args in (("migrate", "--only", "credentials"), ("migrate", "--apply"), ("verify",)):
        shown += rig.invoke(*args).output
    shown += capsys.readouterr().out + caplog.text
    assert "2 declared key(s)" in shown and "1 deployment secret(s) left out" in shown
    for banned in (USER_VALUE, PASS_VALUE, STRAY_VALUE, CANARY, "STRAY_KEY",
                   "AUTOTESTER_APPROVAL_KEY", "PATHLYNKS_MONGO_URI", "DEMO_PASS", "DEMO_USER",
                   "test-only-signing-key-never-a-real-secret"):
        assert banned not in shown


def test_env_is_never_edited_and_the_area_flag_is_not_left_on(rig: Rig) -> None:
    import os

    seed_state(rig)
    before = rig.tree()
    assert rig.invoke("migrate", "--apply", "--only", "credentials").exit_code == 0
    assert rig.tree() == before and "AUTOTESTER_STORE_AREAS" not in os.environ


def test_credentials_do_not_need_the_approval_key(
        rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    seed_state(rig)
    rig.write(".env", f"DEMO_USER={USER_VALUE}\nDEMO_PASS={PASS_VALUE}\n")
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)
    done = rig.invoke("migrate", "--apply", "--only", "credentials")
    assert done.exit_code == 0 and len(_secret_docs(rig)) == 2


def test_a_stored_credential_is_never_replaced_and_a_rerun_writes_nothing(rig: Rig) -> None:
    seed_state(rig)
    rig.invoke("migrate", "--apply", "--only", "credentials")
    again = rig.invoke("migrate", "--apply", "--only", "credentials")
    assert "written: 0" in again.output and "unchanged=2" in again.output
    rig.write(".env", f"DEMO_USER=Qv7-synth-new-9\nDEMO_PASS={PASS_VALUE}\n")
    done = rig.invoke("migrate", "--apply", "--only", "credentials")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output
    assert _secret_docs(rig)["DEMO_USER"]["value"] == USER_VALUE


def test_a_dry_run_with_credentials_opens_no_connection(rig: Rig) -> None:
    seed_state(rig)
    done = rig.invoke("migrate", "--only", "credentials")
    assert done.exit_code == 0 and rig.opened == 0 and "to_insert=2" in done.output


def test_pairs_are_filtered_to_declared_keys_before_anything_else(rig: Rig) -> None:
    seed_state(rig)
    pairs, dropped = mc.credential_pairs(rig.root, None)
    assert sorted((s, k) for s, k, _ in pairs) == [("demo", "DEMO_PASS"), ("demo", "DEMO_USER")]
    assert dropped == 1

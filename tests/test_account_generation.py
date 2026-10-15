"""Stable random account identity and notification consent survive clocks, never replacement."""

import json
import re
import sqlite3

import pytest
from auth_harness import ADMIN, PASSWORD, account, gate_on, login

from autotester.auth import accounts, db
from autotester.schema.delivery import NotificationPref
from autotester.store.filestore import read_json, write_json
from autotester.store.notification_prefs import load_notification_pref, save_notification_pref

FIXED_CLOCK = "2026-10-15T12:00:00+00:00"


def test_fixed_clock_id_replacement_cannot_inherit_opt_in(tmp_path, monkeypatch):
    root = gate_on(tmp_path, monkeypatch)
    monkeypatch.setattr(db, "now_iso", lambda: FIXED_CLOCK)
    account(ADMIN)
    old_id = account("old@team.test")
    old = accounts.get_user(old_id)
    assert re.fullmatch(r"[0-9a-f]{32}", old.generation)
    save_notification_pref(old_id, True)
    old_pref = load_notification_pref(old_id)
    assert old_pref.account_generation == old.generation and old_pref.email_run_reports
    accounts.delete_user(old_id)
    new_id = account("replacement@team.test", "developer")
    new = accounts.get_user(new_id)
    assert new_id == old_id and new.created_at == old.created_at
    assert new.generation != old.generation
    assert not load_notification_pref(new_id).email_run_reports
    person = login(new.email)
    assert " checked" not in person.get("/profile").text
    response = person.post("/profile", data={"email_run_reports": "on",
                                            "account_generation": old.generation,
                                            "user_id": "1", "email": ADMIN})
    assert response.status_code == 303
    pref = load_notification_pref(new_id)
    assert pref.email_run_reports and pref.account_generation == new.generation
    path = root / ".work" / "notification_prefs" / f"{new_id}.json"
    write_json(path, old_pref)
    assert not load_notification_pref(new_id).email_run_reports


def test_generation_is_persistent_immutable_and_not_a_password_identity(tmp_path, monkeypatch):
    gate_on(tmp_path, monkeypatch)
    first_id = account(ADMIN)
    first = accounts.get_user(first_id)
    save_notification_pref(first_id, True)
    accounts.set_display_name(first_id, "New display name")
    accounts.reset_password(first_id, "another-correct-horse-password")
    reset, created = accounts.bootstrap_admin(ADMIN, PASSWORD)
    assert not created and reset.generation == first.generation
    assert accounts.authenticate(ADMIN, PASSWORD).generation == first.generation
    assert load_notification_pref(first_id).email_run_reports
    db._READY.discard(db.auth_db_path())
    assert accounts.get_user(first_id).generation == first.generation
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), db.transaction() as conn:
        conn.execute("UPDATE users SET generation = ? WHERE id = ?", ("a" * 32, first_id))
    assert accounts.get_user(first_id).generation == first.generation
    other, created = accounts.bootstrap_admin("second-admin@team.test", PASSWORD)
    assert created and other.generation != first.generation
    assert re.fullmatch(r"[0-9a-f]{32}", other.generation)


def test_legacy_database_gets_one_generation_without_rewriting_identity(tmp_path, monkeypatch):
    root = gate_on(tmp_path, monkeypatch)
    path = db.auth_db_path()
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, display_name TEXT NOT NULL DEFAULT '',
            disabled INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""")
        conn.execute("INSERT INTO users (email,password_hash,created_at) VALUES (?,?,?)",
                     ("legacy@team.test", "fixture-only-hash", FIXED_CLOCK))
    pref_path = root / ".work" / "notification_prefs" / "1.json"
    pref_path.parent.mkdir(parents=True)
    pref_path.write_text('{"user_id":"1","email_run_reports":true}')
    legacy = accounts.get_user(1)
    assert legacy.email == "legacy@team.test" and legacy.created_at.isoformat() == FIXED_CLOCK
    assert re.fullmatch(r"[0-9a-f]{32}", legacy.generation)
    assert not load_notification_pref(1).email_run_reports
    db._READY.discard(path)
    assert accounts.get_user(1).generation == legacy.generation
    with db.reading() as conn:
        assert conn.execute("SELECT password_hash FROM users").fetchone()[0] == "fixture-only-hash"
    save_notification_pref(1, True)
    assert load_notification_pref(1).account_generation == legacy.generation


@pytest.mark.parametrize("binding", [None, "b" * 32, "not-a-generation"])
def test_unbound_or_invalid_preference_never_opts_in(tmp_path, monkeypatch, binding):
    root = gate_on(tmp_path, monkeypatch)
    user_id = account(ADMIN)
    path = root / ".work" / "notification_prefs" / f"{user_id}.json"
    path.parent.mkdir(parents=True)
    raw = {"user_id": str(user_id), "email_run_reports": True}
    if binding is not None:
        raw["account_generation"] = binding
    path.write_text(json.dumps(raw))
    assert not load_notification_pref(user_id).email_run_reports
    save_notification_pref(user_id, True)
    saved = read_json(path, NotificationPref)
    assert saved.account_generation == accounts.get_user(user_id).generation
    assert load_notification_pref(user_id).email_run_reports


def test_missing_account_store_is_not_created_by_preference_read_or_write(tmp_path, monkeypatch):
    root = gate_on(tmp_path, monkeypatch)
    assert not load_notification_pref(1).email_run_reports
    with pytest.raises(ValueError, match="account identity"):
        save_notification_pref(1, True)
    assert not db.auth_db_path().exists()
    assert not (root / ".work" / "notification_prefs").exists()


def test_profile_account_disappearing_during_save_has_safe_response(tmp_path, monkeypatch):
    gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    person = login(ADMIN)
    from autotester.ui import routes_profile

    def disappeared(*_):
        raise ValueError("private diagnostic must not escape")

    monkeypatch.setattr(routes_profile, "save_notification_pref", disappeared)
    response = person.post("/profile", data={"email_run_reports": "on"})
    assert response.status_code == 409
    assert "private diagnostic" not in response.text

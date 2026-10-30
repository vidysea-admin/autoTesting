"""mongo-store U12: the browser session store -- plain `storage_state` documents in
`browser_sessions`, scoped in and out, restore-safe (M38, M39; D-123: no encryption).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from credential_store_support import CredRig, make_rig
from session_store_support import (
    BLOB_LEAF,
    EVIL,
    NOW,
    PARENT,
    PROJECT,
    SID,
    TOK,
    cookie,
    docs,
    elsewhere,
    make_session,
    sample,
)

from autotester.browser import profiles
from autotester.browser.profiles import (
    MAIN_ACCOUNT,
    SessionRefused,
    capture_session,
    forget_session,
    load_session,
    restore_session,
    save_session,
    scope_state,
    session_id,
)
from autotester.schema.project import Project
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN
from autotester.ui.env_editor import drop_credentials


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[CredRig]:
    with make_rig(tmp_path, monkeypatch).live() as live:
        yield live


# ---- M38: plain, in one collection, scoped on the way in ------------------------------------


def test_an_exported_state_is_stored_plain_scoped_and_nowhere_else(rig: CredRig) -> None:
    session = make_session(rig.root)
    assert capture_session(session, PROJECT, "t1")
    [doc] = docs(rig)
    assert (doc["_id"], doc["p"]) == ("pl|t1", "pl") and set(doc) == {
        "_id", "p", "state", "saved_at", "expires_at", "hosts"}
    assert doc["hosts"] == ["app.pl.test"]
    dumped = json.dumps(doc["state"])
    assert SID in dumped and TOK in dumped  # plain: D-123
    assert not {EVIL, PARENT} & {c["value"] for c in doc["state"]["cookies"]}
    assert EVIL not in dumped and PARENT not in dumped
    assert [o["origin"] for o in doc["state"]["origins"]] == ["https://app.pl.test"]
    for secret in (SID, TOK, BLOB_LEAF):
        assert secret not in elsewhere(rig)
    assert not list(rig.root.rglob("*.json")) and not (rig.root / ".env").exists()


def test_scope_uses_the_projects_allowed_domains_and_fails_closed() -> None:
    state = {"cookies": [cookie("a", "v" * 9, "app.pl.test"), cookie("b", "v" * 9, ".app.pl.test."),
                         cookie("c", "v" * 9, "pl.test"), cookie("d", "v" * 9, "xapp.pl.test"),
                         cookie("e", "v" * 9, ""), "junk", {"value": "x"}],
             "origins": [{"origin": "https://app.pl.test:8443"}, {"origin": "https://pl.test"},
                         {"origin": "https://app.pl.test\\@evil.example"}, {"origin": ""}, 5]}
    kept = scope_state(state, PROJECT)
    assert [c["name"] for c in kept["cookies"]] == ["a", "b"]
    assert [o["origin"] for o in kept["origins"]] == ["https://app.pl.test:8443"]


def test_an_expired_cookie_is_dropped_and_the_age_is_capped(rig: CredRig) -> None:
    state = {"cookies": [cookie("old", SID, expires=NOW - 1), cookie("live", TOK, expires=NOW + 60),
                         cookie("sess", BLOB_LEAF, expires=-1)], "origins": []}
    kept = save_session(PROJECT, "t1", state, now=NOW)
    assert [c["name"] for c in kept["cookies"]] == ["live", "sess"]
    assert docs(rig)[0]["expires_at"] == NOW + 60  # the earliest unexpired cookie
    save_session(PROJECT, "t1", {"cookies": [cookie("far", SID, expires=NOW + 9e9)],
                                 "origins": []}, now=NOW)
    assert docs(rig)[0]["expires_at"] == NOW + profiles.MAX_AGE_S


def test_a_state_with_nothing_in_scope_stores_nothing_and_drops_the_old_one(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    assert save_session(PROJECT, "t1", {"cookies": [cookie("e", EVIL, "evil.example")],
                                        "origins": []}, now=NOW) is None
    assert docs(rig) == []


@pytest.mark.parametrize("slug,account", [("a|b", "t1"), ("pl", "t|1"), ("", "t1"), ("pl", "")])
def test_an_ambiguous_session_id_is_refused(slug: str, account: str) -> None:
    with pytest.raises(SessionRefused):
        session_id(slug, account)


# ---- M38/M39: scoped on the way out, restore refusals ---------------------------------------


def test_a_restore_re_scopes_what_the_store_holds(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample())
    doc = docs(rig)[0]  # an old document, written under wider domains, is re-scoped on the way out
    doc["state"]["cookies"].append(cookie("e", EVIL, "evil.example"))
    doc["state"]["origins"].append({"origin": "https://evil.example",
                                    "localStorage": [{"name": "t", "value": EVIL}]})
    session = make_session(rig.root, state={"cookies": [], "origins": []})
    assert restore_session(session, PROJECT, "t1") is True
    ctx = session._context
    assert SID in json.dumps(ctx.cookies)
    assert EVIL not in json.dumps(ctx.cookies) and all(EVIL not in x for x in ctx.scripts)


def test_a_restore_adds_cookies_and_a_scoped_local_storage_script(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample())
    session = make_session(rig.root, state={"cookies": [], "origins": []})
    assert restore_session(session, PROJECT, "t1") is True
    ctx = session._context
    assert [c["name"] for c in ctx.cookies] == ["sid", "lang"]
    [script] = ctx.scripts
    assert "location.origin" in script and TOK in script and "getItem(k) === null" in script
    assert "evil.example" not in script and "m[location.origin]" in script


def test_an_expired_state_is_deleted_and_never_restored(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    assert load_session(PROJECT, "t1", now=NOW + profiles.MAX_AGE_S + 1) is None
    assert docs(rig) == []
    save_session(PROJECT, "t1", sample(), now=NOW)
    docs(rig)[0]["expires_at"] = "soon"  # unreadable expiry reads as expired
    assert load_session(PROJECT, "t1", now=NOW) is None and docs(rig) == []


def test_a_foreign_document_is_ignored_not_used_not_deleted_not_overwritten(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    docs(rig)[0]["p"] = "other"
    assert load_session(PROJECT, "t1", now=NOW) is None
    assert len(docs(rig)) == 1  # not ours to delete
    with pytest.raises(SessionRefused):
        save_session(PROJECT, "t1", sample(), now=NOW)
    assert not forget_session(PROJECT, "t1") and len(docs(rig)) == 1


def test_one_accounts_state_never_reaches_another_account(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    other = make_session(rig.root, "pl-role-t2", {"cookies": [], "origins": []})
    assert load_session(PROJECT, "t2", now=NOW) is None
    assert restore_session(other, PROJECT, "t2") is False
    assert other._context.cookies == [] and other._context.scripts == []


def test_an_entry_run_never_restores_a_login(rig: CredRig) -> None:
    fresh = {"cookies": [cookie("sid", SID, expires=-1)], "origins": []}
    save_session(PROJECT, MAIN_ACCOUNT, fresh)
    entry = make_session(rig.root, "pl-entry-test", fresh)
    assert restore_session(entry, PROJECT, MAIN_ACCOUNT) is False
    assert entry._context.cookies == [] and entry._context.scripts == []
    shared = make_session(rig.root, "pl", fresh)
    assert restore_session(shared, PROJECT, MAIN_ACCOUNT) is True


def test_a_logout_removes_the_state_so_nothing_restores_it(rig: CredRig) -> None:
    save_session(PROJECT, "t1", {"cookies": [cookie("sid", SID, expires=-1)], "origins": []})
    assert forget_session(PROJECT, "t1") is True
    assert restore_session(make_session(rig.root), PROJECT, "t1") is False


def test_removing_a_project_removes_its_sessions_only(rig: CredRig) -> None:
    fresh = {"cookies": [cookie("sid", SID, expires=-1)], "origins": []}
    save_session(PROJECT, "t1", fresh)
    other = Project(slug="zz", name="zz", base_url="https://app.pl.test",
                    allowed_domains=["app.pl.test"])
    save_session(other, "t1", fresh)
    drop_credentials("pl")
    assert [d["_id"] for d in docs(rig)] == ["zz|t1"]




def test_the_project_level_account_id_cannot_collide_with_a_role_account() -> None:
    assert not re.match(ROLE_ACCOUNT_ID_PATTERN, MAIN_ACCOUNT)

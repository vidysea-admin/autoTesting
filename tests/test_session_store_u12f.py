"""mongo-store U12f: the U12 dual-check warnings A-W1, B-W1, W2, W3, W4 (M38-M40). Fake Mongo only,
synthetic values. Each test names the warning it closes. W5 (a restore may overwrite fresher
cookies) and W6 (the orchestrate path does not restore) are deliberately left open.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from auth_harness import gate_on, team
from credential_store_support import CredRig, make_rig
from fake_mongo import seams
from session_store_support import (
    NOW,
    PROJECT,
    SID,
    Ctx,
    RoleFake,
    cookie,
    docs,
    sample,
)

from autotester.browser import profiles
from autotester.browser.profiles import (
    MAIN_ACCOUNT,
    MAX_AGE_S,
    load_session,
    save_session,
)
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.project import SecretRef
from autotester.schema.role_signin import RoleSignIn
from autotester.stages import manual_login as manual_login_mod
from autotester.stages import role_session_port
from autotester.stages.multi_role_session import RoleSessions
from autotester.stages.role_session_port import LiveRolePort, RoleLoginFailed
from autotester.store import mongo_backend
from autotester.store.mongo_routes import repo_redactor
from autotester.store.project_store import ProjectStore
from autotester.ui import run_execution

OLD = "Zk9-previous-good-session-F6"


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[CredRig]:
    root = gate_on(tmp_path, monkeypatch)
    live = make_rig(tmp_path, monkeypatch)
    assert live.root == root
    with live.live() as armed:
        yield armed


# ---- A-W1: a session save reuses the one client and still rebuilds the secret gate ------------


def test_session_saves_reuse_one_client_and_the_gate_still_rebuilds(rig: CredRig) -> None:
    clients: list[int] = []
    with seams(client_factory=lambda _uri: clients.append(1) or rig.server.client()):
        mongo_backend.reset_default_backend()
        save_session(PROJECT, "t1", sample(), now=NOW)
        save_session(PROJECT, "t2", sample(), now=NOW)
        mongo_backend.default_backend().put("projects/p/x.json", "{}")  # the gate is built now
        later = {"cookies": [cookie("sid", OLD)], "origins": []}
        save_session(PROJECT, "t1", later, now=NOW)
        assert len(clients) == 1
        with pytest.raises(mongo_backend.routes.StoreSecretRefused):  # the NEW value is known
            mongo_backend.default_backend().put("projects/p/x.json", f'{{"n": "{OLD}"}}')


# ---- B-W1: the two call sites that had no test ---------------------------------------------------


def _manual(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def start(self: BrowserSession) -> BrowserSession:
        self._context = Ctx(sample())
        return self

    monkeypatch.setattr(BrowserSession, "start", start)
    monkeypatch.setattr(BrowserSession, "goto", lambda self, url: None)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    manual_login_mod.manual_login(PROJECT, ProjectPaths(PROJECT.slug, tmp_path),
                                  wait_for_human=lambda _prompt: None)


def test_a_manual_login_is_saved_under_the_project_account(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    _manual(monkeypatch, rig.root)
    assert [d["_id"] for d in docs(rig)] == [f"pl|{MAIN_ACCOUNT}"]
    stored = load_session(PROJECT, MAIN_ACCOUNT)
    assert stored is not None and [c["value"] for c in stored["cookies"]] == [SID, "en"]


def _normal_run(root: Path, monkeypatch: pytest.MonkeyPatch, slug: str = "pl") -> Ctx:
    made: list[Ctx] = []

    class Fake:
        def __init__(self, *_a: Any, **_kw: Any) -> None:
            self._context = Ctx({"cookies": [], "origins": []})
            self.paths, self.secrets = ProjectPaths(slug, root), SecretStore(PROJECT, {})
            made.append(self._context)

        def close(self) -> None:
            return None

    monkeypatch.setattr(run_execution, "BrowserSession", Fake)
    monkeypatch.setattr(run_execution, "_start_session", lambda *_a, **_kw: None)
    pool = SimpleNamespace(lend=lambda: None, close=lambda: None)
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    run_execution._run_normal_cases([], pool, PROJECT, SimpleNamespace(), root, SimpleNamespace(),
                                    SimpleNamespace(trace=None), "r1", SimpleNamespace(),
                                    budget=budget)
    return made[0]


def test_a_normal_run_restores_the_project_account_login(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    save_session(PROJECT, MAIN_ACCOUNT, sample(), now=NOW)
    save_session(PROJECT, "t1", {"cookies": [cookie("sid", OLD)], "origins": []}, now=NOW)
    ctx = _normal_run(rig.root, monkeypatch)
    assert [c["value"] for c in ctx.cookies] == [SID, "en"]  # the project login, not t1's


# ---- W2: the sign-in state is saved only after the signed-in proof ----------------------------


def _port(rig: CredRig, monkeypatch: pytest.MonkeyPatch, proven: bool) -> LiveRolePort:
    RoleFake.made.clear()
    monkeypatch.setattr(role_session_port.ResponseLog, "attach", lambda self, session: None)
    monkeypatch.setattr(role_session_port.role_probe, "appears", lambda session, target: proven)
    roles = RoleSessions(PROJECT, SecretStore(PROJECT, {}), rig.root / "runs",
                         paths_root=rig.root, session_cls=RoleFake)
    sign_in = RoleSignIn(platform_id="web", login_url="https://app.pl.test/login",
                         user_locator="#u", password_locator="#p", submit_locator="#s",
                         signed_in_target="#me")
    return LiveRolePort(roles.open(), [sign_in])


def test_a_failed_login_never_replaces_a_good_stored_session(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    save_session(PROJECT, "t1", {"cookies": [cookie("sid", OLD)], "origins": []}, now=NOW)
    held = repr(docs(rig))
    port = _port(rig, monkeypatch, proven=False)
    try:
        with pytest.raises(RoleLoginFailed):
            port.login("t1")
    finally:
        port.roles.close()
    assert repr(docs(rig)) == held and SID not in held


def test_a_proven_login_is_saved(rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    port = _port(rig, monkeypatch, proven=True)
    try:
        port.login("t1")
    finally:
        port.roles.close()
    stored = load_session(PROJECT, "t1")
    assert stored is not None and SID in [c["value"] for c in stored["cookies"]]


# ---- W3: a bad stored document is deleted, never raised, and the age cap holds on load --------


def test_a_malformed_stored_state_is_deleted_not_raised(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    docs(rig)[0]["state"]["cookies"] = 5
    assert load_session(PROJECT, "t1", now=NOW) is None
    assert docs(rig) == []


def test_a_bad_stored_item_never_breaks_the_run_wide_redactor(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    save_session(PROJECT, "t2", sample(), now=NOW)
    first = next(d for d in docs(rig) if d["_id"] == "pl|t1")
    first["state"]["origins"] = [
        {"origin": "https://app.pl.test", "localStorage": [5, {"name": 1}]}]
    first["state"]["cookies"] = [7, {"value": None}, {"name": "x"}]
    assert SID not in repo_redactor().scrub(f"x {SID}")  # the healthy document is still masked
    assert profiles.session_values({"cookies": 5, "origins": [{"localStorage": 5}, 9]}) == {}


def test_a_stored_localstorage_shape_error_does_not_stop_a_restore(rig: CredRig) -> None:
    save_session(PROJECT, "t1", sample(), now=NOW)
    docs(rig)[0]["state"]["origins"] = [
        {"origin": "https://app.pl.test", "localStorage": [5, {"name": "k", "value": "v"}]},
        {"origin": "https://app.pl.test", "localStorage": 5}]
    state = load_session(PROJECT, "t1", now=NOW)
    assert state is not None
    assert state["origins"][0]["localStorage"] == [{"name": "k", "value": "v"}]


def test_a_tampered_far_future_expiry_is_not_trusted_on_load(rig: CredRig) -> None:
    live = {"cookies": [cookie("sid", SID, expires=-1)], "origins": []}
    save_session(PROJECT, "t1", live, now=NOW)
    docs(rig)[0]["expires_at"] = NOW + 10 * 365 * 24 * 3600
    assert load_session(PROJECT, "t1", now=NOW + MAX_AGE_S - 60) is not None
    assert load_session(PROJECT, "t1", now=NOW + MAX_AGE_S + 60) is None
    assert docs(rig) == []


def test_a_save_time_in_the_future_is_not_a_login(rig: CredRig) -> None:
    live = {"cookies": [cookie("sid", SID, expires=-1)], "origins": []}
    save_session(PROJECT, "t1", live, now=NOW)
    docs(rig)[0]["saved_at"] = NOW + 30 * 24 * 3600
    docs(rig)[0]["expires_at"] = NOW + 60 * 24 * 3600
    assert load_session(PROJECT, "t1", now=NOW) is None and docs(rig) == []


# ---- W4: forget_session has a caller: undeclaring a role account's credential key -------------


def test_undeclaring_a_role_credential_key_forgets_that_accounts_login(rig: CredRig) -> None:
    keys = ["T1_U", "T1_P", "T2_U", "T2_P"]
    ProjectStore("pl", rig.root).save_project(PROJECT.model_copy(update={
        "secrets": [SecretRef(key=k, domains=["app.pl.test"]) for k in keys]}))
    save_session(PROJECT, "t1", sample(), now=NOW)
    save_session(PROJECT, "t2", sample(), now=NOW)
    save_session(PROJECT, MAIN_ACCOUNT, sample(), now=NOW)
    resp = team()["admin"].post("/projects/pl/secrets/T1_P/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert sorted(d["_id"] for d in docs(rig)) == ["pl|_project", "pl|t2"]

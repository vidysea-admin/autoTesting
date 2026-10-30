"""mongo-store U11 over HTTP: the UI write paths reach the credential store through the door, and
only through it (M31, M32, M35, M37). Fake Mongo; every value is synthetic.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_harness import gate_on, team
from credential_store_support import OTHER, VALUE, CredRig, make_rig

from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui.env_editor import put_credentials

MARK = "Qv7-synthetic-"


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[CredRig]:
    root = gate_on(tmp_path, monkeypatch)
    live = make_rig(tmp_path, monkeypatch)
    assert live.root == root
    with live.live() as armed:
        yield armed


def _declared(root: Path, slug: str = "pl", *keys: str) -> ProjectStore:
    store = ProjectStore(slug, root)
    store.save_project(Project(
        slug=slug, name=slug, base_url=f"https://{slug}.test", allowed_domains=[f"{slug}.test"],
        secrets=[SecretRef(key=k, domains=[f"{slug}.test"]) for k in keys]))
    return store


def _roles_form(slug: str = "northwind") -> dict[str, list[str] | str]:
    return {"slug": slug, "name": slug.title(), "platform_id": ["p1"], "platform_name": ["App"],
            "platform_base_url": ["https://app.nw.test/"], "platform_domains": ["app.nw.test"],
            "platform_subdomains": ["yes"], "account_id": ["a0", "a1"],
            "account_role": ["Parent", "Principal"], "account_platform": ["p1", "p1"],
            "account_tenant": ["t0", "t0"], "account_scope": ["", ""],
            "account_user_key": ["NORTHWIND_A0_USER", "NORTHWIND_A1_USER"],
            "account_user_value": [f"{MARK}u0", f"{MARK}u1"],
            "account_pass_key": ["NORTHWIND_A0_PASS", "NORTHWIND_A1_PASS"],
            "account_pass_value": [f"{MARK}p0", f"{MARK}p1"]}


def test_role_onboarding_puts_every_login_in_the_store_and_none_in_env(rig: CredRig) -> None:
    resp = team()["dev"].post("/onboard/roles", data=_roles_form())
    assert resp.status_code == 303, resp.text[:300]
    docs = {d["_id"]: d for d in rig.secrets()}
    assert set(docs) == {f"NORTHWIND_A{i}_{kind}" for i in (0, 1) for kind in ("USER", "PASS")}
    assert {d["p"] for d in docs.values()} == {"northwind"}
    assert docs["NORTHWIND_A1_PASS"]["value"] == f"{MARK}p1"
    assert not (rig.root / ".env").exists()  # M35: the value never reached the repo `.env`
    assert MARK not in resp.text and MARK not in str(ProjectStore("northwind", rig.root)
                                                     .load_project())


def test_a_failed_commit_puts_the_previous_stored_documents_back(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = team()["dev"]
    assert dev.post("/onboard/roles", data=_roles_form()).status_code == 303
    before, calls = list(rig.secrets()), {"n": 0}

    def boom(self: ProjectStore, project: Project) -> None:
        calls["n"] += 1
        raise RuntimeError("disk full")

    monkeypatch.setattr(ProjectStore, "save_project", boom)
    changed = _roles_form() | {"account_pass_value": [f"{MARK}new0", f"{MARK}new1"]}
    with pytest.raises(RuntimeError):  # the route restores, then re-raises
        dev.post("/projects/northwind/accounts", data=changed)
    assert calls["n"] >= 1  # the project write was attempted after the credential write
    assert rig.secrets() == before  # the old documents, unchanged: M37 snapshot-restore
    assert MARK + "new0" not in rig.everywhere()
    assert not (rig.root / ".env").exists()


def test_the_credential_editor_saves_to_the_store_and_the_page_shows_set(rig: CredRig) -> None:
    _declared(rig.root, "pl", "PL_PASS")
    clients = team()
    admin = clients["admin"]
    assert admin.post("/projects/pl/env", data={"key": "PL_PASS", "value": VALUE},
                      follow_redirects=False).status_code == 303
    [doc] = rig.secrets()
    assert (doc["_id"], doc["p"], doc["value"]) == ("PL_PASS", "pl", VALUE)
    assert not (rig.root / ".env").exists()
    assert "PL_PASS" in admin.get("/projects/pl/env").text
    for name in ("dev", "tester"):  # a viewer without credentials.view never gets the value
        assert VALUE not in clients[name].get("/projects/pl/env").text


def test_adding_a_custom_credential_declares_it_and_stores_its_value(rig: CredRig) -> None:
    _declared(rig.root, "pl")
    resp = team()["admin"].post("/projects/pl/env/add", follow_redirects=False, data={
        "key": "PL_TOKEN", "value": VALUE, "domains": "pl.test", "description": "t"})
    assert resp.status_code == 303
    assert [(d["_id"], d["p"]) for d in rig.secrets()] == [("PL_TOKEN", "pl")]
    assert not (rig.root / ".env").exists()


def test_a_deployment_key_is_refused_with_a_400_and_nothing_is_stored(rig: CredRig) -> None:
    _declared(rig.root, "pl", "AUTOTESTER_APPROVAL_KEY")
    resp = team()["admin"].post("/projects/pl/env", follow_redirects=False,
                                data={"key": "AUTOTESTER_APPROVAL_KEY", "value": OTHER})
    assert resp.status_code in (400, 403) and OTHER not in resp.text
    assert rig.secrets() == []


def test_a_store_outage_on_save_is_a_503_and_no_file_is_written(rig: CredRig) -> None:
    _declared(rig.root, "pl", "PL_PASS")
    admin = team()["admin"]
    admin.post("/projects/pl/env", data={"key": "PL_PASS", "value": VALUE})
    rig.server.down = True
    resp = admin.post("/projects/pl/env", data={"key": "PL_PASS", "value": OTHER})
    assert resp.status_code == 503 and OTHER not in resp.text and VALUE not in resp.text
    assert not (rig.root / ".env").exists()
    rig.server.down = False
    assert [d["value"] for d in rig.secrets()] == [VALUE]


def test_removing_a_declaration_deletes_its_stored_value(rig: CredRig) -> None:
    store = _declared(rig.root, "pl", "PL_USER", "PL_PASS")
    put_credentials("pl", {"PL_USER": OTHER, "PL_PASS": VALUE})
    resp = team()["admin"].post("/projects/pl/secrets/PL_PASS/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert [d["_id"] for d in rig.secrets()] == ["PL_USER"]  # M37: the value went with the key
    loaded = store.load_project()
    assert loaded is not None and [s.key for s in loaded.secrets] == ["PL_USER"]


def test_onboarding_with_a_credential_row_stores_it_in_the_store(rig: CredRig) -> None:
    data = {"slug": "pl", "name": "Pl", "base_url": "https://pl.test/signin",
            "allowed_domains": "pl.test", "credential_key": "PL_PASS", "credential_value": VALUE,
            "credential_domains": "pl.test", "credential_description": "login"}
    assert team()["admin"].post("/onboard", data=data, follow_redirects=False).status_code == 303
    assert [(d["_id"], d["p"]) for d in rig.secrets()] == [("PL_PASS", "pl")]
    assert not (rig.root / ".env").exists()


def test_onboarding_refuses_a_key_the_store_already_holds(rig: CredRig) -> None:
    put_credentials("ghost", {"PL_GHOST": VALUE})  # held by no declared project
    data = {"slug": "pl", "name": "Pl", "base_url": "https://pl.test/signin",
            "allowed_domains": "pl.test", "credential_key": "PL_GHOST", "credential_value": OTHER,
            "credential_domains": "pl.test", "credential_description": "login"}
    resp = team()["admin"].post("/onboard", data=data, follow_redirects=False)
    assert resp.status_code == 400 and OTHER not in resp.text and VALUE not in resp.text
    assert [(d["value"], d["p"]) for d in rig.secrets()] == [(VALUE, "ghost")]


def test_role_onboarding_refuses_a_key_the_store_already_holds(rig: CredRig) -> None:
    put_credentials("someone-else", {"NORTHWIND_A0_PASS": VALUE})
    resp = team()["dev"].post("/onboard/roles", data=_roles_form())
    assert resp.status_code == 400 and VALUE not in resp.text
    assert [(d["_id"], d["p"], d["value"]) for d in rig.secrets()] == [
        ("NORTHWIND_A0_PASS", "someone-else", VALUE)]  # nothing overwritten, nothing added
    assert ProjectStore("northwind", rig.root).load_project() is None

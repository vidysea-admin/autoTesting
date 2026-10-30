"""mongo-store U11f: the U11 dual-check follow-ups (M31-M37, M34). Fake Mongo only; every value is
synthetic. Each test names the warning it closes: the door's own shape check, the undeclare order,
the two redaction sites that had no test, one client for credential writes, and `blob_store()`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from auth_harness import gate_on, team
from credential_store_support import OTHER, URI, VALUE, CredRig, make_rig
from fake_mongo import seams

from autotester.core.env import is_server_key, stored_secret_values
from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider, _env_secret_values
from autotester.schema.document import DocumentPage, DocumentReading
from autotester.schema.project import Project, SecretRef
from autotester.sources.adapters import _sanitize_pdf_reading
from autotester.sources.extract import Extraction
from autotester.store import mongo_backend, run_store
from autotester.store.blobs import MongoBlobStore
from autotester.store.mongo_backend import MongoBackend
from autotester.store.project_store import ProjectStore
from autotester.ui.env_editor import (
    CredentialRefused,
    InvalidEnvValue,
    put_credentials,
    restore_credentials,
    save_credentials,
    snapshot_credentials,
    validate_env_values,
)


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[CredRig]:
    root = gate_on(tmp_path, monkeypatch)
    live = make_rig(tmp_path, monkeypatch)
    assert live.root == root
    with live.live() as armed:
        yield armed


def _declared(root: Path, slug: str, *keys: str) -> ProjectStore:
    store = ProjectStore(slug, root)
    store.save_project(Project(
        slug=slug, name=slug, base_url=f"https://{slug}.test", allowed_domains=[f"{slug}.test"],
        secrets=[SecretRef(key=k, domains=[f"{slug}.test"]) for k in keys]))
    return store


# ---- (1) the door runs the shape check itself, and refuses server keys in any case -------------


@pytest.mark.parametrize("key", ["autotester_approval_key", "Autotester_Harness_Password",
                                 "anthropic_api_key", "Gemini_Api_Key"])
def test_a_server_key_is_a_server_key_in_any_letter_case(key: str) -> None:
    assert is_server_key(key)


@pytest.mark.parametrize("key", ["autotester_approval_key", "Autotester_Approval_Key",
                                 "openai_api_key"])
def test_the_door_refuses_a_server_key_in_any_letter_case(rig: CredRig, key: str) -> None:
    with pytest.raises(InvalidEnvValue) as caught:  # a lowercase key fails the shape check first
        put_credentials("pl", {"PL_OK": VALUE, key: OTHER})
    assert rig.secrets() == [] and OTHER not in str(caught.value)


BAD_PAIRS = [
    pytest.param("pl_pass", VALUE, id="lowercase-key"), pytest.param("PL PASS", VALUE, id="space"),
    pytest.param("1PL", VALUE, id="digit-first"), pytest.param("PL-PASS", VALUE, id="dash"),
    pytest.param("", VALUE, id="empty-key"),
    pytest.param("PL_PASS", f"{VALUE}\nINJECT=1", id="newline"),
    pytest.param("PL_PASS", f"{VALUE}\rX", id="carriage-return"),
    pytest.param("PL_PASS", f"{VALUE}\x00", id="nul"),
    pytest.param("PL_PASS", f"{VALUE}\x07", id="bell"),
    pytest.param("PL_PASS", f"{VALUE}\x7f", id="delete"),
    pytest.param("PL_PASS", "", id="empty-value"),
]


@pytest.mark.parametrize("key,value", BAD_PAIRS)
def test_the_door_itself_refuses_a_malformed_pair_and_writes_nothing(
        rig: CredRig, key: str, value: str) -> None:
    before = rig.tree()
    with pytest.raises(InvalidEnvValue) as caught:
        put_credentials("pl", {"PL_GOOD": OTHER, key: value})  # the whole batch is checked first
    assert rig.secrets() == [] and rig.tree() == before
    assert VALUE not in str(caught.value) and OTHER not in str(caught.value)


@pytest.mark.parametrize("value", [URI, f"  {URI}  "])
def test_a_value_equal_to_the_mongo_uri_is_refused_under_any_key_name(
        rig: CredRig, value: str) -> None:
    with pytest.raises(CredentialRefused) as caught:
        put_credentials("pl", {"PL_NOTES": value})
    assert rig.secrets() == [] and "db.example" not in str(caught.value)
    with pytest.raises(CredentialRefused):
        save_credentials("pl", rig.root / ".env", {"PL_NOTES": value})
    assert rig.secrets() == [] and not (rig.root / ".env").exists()


def test_the_validation_only_gate_agrees_with_the_door(rig: CredRig) -> None:
    """An intake that validates first never passes a batch the door then refuses."""
    for bad in ({"autotester_approval_key": VALUE}, {"PL_PASS": f"{VALUE}\x07"},
                {"PL_NOTES": URI}, {"PL_PASS": ""}):
        with pytest.raises(InvalidEnvValue):
            validate_env_values(bad)
    validate_env_values({"PL_PASS": VALUE, "PL_USER": OTHER})


# ---- (2) undeclare: the store first, so an outage orphans nothing --------------------------------


def test_a_store_outage_on_undeclare_is_a_503_and_nothing_changed(rig: CredRig) -> None:
    store = _declared(rig.root, "pl", "PL_PASS")
    put_credentials("pl", {"PL_PASS": VALUE})
    rig.server.down = True
    resp = team()["admin"].post("/projects/pl/secrets/PL_PASS/delete", follow_redirects=False)
    assert resp.status_code == 503 and VALUE not in resp.text
    rig.server.down = False
    loaded = store.load_project()  # the 503 is truthful: the declaration is still there
    assert loaded is not None and [s.key for s in loaded.secrets] == ["PL_PASS"]
    assert [d["value"] for d in rig.secrets()] == [VALUE]


def test_a_failed_project_save_on_undeclare_puts_the_stored_value_back(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    _declared(rig.root, "pl", "PL_PASS")
    put_credentials("pl", {"PL_PASS": VALUE})

    def boom(self: ProjectStore, project: Project) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(ProjectStore, "save_project", boom)
    with pytest.raises(OSError):
        team()["admin"].post("/projects/pl/secrets/PL_PASS/delete")
    assert [(d["_id"], d["value"]) for d in rig.secrets()] == [("PL_PASS", VALUE)]


def test_redeclaring_an_undeclared_key_does_not_revive_the_old_value(rig: CredRig) -> None:
    _declared(rig.root, "pl", "PL_PASS")
    put_credentials("pl", {"PL_PASS": VALUE})
    admin = team()["admin"]
    assert admin.post("/projects/pl/secrets/PL_PASS/delete").status_code == 303
    assert admin.post("/projects/pl/secrets", data={
        "key": "PL_PASS", "domains": "pl.test", "description": ""}).status_code == 303
    assert rig.secrets() == [] and stored_secret_values() == {}
    assert VALUE not in rig.everywhere()


# ---- (3) M34: the two redaction sites that were not pinned ---------------------------------------


def test_the_litellm_guard_withholds_a_value_held_only_in_the_store(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    put_credentials("pl", {"PL_PASS": VALUE})
    assert VALUE in _env_secret_values()  # no .env, no process variable: the store alone
    provider = LiteLLMProvider(model="openai/gpt-4o")
    assert VALUE in provider._secret_values()
    with pytest.raises(ProviderError) as caught:
        provider.guard_text(f"please type {VALUE} into the form")
    assert VALUE not in str(caught.value)


def test_a_pdf_reading_is_scrubbed_of_a_value_held_only_in_the_store(rig: CredRig) -> None:
    store = _declared(rig.root, "pl", "PL_PASS")
    put_credentials("pl", {"PL_PASS": VALUE})
    assert not store.paths.env_file.exists()  # the store is the only place the value lives
    page = DocumentPage(number=1, text=f"login with {VALUE} now", method="text")
    reading = DocumentReading(pages=[page])
    cleaned = _sanitize_pdf_reading(store, Extraction(f"[page 1]\n{page.text}", None, reading))
    assert VALUE not in (cleaned.text or "")
    assert cleaned.reading is not None and VALUE not in cleaned.reading.model_dump_json()


# ---- (4) one backend, one client, indexes once ---------------------------------------------------


def test_credential_writes_reuse_one_client_and_build_indexes_once(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    clients: list[Any] = []
    built: list[int] = []
    real_ensure = MongoBackend.ensure_indexes

    def counted(self: MongoBackend) -> None:
        built.append(1)
        real_ensure(self)

    monkeypatch.setattr(MongoBackend, "ensure_indexes", counted)
    with seams(client_factory=lambda _uri: clients.append(1) or rig.server.client()):
        mongo_backend.reset_default_backend()
        put_credentials("pl", {"PL_PASS": VALUE})
        put_credentials("pl", {"PL_PASS": OTHER, "PL_USER": VALUE})
        snap = snapshot_credentials(["PL_PASS"])
        restore_credentials(snap)
        stored_secret_values()
    assert len(clients) == 1 and len(built) == 1
    assert {d["_id"] for d in rig.secrets()} == {"PL_PASS", "PL_USER"}


def test_the_secret_gate_still_rebuilds_after_each_credential_write(rig: CredRig) -> None:
    mongo_backend.default_backend().put("projects/p/x.json", "{}")  # gate built and cached
    put_credentials("pl", {"PL_PASS": VALUE})
    with pytest.raises(mongo_backend.routes.StoreSecretRefused):
        mongo_backend.default_backend().put("projects/p/x.json", f'{{"n": "{VALUE}"}}')
    put_credentials("pl", {"PL_PASS": OTHER})  # changed: the next write knows the new value too
    with pytest.raises(mongo_backend.routes.StoreSecretRefused):
        mongo_backend.default_backend().put("projects/p/x.json", f'{{"n": "{OTHER}"}}')


# ---- (5) blob_store() with blobs=mongo -----------------------------------------------------------


def test_blob_store_builds_on_the_fake_with_blobs_on_mongo(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rig = make_rig(tmp_path, monkeypatch, area=False)
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "blobs=mongo")
    monkeypatch.setenv(mongo_backend.MONGO_URI_ENV, URI)
    monkeypatch.delitem(run_store._BLOBS, "mongo", raising=False)
    try:
        with seams(client_factory=lambda _uri: rig.server.client()):
            store = run_store.blob_store()
            assert isinstance(store, MongoBlobStore) and run_store.blob_store() is store
            info = store.put("runs/r1/note.txt", b"plain evidence", kind="evidence", masked=True)
            assert info is not None and store.get("runs/r1/note.txt") == b"plain evidence"
    finally:
        run_store._BLOBS.pop("mongo", None)


def test_blob_store_without_a_uri_is_a_named_selection_error(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_rig(tmp_path, monkeypatch, area=False)
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "blobs=mongo")
    monkeypatch.delitem(run_store._BLOBS, "mongo", raising=False)
    with pytest.raises(run_store.StoreSelectionError):
        run_store.blob_store()

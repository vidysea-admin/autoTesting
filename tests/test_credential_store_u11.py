"""mongo-store U11: the credential store -- plain documents, one door, store-first resolution
(M8, M31-M37, M47; D-123: no encryption, no key). Fake Mongo only; every value is synthetic.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from credential_store_support import OTHER, VALUE, CredRig, make_rig

from autotester.browser.secrets import MissingSecret, SecretStore, parse_env
from autotester.core.env import (
    MONGO_URI_ENV,
    credential_collection,
    redaction_values,
    resolve_credentials,
    stored_secret_values,
)
from autotester.schema.project import Project, SecretRef
from autotester.store.mongo_backend import default_backend
from autotester.store.mongo_guard import StoreUnavailable
from autotester.store.mongo_routes import StoreSecretRefused, repo_redactor
from autotester.ui.env_editor import (
    CredentialRefused,
    InvalidEnvValue,
    drop_credentials,
    put_credentials,
    restore_credentials,
    save_credentials,
    snapshot_credentials,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[CredRig]:
    with make_rig(tmp_path, monkeypatch).live() as live:
        yield live


def _project(slug: str = "pl", *keys: str) -> Project:
    return Project(slug=slug, name=slug, base_url="https://app.pl.test",
                   allowed_domains=["pl.test"],
                   secrets=[SecretRef(key=k, domains=["app.pl.test"]) for k in keys])


# ---- M31: plain, in `secrets`, through one door ---------------------------------------------


def test_the_door_stores_a_plain_document_in_secrets_and_nowhere_else(rig: CredRig) -> None:
    env = rig.root / ".env"
    save_credentials("pl", env, {"PL_PASS": VALUE})
    [doc] = rig.secrets()
    assert set(doc) == {"_id", "p", "value", "updated_at"}
    assert (doc["_id"], doc["p"], doc["value"]) == ("PL_PASS", "pl", VALUE)  # no cipher text
    assert rig.everywhere().count(VALUE) == 1  # not in another collection, not in GridFS
    assert not env.exists()  # M35: no second copy on the ephemeral disk


def test_only_the_door_writes_secrets_and_no_crypto_exists() -> None:
    users = {p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py")
             if "credential_collection(" in p.read_text("utf-8")}
    assert users == {"core/env.py", "ui/env_editor.py"}  # M31(b): the read side and the door
    assert 'collection("secrets")' in (SRC / "core/env.py").read_text("utf-8")
    door = (SRC / "ui/env_editor.py").read_text("utf-8")
    assert door.count(".replace_one(") == 1 and "insert_one" not in door  # `_put_doc` only
    for path in SRC.rglob("*.py"):  # M31(c) / M47
        assert not re.search(r"^\s*(import|from)\s+cryptography", path.read_text("utf-8"), re.M)
    assert not (SRC / "store" / "secret_box.py").exists()
    assert "cryptography" not in (SRC.parents[1] / "pyproject.toml").read_text("utf-8")


def test_project_b_cannot_overwrite_or_read_a_key(rig: CredRig) -> None:
    put_credentials("a", {"A_PASS": VALUE})
    put_credentials("b", {"B_PASS": OTHER})
    assert {(d["_id"], d["p"]) for d in rig.secrets()} == {("A_PASS", "a"), ("B_PASS", "b")}
    with pytest.raises(CredentialRefused):  # M31(d): b's save never takes a's key
        put_credentials("b", {"A_PASS": OTHER})
    assert stored_secret_values()["A_PASS"] == VALUE
    assert resolve_credentials({}, "b", {"A_PASS"})[0] == {}  # nor reads it under b's slug


# ---- M32: no key dependency; closed on an outage --------------------------------------------


@pytest.mark.parametrize("state", [None, "", "rotated-key"])
def test_credentials_do_not_depend_on_the_approval_key(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch, state: str | None) -> None:
    monkeypatch.setenv("AUTOTESTER_APPROVAL_KEY", "first-key")
    put_credentials("pl", {"PL_PASS": VALUE})
    if state is None:
        monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY")
    else:
        monkeypatch.setenv("AUTOTESTER_APPROVAL_KEY", state)
    assert stored_secret_values() == {"PL_PASS": VALUE}
    put_credentials("pl", {"PL_PASS": OTHER})
    assert stored_secret_values() == {"PL_PASS": OTHER}


def test_an_unreachable_store_raises_and_falls_back_to_nothing(rig: CredRig) -> None:
    put_credentials("pl", {"PL_PASS": VALUE})
    before, rig.server.down = rig.tree(), True
    with pytest.raises(StoreUnavailable):
        save_credentials("pl", rig.root / ".env", {"PL_NEW": OTHER})
    with pytest.raises(StoreUnavailable):
        SecretStore.load(_project("pl", "PL_PASS"), rig.root / ".env", strict=False)
    assert rig.tree() == before and not (rig.root / ".env").exists()
    rig.server.down = False
    assert OTHER not in rig.everywhere()


# ---- M33: scoping and resolve order ---------------------------------------------------------


def test_a_project_resolves_only_the_keys_it_declares(rig: CredRig) -> None:
    put_credentials("a", {"A_PASS": VALUE})
    put_credentials("b", {"B_PASS": OTHER})
    usable, shadow = resolve_credentials({}, "b", {"B_PASS"})
    assert usable == {"B_PASS": OTHER}
    assert resolve_credentials({}, "b", {"A_PASS", "B_PASS"})[0] == {"B_PASS": OTHER}  # not a's
    assert VALUE in shadow.values() and VALUE not in usable.values()  # masked, not resolvable
    secrets = SecretStore.load(_project("b", "B_PASS"), rig.root / ".env")
    assert secrets.resolve("{{SECRET:B_PASS}}", "https://app.pl.test/") == OTHER


def test_the_store_beats_the_process_environment_which_beats_the_file(
        rig: CredRig, monkeypatch: pytest.MonkeyPatch) -> None:
    declared = {"PL_PASS"}
    assert resolve_credentials({"PL_PASS": "file-v"}, "pl", declared)[0] == {"PL_PASS": "file-v"}
    monkeypatch.setenv("PL_PASS", "env-v")
    usable, shadow = resolve_credentials({"PL_PASS": "file-v"}, "pl", declared)
    assert usable == {"PL_PASS": "env-v"} and "file-v" in shadow.values()
    put_credentials("pl", {"PL_PASS": VALUE})
    usable, shadow = resolve_credentials({"PL_PASS": "file-v"}, "pl", declared)
    assert usable == {"PL_PASS": VALUE}
    assert {"file-v", "env-v"} <= set(shadow.values())  # every hidden value stays masked


def test_a_deleted_credential_no_longer_resolves(rig: CredRig) -> None:
    put_credentials("pl", {"PL_PASS": VALUE})
    live = SecretStore.load(_project("pl", "PL_PASS"), rig.root / ".env")
    assert live.resolve("{{SECRET:PL_PASS}}", "https://app.pl.test/") == VALUE
    drop_credentials("pl", ["PL_PASS"])
    assert resolve_credentials({}, "pl", {"PL_PASS"})[0] == {}
    with pytest.raises(MissingSecret):
        SecretStore.load(_project("pl", "PL_PASS"), rig.root / ".env")


# ---- M34 / M8: the redactor is the union and refreshes ---------------------------------------


def test_the_redactor_covers_env_and_store_values_and_refreshes_on_a_write(rig: CredRig) -> None:
    (rig.root / ".env").write_text("FILE_ONLY=file-canary-value\n", encoding="utf-8")
    put_credentials("pl", {"PL_PASS": VALUE})
    red = repo_redactor()
    assert VALUE not in red.scrub(f"trace {VALUE} exception: {VALUE}!")
    assert "file-canary-value" not in red.scrub("x file-canary-value")
    assert VALUE in redaction_values({}).values()
    put_credentials("pl", {"PL_PASS": OTHER})  # changed: the next scrub knows the new value
    assert OTHER not in repo_redactor().scrub(f"v {OTHER}")
    secrets = SecretStore.load(_project("pl", "PL_PASS"), rig.root / ".env")
    with pytest.raises(ValueError):
        secrets.guard_prompt(f"prompt carrying {OTHER}")


def test_a_stored_value_is_refused_in_every_other_document(rig: CredRig) -> None:
    default_backend().put("projects/p/x.json", "{}")  # the secret gate is built and cached now
    put_credentials("pl", {"PL_PASS": VALUE})
    with pytest.raises(StoreSecretRefused):  # ... and rebuilt after the credential write
        default_backend().put("projects/p/x.json", f'{{"note": "{VALUE}"}}')
    assert rig.everywhere().count(VALUE) == 1


# ---- M36: deployment secrets are never stored ------------------------------------------------


@pytest.mark.parametrize("key", [MONGO_URI_ENV, "AUTOTESTER_APPROVAL_KEY", "ANTHROPIC_API_KEY",
                                 "OPENAI_API_KEY", "AUTOTESTER_HARNESS_PASSWORD"])
def test_deployment_secrets_are_refused_and_the_batch_writes_nothing(
        rig: CredRig, key: str) -> None:
    with pytest.raises(CredentialRefused) as caught:
        put_credentials("pl", {"PL_OK": VALUE, key: OTHER})
    assert rig.secrets() == [] and OTHER not in str(caught.value) and VALUE not in str(caught.value)


def test_a_malformed_pair_is_refused_without_echoing_the_value(rig: CredRig) -> None:
    with pytest.raises(InvalidEnvValue) as caught:
        save_credentials("pl", rig.root / ".env", {"PL_PASS": f"{VALUE}\nINJECT=1"})
    assert VALUE not in str(caught.value) and rig.secrets() == []


# ---- M37: lifecycle ---------------------------------------------------------------------------


def test_dropping_a_key_deletes_only_that_projects_document(rig: CredRig) -> None:
    put_credentials("a", {"A_PASS": VALUE, "A_USER": OTHER})
    put_credentials("b", {"B_PASS": "other-b"})
    assert drop_credentials("a", ["A_PASS"]) == 1
    assert drop_credentials("a", ["B_PASS"]) == 0  # the filter carries `p`: b's key survives
    assert {d["_id"] for d in rig.secrets()} == {"A_USER", "B_PASS"}


def test_dropping_a_project_deletes_its_secrets_and_sessions(rig: CredRig) -> None:
    put_credentials("a", {"A_PASS": VALUE})
    put_credentials("b", {"B_PASS": OTHER})
    sessions = next(iter(rig.server.databases.values()))["browser_sessions"]
    sessions.docs.extend([{"_id": "s1", "p": "a"}, {"_id": "s2", "p": "b"}])
    assert drop_credentials("a") == 1
    assert [d["_id"] for d in rig.secrets()] == ["B_PASS"]
    assert [d["_id"] for d in sessions.docs] == ["s2"]


def test_a_snapshot_puts_the_previous_document_back_unchanged(rig: CredRig) -> None:
    put_credentials("pl", {"PL_PASS": VALUE})
    before, tree = copy.deepcopy(rig.secrets()), rig.tree()  # copies: the fake edits in place
    snap = snapshot_credentials(["PL_PASS", "PL_NEW"])
    put_credentials("pl", {"PL_PASS": OTHER, "PL_NEW": OTHER})
    restore_credentials(snap)
    assert rig.secrets() == before  # same document, same updated_at; the new one is gone
    assert rig.tree() == tree  # no copy in `.env`, a temp file or a log


# ---- file mode is the old path ----------------------------------------------------------------


def test_with_the_store_off_everything_is_the_env_path(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    off = make_rig(tmp_path, monkeypatch, area=False)
    monkeypatch.setenv("PL_PASS", "env-v")  # the environment is NOT a layer in file mode
    env = off.root / ".env"
    save_credentials("pl", env, {"PL_PASS": VALUE})
    assert parse_env(env.read_text(encoding="utf-8")) == {"PL_PASS": VALUE}
    assert credential_collection() is None and stored_secret_values() == {}
    assert drop_credentials("pl") == 0 and snapshot_credentials(["PL_PASS"]) == {}
    assert resolve_credentials({"PL_PASS": VALUE, "X": "y"}, "pl", {"PL_PASS"}) == (
        {"PL_PASS": VALUE}, {"X": "y"})
    assert redaction_values({"K": "v"}) == {"K": "v"}
    with pytest.raises(CredentialRefused):
        put_credentials("pl", {"PL_PASS": VALUE})  # the door itself needs the store on

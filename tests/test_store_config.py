"""mongo-store M1, M4(a,b,d): the database name has ONE source, a committed config table.

Every refusal here happens before any client exists: the factory below fails the test if called.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from fake_mongo import FakeMongoServer
from pydantic import ValidationError

from autotester.core.paths import code_root, repo_root
from autotester.schema.store_config import (
    StoreConfig,
    StoreConfigError,
    clear_store_config_cache,
    load_store_config,
)
from autotester.store.mongo_guard import GuardedStore

URI = "mongodb://h/"


def _cfg(tmp_path: Path, body: str, name: str = "pyproject.toml") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _store_table(database: str) -> str:
    return f'[tool.autotester.store]\ndatabase = "{database}"\n'


def _never_a_client(_uri: str) -> object:
    raise AssertionError("a client was created for a configuration that must be refused")


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    clear_store_config_cache()


def test_the_committed_file_names_autotester_and_the_loader_returns_it() -> None:
    raw = tomllib.loads((code_root() / "pyproject.toml").read_text(encoding="utf-8"))
    assert raw["tool"]["autotester"]["store"] == {"database": "autotester"}
    assert load_store_config().database == "autotester"


@pytest.mark.parametrize("name", ["admin", "local", "config", "Admin", "LOCAL", "CoNfIg"])
def test_system_databases_are_refused_case_folded(tmp_path: Path, name: str) -> None:
    path = _cfg(tmp_path, _store_table(name))
    with pytest.raises(StoreConfigError):
        GuardedStore(URI, config_path=path, client_factory=_never_a_client)
    with pytest.raises(ValidationError):
        StoreConfig(database=name)


@pytest.mark.parametrize(
    "name",
    ["", "a.b", "x y", "$x", "a/b", "a" * 39, "caf\u00e9", "1abc", "-a", "ok\n", "a\x00b"],
)
def test_names_that_are_not_plain_identifiers_are_refused(tmp_path: Path, name: str) -> None:
    body = "[tool.autotester.store]\ndatabase = " + repr(name).replace("'", '"') + "\n"
    path = _cfg(tmp_path, body)
    with pytest.raises((StoreConfigError, ValidationError)):
        GuardedStore(URI, config_path=path, client_factory=_never_a_client)
    with pytest.raises(ValidationError):
        StoreConfig(database=name)


def test_the_longest_plain_name_is_accepted() -> None:
    assert StoreConfig(database="a" * 38).database == "a" * 38


@pytest.mark.parametrize(
    "body",
    [
        "[tool.autotester]\nx = 1\n",
        "[tool.pytest]\nx = 1\n",
        "[tool.autotester.store]\n",
        '[tool.autotester.store]\nproduct_databases = ["pathlynks"]\n',
        '[tool.autotester.store]\ndatabase = "x1"\nproduct_databases = ["pathlynks"]\n',
        '[tool.autotester.store]\ndatabase = "x1"\nextra = 1\n',
        "[tool.autotester.store]\ndatabase = 5\n",
        '[tool.autotester]\nstore = "x1"\n',
        "not = [valid toml",
    ],
    ids=["no-table", "no-tool", "no-key", "only-leftover-key", "leftover-key", "unknown-key",
         "non-string", "store-not-a-table", "broken-toml"],
)
def test_a_missing_table_missing_key_or_unknown_key_stops_startup(
        tmp_path: Path, body: str) -> None:
    path = _cfg(tmp_path, body)
    with pytest.raises(StoreConfigError):
        GuardedStore(URI, config_path=path, client_factory=_never_a_client)


def test_a_missing_config_file_stops_startup(tmp_path: Path) -> None:
    with pytest.raises(StoreConfigError):
        GuardedStore(URI, config_path=tmp_path / "nope.toml", client_factory=_never_a_client)


def test_the_model_is_frozen_and_forbids_extra_keys() -> None:
    cfg = StoreConfig(database="alpha")
    with pytest.raises(ValidationError):
        cfg.database = "beta"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        StoreConfig(database="alpha", product_databases=["x"])  # type: ignore[call-arg]


def test_environment_and_data_root_have_no_effect_on_the_name(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("AUTOTESTER_DB", "AUTOTESTER_STORE_DATABASE", "MONGODB_DB", "MONGO_DB_NAME",
                "AUTOTESTER_STORE_CONFIG"):
        monkeypatch.setenv(var, "hijack")
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(data_root))
    client = FakeMongoServer().client()
    GuardedStore(URI, client_factory=lambda _uri: client)
    assert client.accessed == ["autotester"]
    assert set(client.accessed) == {load_store_config().database}


def test_the_data_root_moves_repo_root_but_never_code_root(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before = code_root()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    assert repo_root() == tmp_path.resolve()
    assert code_root() == before
    assert (code_root() / "pyproject.toml").is_file()


def test_the_config_is_read_once_per_process(tmp_path: Path) -> None:
    path = _cfg(tmp_path, _store_table("first"))
    assert load_store_config(path).database == "first"
    path.write_text(_store_table("second"), encoding="utf-8")
    assert load_store_config(path).database == "first"
    clear_store_config_cache()
    assert load_store_config(path).database == "second"

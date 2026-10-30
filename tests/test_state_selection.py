"""mongo-store M13: the backend is configuration, and a driver is never imported for `file`.

`AUTOTESTER_STORE` unset means `file`. An unknown value, or an unknown area / backend in
`AUTOTESTER_STORE_AREAS`, stops startup (never a silent default). `mongo` is wired to
`store/mongo_backend.py` and needs `AUTOTESTER_MONGO_URI`; without it startup stops. An area whose
data never travels through a state key (auth, credentials, blobs) is refused on `mongo` until its
unit routes it (U2 checker-B W5). The cold-start test runs a real file-mode workload in a fresh
interpreter and asserts no database driver was imported.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_mongo import FakeMongoServer, seams

import autotester.store.filestore as filestore
from autotester.core.paths import code_root
from autotester.store.filestore import FileBackend, backend_for, validate_store_env
from autotester.store.mongo_backend import MongoBackend, reset_default_backend
from autotester.store.mongo_routes import (
    AREAS,
    UNROUTED,
    StoreSelectionError,
    area_of,
    store_selection,
)


@pytest.fixture(autouse=True)
def _clean_selection(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS", "AUTOTESTER_MONGO_URI"):
        monkeypatch.delenv(name, raising=False)
    reset_default_backend()
    yield
    reset_default_backend()


def test_unset_and_blank_mean_file_for_every_area(monkeypatch: pytest.MonkeyPatch) -> None:
    assert store_selection() == dict.fromkeys(AREAS, "file")
    monkeypatch.setenv("AUTOTESTER_STORE", "  ")
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", " , ,")
    assert store_selection() == dict.fromkeys(AREAS, "file")
    assert validate_store_env() == dict.fromkeys(AREAS, "file")


@pytest.mark.parametrize("value", ["File", "sqlite", "mongodb", "postgres", "1", "mongo,file"])
def test_an_unknown_store_value_stops_startup(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", value)
    with pytest.raises(StoreSelectionError, match="unknown store backend"):
        validate_store_env()


@pytest.mark.parametrize("areas", ["projcts=mongo", "settings=sqlite", "settings", "=mongo",
                                   "settings=file,runz=file", "settings=", "a=b=c"])
def test_a_typo_in_the_areas_stops_startup(monkeypatch: pytest.MonkeyPatch, areas: str) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", areas)
    with pytest.raises(StoreSelectionError):
        validate_store_env()


def test_areas_override_single_areas_and_tolerate_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", " settings = file , runs=mongo ,")
    chosen = store_selection()
    assert (chosen["runs"], chosen["settings"], chosen["projects"]) == ("mongo", "file", "file")


def test_mongo_without_a_uri_stops_startup_and_names_the_variable(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    assert set(store_selection().values()) == {"mongo"}
    with pytest.raises(StoreSelectionError, match="AUTOTESTER_MONGO_URI is not set"):
        validate_store_env()
    with pytest.raises(StoreSelectionError, match="AUTOTESTER_MONGO_URI is not set"):
        backend_for("projects/p/project.json")


def test_mongo_with_a_uri_is_wired_to_the_mongo_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv("AUTOTESTER_MONGO_URI", "mongodb://h/")
    with seams(client_factory=lambda _uri: FakeMongoServer().client()):
        assert isinstance(backend_for("projects/p/project.json"), MongoBackend)
        assert validate_store_env()["projects"] == "mongo"


def test_one_area_on_mongo_only_fails_the_keys_in_that_area(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "runs=mongo")
    assert isinstance(backend_for("projects/p/project.json"), FileBackend)
    with pytest.raises(StoreSelectionError, match="AUTOTESTER_MONGO_URI is not set"):
        backend_for("projects/p/runs/r1/result.json")
    with pytest.raises(StoreSelectionError):
        validate_store_env()


@pytest.mark.parametrize("area", sorted(UNROUTED))
def test_an_area_that_routes_nothing_is_refused_on_mongo_but_allowed_on_file(
        monkeypatch: pytest.MonkeyPatch, area: str) -> None:
    """W5: `auth=mongo` used to be accepted and silently did nothing."""
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", f"{area}=mongo")
    with pytest.raises(StoreSelectionError, match="routes nothing yet"):
        validate_store_env()
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", f"{area}=file")
    assert store_selection()[area] == "file"


def test_the_approvals_and_queue_families_have_an_area_so_they_can_be_flipped() -> None:
    assert area_of("projects/p/approvals.jsonl") == "approvals"
    assert area_of("projects/p/approval_revocations.jsonl") == "approvals"
    assert area_of(".work/run_queue.json") == "queue"
    assert area_of(".work/team/schedule/claims/a.json") == "queue"
    assert area_of(".work/team/delivery/d.jsonl") == "queue"


def test_a_typo_surfaces_on_first_use_not_only_at_startup(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTOTESTER_STORE", "bogus")
    with pytest.raises(StoreSelectionError):
        filestore.write_text(tmp_path.resolve() / "projects" / "p" / "x.txt", "x")
    assert not (tmp_path / "projects").exists()


def test_the_server_refuses_to_start_on_a_typo(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.ui.app import _lifespan, app

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))  # load_repo_env reads no real `.env`
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "projcts=mongo")

    async def start() -> None:
        async with _lifespan(app):
            pass

    with pytest.raises(StoreSelectionError):
        asyncio.run(start())


def test_area_of_routes_the_documented_prefixes() -> None:
    assert area_of("projects/p/runs/r/result.json") == "runs"
    assert area_of("projects/p/crawl/c.json") == "crawls"
    assert area_of("projects/p/project.json") == "projects"
    assert area_of(".work/server_settings.json") == "settings"
    assert set(map(area_of, ["projects/p", "x.json", ".work/a"])) <= set(AREAS)


def test_a_file_mode_workload_never_imports_a_database_driver(tmp_path: Path) -> None:
    """Cold start in a fresh interpreter, as production runs: nothing pulls pymongo or gridfs."""
    script = (
        "import sys\n"
        "import autotester.cli, autotester.ui.app\n"
        "from pathlib import Path\n"
        "from autotester.schema.project import Project\n"
        "from autotester.store.project_store import ProjectStore\n"
        "from autotester.store.filestore import validate_store_env\n"
        "validate_store_env()\n"
        "store = ProjectStore('pathlinks', Path(sys.argv[1]))\n"
        "store.save_project(Project(slug='pathlinks', name='P', base_url='https://a.test',"
        " allowed_domains=['a.test']))\n"
        "assert store.load_project() is not None\n"
        "drivers = {'pymongo', 'gridfs', 'bson'}\n"
        "print(sorted(m for m in sys.modules if m.split('.')[0] in drivers))\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("AUTOTESTER_STORE")}
    env.update(PYTHONPATH=str(code_root() / "src"), AUTOTESTER_ROOT=str(tmp_path))
    done = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=env,
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-1500:]
    assert done.stdout.strip().splitlines()[-1] == "[]"

"""mongo-store M13: the backend is configuration, and a driver is never imported for `file`.

`AUTOTESTER_STORE` unset means `file`. An unknown value, or an unknown area / backend in
`AUTOTESTER_STORE_AREAS`, stops startup (never a silent default). `mongo` is a recognised name but
no Mongo backend is wired in this build, so choosing it stops startup too. The cold-start test runs
a real file-mode workload in a fresh interpreter and asserts no database driver was imported.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

import autotester.store.filestore as filestore
from autotester.core.paths import code_root
from autotester.store.filestore import (
    AREAS,
    FileBackend,
    StoreSelectionError,
    area_of,
    backend_for,
    store_selection,
    validate_store_env,
)


@pytest.fixture(autouse=True)
def _clean_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS", raising=False)


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


def test_mongo_is_recognised_but_not_wired_in_this_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    assert set(store_selection().values()) == {"mongo"}
    with pytest.raises(StoreSelectionError, match="not wired"):
        validate_store_env()
    with pytest.raises(StoreSelectionError, match="not wired"):
        backend_for("projects/p/project.json")


def test_one_area_on_mongo_only_fails_the_keys_in_that_area(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "runs=mongo")
    assert isinstance(backend_for("projects/p/project.json"), FileBackend)
    with pytest.raises(StoreSelectionError, match="not wired"):
        backend_for("projects/p/runs/r1/result.json")
    with pytest.raises(StoreSelectionError):
        validate_store_env()


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

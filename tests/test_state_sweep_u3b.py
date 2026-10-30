"""mongo-store U3b (M16): listings, existence and mtime of project state go through the store.

Every test flips the `projects` and `runs` areas to the Mongo backend over the hand-written fake,
writes the state only through `filestore`, and then checks that the site under test sees it while
nothing exists on disk. A site that still lists or stats the data root would see an empty
directory and the test fails.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_mongo import FakeMongoServer, seams
from fastapi import HTTPException
from schedule_fakes import daily

import autotester.store.filestore as filestore
from autotester.core.env import project_credentials
from autotester.core.paths import repo_root
from autotester.schema.project import Project
from autotester.stages.schedule_wiring import scheduled_projects
from autotester.store.mongo_backend import reset_default_backend
from autotester.store.project_store import ProjectStore
from autotester.ui.credential_guard import refuse_foreign_key
from autotester.ui.helpers import _project_slugs
from autotester.ui.project_view import _has_corrupt_run, _last_change


def _project(slug: str, **extra: object) -> Project:
    return Project(slug=slug, name=slug, base_url="https://demo.test",
                   allowed_domains=["demo.test"], **extra)


@pytest.fixture
def mongo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "projects=mongo,runs=mongo")
    monkeypatch.setenv("AUTOTESTER_MONGO_URI", "mongodb://h/")
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    reset_default_backend()
    try:
        with seams(client_factory=lambda _uri: FakeMongoServer().client()):
            yield root.resolve()
    finally:
        reset_default_backend()


def _nothing_on_disk(root: Path) -> None:
    assert not (root / "projects").exists()


def test_the_project_list_comes_from_the_store(mongo_root: Path) -> None:
    ProjectStore("beta").save_project(_project("beta"))
    ProjectStore("alpha").save_project(_project("alpha"))
    filestore.write_text(repo_root() / "projects" / "stray" / "notes.txt", "no project.json")
    assert _project_slugs() == ["alpha", "beta"]
    _nothing_on_disk(mongo_root)


def test_a_foreign_namespace_is_found_through_the_store(mongo_root: Path) -> None:
    ProjectStore("alpha").save_project(_project("alpha"))
    ProjectStore("alpha-beta").save_project(_project("alpha-beta"))
    with pytest.raises(HTTPException) as caught:
        refuse_foreign_key(_project("alpha"), "ALPHA_BETA_TOKEN")
    assert "another project's namespace" in caught.value.detail
    refuse_foreign_key(_project("alpha"), "ALPHA_OWN_TOKEN")  # its own namespace passes
    _nothing_on_disk(mongo_root)


def test_last_change_reads_the_store_mtime(mongo_root: Path) -> None:
    store = ProjectStore("demo")
    assert _last_change(store) is None
    store.save_project(_project("demo"))
    assert _last_change(store) is not None
    _nothing_on_disk(mongo_root)


def test_a_corrupt_run_is_found_through_the_store(mongo_root: Path) -> None:
    store = ProjectStore("demo")
    store.save_project(_project("demo"))
    assert _has_corrupt_run(store) is False
    filestore.write_text(store.paths.runs_dir / "r1" / "run.json", "{not json")
    assert _has_corrupt_run(store) is True
    _nothing_on_disk(mongo_root)


def test_declared_credentials_are_read_from_the_store(mongo_root: Path) -> None:
    body = json.dumps({"name": "demo", "secrets": [{"key": "DEMO_PASSWORD"}, "junk", {"nokey": 1}]})
    filestore.write_text(mongo_root / "projects" / "demo" / "project.json", body)
    filestore.write_text(mongo_root / "projects" / "gone" / "project.json", "[]")
    prefixes, declared = project_credentials(mongo_root)
    assert prefixes == ("DEMO_", "GONE_")
    assert declared == frozenset({"DEMO_PASSWORD"})
    _nothing_on_disk(mongo_root)


def test_scheduled_projects_are_listed_from_the_store(mongo_root: Path) -> None:
    ProjectStore("nightly").save_project(_project("nightly", schedule=daily()))
    ProjectStore("plain").save_project(_project("plain"))
    filestore.write_text(repo_root() / "projects" / "stray" / "notes.txt", "no project.json")
    items, invalid = scheduled_projects()
    assert [i.project for i in items] == ["nightly"] and invalid == []
    assert items[0].since.tzinfo is not None
    _nothing_on_disk(mongo_root)


# --- file mode: behaviour with AUTOTESTER_STORE unset is what it was -------------------------
def test_file_mode_credentials_tolerate_every_shape_of_project_json(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS", raising=False)
    shapes = {"a": '{"secrets": [{"key": "A_KEY"}]}', "b": "{not json", "c": "[1]",
              "d": '{"secrets": {"key": "X"}}', "e": '{"secrets": [{"key": "E_KEY"}, 3]}',
              "f": '{"name": "no secrets"}'}
    for slug, text in shapes.items():
        target = tmp_path / "projects" / slug / "project.json"
        target.parent.mkdir(parents=True)
        target.write_text(text, encoding="utf-8")
    (tmp_path / "projects" / "no-config").mkdir()
    (tmp_path / "projects" / "a-file.txt").write_text("x", encoding="utf-8")
    prefixes, declared = project_credentials(tmp_path)
    assert prefixes == ("A_", "B_", "C_", "D_", "E_", "F_")
    assert declared == frozenset({"A_KEY", "E_KEY"})
    assert project_credentials(tmp_path / "missing") == ((), frozenset())

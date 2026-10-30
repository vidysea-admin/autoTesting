"""mongo-store M2, M5, M6, M7, M8, M11 on the Mongo BACKEND: it only ever speaks through the guard.

The backend adds three promises on top of the guard's: it never names a database (M2, M5), it
refuses to edit an insert-only family with a named error and deletes nothing when any victim is
insert-only (M7), and a known secret value is refused before any write, in the text or the key,
without the error quoting it (M8). The identity marker shares `server_state` with state, and the
backend neither reads nor writes it as a state document (M11).
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from fake_mongo import FakeMongoServer, open_store

import autotester.store.mongo_backend as backend_module
import autotester.store.mongo_routes as routes_module
from autotester.core.redact import Redactor
from autotester.store.mongo_backend import MongoBackend, repo_redactor
from autotester.store.mongo_routes import (
    StoreImmutable,
    StoreSecretRefused,
    text_sha,
)

SECRET = "S3cr3t-Value-9f3a7c"
DB = "autotester"


def make(server: FakeMongoServer | None = None, uri: str = "mongodb://h/",
         redactor: Redactor | None = None) -> tuple[MongoBackend, FakeMongoServer, Any]:
    server = server or FakeMongoServer()
    client = server.client()
    return MongoBackend(open_store(uri, client), redactor or Redactor({})), server, client


def dump(server: FakeMongoServer) -> str:
    """Every document of every collection of every database, as text."""
    return json.dumps([doc for db in server.databases.values()
                       for coll in db.collections.values() for doc in coll.docs], default=str)


def test_no_public_parameter_of_the_backend_is_a_database_name() -> None:
    """M2: the public surface of `mongo_backend` and `mongo_routes` names no database."""
    banned = {"db", "database", "db_name"}
    for module in (backend_module, routes_module):
        for name, member in vars(module).items():
            if name.startswith("_") or getattr(member, "__module__", None) != module.__name__:
                continue
            targets = [member, *(m for _, m in inspect.getmembers(member, inspect.isfunction))]
            for target in (t for t in targets if callable(t)):
                try:
                    params = set(inspect.signature(target).parameters)
                except (TypeError, ValueError):
                    continue
                assert not params & banned, f"{module.__name__}.{name}"
    store = open_store(client=FakeMongoServer().client())
    with pytest.raises(TypeError):
        MongoBackend(store, Redactor({}), db_name="x")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        MongoBackend(store, Redactor({}), "x")  # type: ignore[misc]


def test_neither_module_imports_a_driver_or_opens_a_client() -> None:
    """M5/M6: the only driver import in the store is `mongo_guard`."""
    for module in (backend_module, routes_module):
        tree = ast.parse(Path(str(module.__file__)).read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom)}
        assert not imported & {"pymongo", "gridfs", "bson"}, module.__name__
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not (names | attrs) & {"MongoClient", "get_database", "drop_database"}


@pytest.mark.parametrize("uri", ["mongodb://h/", "mongodb://h/scratch",
                                 "mongodb://h/?authSource=admin"])
def test_a_whole_workload_touches_only_the_configured_database(uri: str) -> None:
    backend, server, client = make(uri=uri)
    backend.put("projects/p/project.json", "{}")
    backend.append_row("projects/p/cases.jsonl", '{"id": "a"}')
    backend.upsert_row("projects/p/cases.jsonl", "id", "a", '{"id": "a", "v": 2}')
    backend.replace_rows("projects/p/cases.jsonl", ['{"id": "b"}'])
    assert backend.put_if("projects/p/runs/r/run.json", "x", None)
    assert backend.create_exclusive(".work/team/schedule/claims/c.json", "x")
    assert backend.keys("projects/") and backend.children("projects")
    backend.delete_prefix("projects/p/runs/")
    backend.delete("projects/p/project.json")
    backend.ping()
    assert set(client.accessed) == {DB}
    assert {name for name, _ in server.log} == {DB}


@pytest.mark.parametrize("key", ["projects/p/approvals.jsonl",
                                 "projects/p/approval_revocations.jsonl"])
def test_an_insert_only_row_set_takes_appends_and_refuses_every_edit(key: str) -> None:
    backend, _, _ = make()
    backend.append_row(key, '{"id": "a"}')
    backend.append_row(key, '{"id": "b"}')
    for call in (lambda: backend.replace_rows(key, []), lambda: backend.delete(key),
                 lambda: backend.upsert_row(key, "id", "a", '{"id": "a", "x": 1}'),
                 lambda: backend.delete_row(key, "id", "a"),
                 lambda: backend.put(key, '{"id": "z"}\n')):
        with pytest.raises(StoreImmutable, match="insert-only"):
            call()
    assert backend.rows(key) == ['{"id": "a"}', '{"id": "b"}']


@pytest.mark.parametrize("key", ["projects/p/bug_events/e1.json", ".work/team/delivery/d1.json"])
def test_an_insert_only_document_is_written_once_and_never_changed(key: str) -> None:
    backend, _, _ = make()
    backend.put(key, "first")
    backend.put(key, "first")  # the identical text is a no-op, not an edit
    with pytest.raises(StoreImmutable):
        backend.put(key, "second")
    with pytest.raises(StoreImmutable):
        backend.put_if(key, "third", text_sha("first"))
    with pytest.raises(StoreImmutable):
        backend.delete(key)
    assert backend.get(key) == "first" and backend.create_exclusive(key, "x") is False


def test_append_text_to_an_insert_only_family_adds_rows_but_never_edits_a_document() -> None:
    backend, _, _ = make()
    backend.append_text("projects/p/approvals.jsonl", '{"id": "a"}\n{"id": "b"}\n')
    assert backend.rows("projects/p/approvals.jsonl") == ['{"id": "a"}', '{"id": "b"}']
    backend.put("projects/p/bug_events/e1.json", "first")
    with pytest.raises(StoreImmutable):
        backend.append_text("projects/p/bug_events/e1.json", "more")
    assert backend.get("projects/p/bug_events/e1.json") == "first"


def test_delete_prefix_over_an_insert_only_family_deletes_nothing() -> None:
    backend, _, _ = make()
    backend.put("projects/p/a.json", "keep")
    backend.append_row("projects/p/approvals.jsonl", '{"id": "a"}')
    backend.put("projects/p/z.json", "keep")
    with pytest.raises(StoreImmutable):
        backend.delete_prefix("projects/p/")
    assert backend.get("projects/p/a.json") == "keep" and backend.get("projects/p/z.json") == "keep"
    assert backend.rows("projects/p/approvals.jsonl") == ['{"id": "a"}']


def _writes(backend: MongoBackend, key: str, text: str) -> list[Any]:
    rows = key.replace(".json", ".jsonl")
    return [lambda: backend.put(key, text), lambda: backend.put(key, text.encode()),
            lambda: backend.put_if(key, text, None), lambda: backend.create_exclusive(key, text),
            lambda: backend.append_row(rows, text), lambda: backend.replace_rows(rows, [text]),
            lambda: backend.upsert_row(rows, "id", "1", text),
            lambda: backend.append_text(key, text)]


def _quotes_nothing(error: BaseException) -> bool:
    """The secret is in no rendering of the error: str, repr, or any of its args."""
    return all(SECRET not in text for text in (str(error), repr(error), *map(str, error.args)))


def test_a_known_secret_is_refused_everywhere_and_never_quoted() -> None:
    backend, server, _ = make(redactor=Redactor({"PATHLYNKS_PASSWORD": SECRET}))
    for text in (f"password={SECRET}", f'{{"id": "1", "note": "{SECRET}"}}'):
        for call in _writes(backend, "projects/p/x.json", text):
            with pytest.raises(StoreSecretRefused) as caught:
                call()
            assert _quotes_nothing(caught.value)
            assert caught.value.__cause__ is None and caught.value.__context__ is None
    with pytest.raises(StoreSecretRefused) as keyed:
        backend.put(f"projects/p/{SECRET}.json", "clean text")  # the key is scanned too
    assert _quotes_nothing(keyed.value)  # cycle 1: the refusal never echoes the key either
    with pytest.raises(StoreSecretRefused) as huge:  # ... nor does the size check run first
        backend.put(f"projects/p/{SECRET}.json", "x" * (backend_module.MAX_DOC_BYTES + 1))
    assert _quotes_nothing(huge.value)
    assert SECRET not in dump(server)
    assert backend.keys("") == []


def test_a_secret_hidden_by_a_row_that_is_not_the_first_is_still_refused() -> None:
    backend, server, _ = make(redactor=Redactor({"K": SECRET}))
    with pytest.raises(StoreSecretRefused):
        backend.replace_rows("projects/p/cases.jsonl", ['{"id": "a"}', f'{{"id": "{SECRET}"}}'])
    assert backend.rows("projects/p/cases.jsonl") == [] and SECRET not in dump(server)


def test_the_default_redactor_reads_the_repo_env_without_echoing_it(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(f"PATHLYNKS_PASSWORD={SECRET}\nEMPTY=\n", encoding="utf-8")
    backend = MongoBackend(open_store(client=FakeMongoServer().client()))
    with pytest.raises(StoreSecretRefused) as caught:
        backend.put("projects/p/x.json", f"leak {SECRET}")
    assert SECRET not in str(caught.value)
    with pytest.raises(StoreSecretRefused):
        MongoBackend(open_store(client=FakeMongoServer().client()),
                     repo_redactor({"MONGO_URI": "mongodb://u:pw@h/"})).put(
            "projects/p/y.json", "mongodb://u:pw@h/")
    backend.put("projects/p/x.json", "clean")


def test_the_identity_marker_is_not_a_state_document_and_is_never_rewritten() -> None:
    backend, server, _ = make()
    assert backend.get("marker") is None and backend.exists("marker") is False
    backend.put(".work/a.json", "x")
    marker = dict(server.databases[DB]["server_state"].docs[0])
    assert marker["_id"] == "marker" and marker["database"] == DB
    for call in (lambda: backend.put("marker", "x"),
                 lambda: backend.create_exclusive("marker", "x"),
                 lambda: backend.delete("marker"), lambda: backend.put_if("marker", "x", None)):
        with pytest.raises(ValueError, match="marker"):
            call()
    second, _, _ = make(server)
    second.put(".work/b.json", "y")
    docs = server.databases[DB]["server_state"].docs
    assert [d for d in docs if d["_id"] == "marker"] == [marker]
    assert second.keys("") == [".work/a.json", ".work/b.json"]


def test_a_document_append_that_loses_the_compare_and_set_retries_and_keeps_both() -> None:
    backend, _, _ = make()
    backend.put("logs/x.log", "a\n")
    real, fired = backend.get, []

    def racing(key: str) -> str | None:  # another writer lands between our read and our write
        seen = real(key)
        if not fired:
            fired.append(key)
            backend.put(key, (seen or "") + "other\n")
        return seen

    backend.get = racing  # type: ignore[method-assign]
    backend.append_text("logs/x.log", "mine\n")
    assert real("logs/x.log") == "a\nother\nmine\n" and fired


def test_append_text_is_all_or_nothing_when_a_later_line_is_refused() -> None:
    """Cycle 1: every line is vetted before the first one is written."""
    backend, server, _ = make(redactor=Redactor({"K": SECRET}))
    backend.append_row("logs/a.jsonl", '{"id": "0"}')
    text = '{"id": "1"}\n{"id": "2"}\n' + f'{{"id": "{SECRET}"}}\n'
    with pytest.raises(StoreSecretRefused):
        backend.append_text("logs/a.jsonl", text)
    assert backend.rows("logs/a.jsonl") == ['{"id": "0"}'] and SECRET not in dump(server)




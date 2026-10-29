"""mongo-store M2, M4(c,e), M5, M9, M11: the write fence, driven through a SPY client.

Nothing here opens a socket (M47). The server double holds FOREIGN databases so a leak shows up as
a name in the access log or a changed foreign document, not as a silent pass.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from pathlib import Path

import pytest
from fake_mongo import (
    CANARY,
    FakeBucket,
    FakeMongoClient,
    FakeMongoServer,
    assert_no_canary,
    open_store,
    seams,
)

import autotester.store.mongo_guard as guard_module
from autotester.store.mongo_guard import (
    COLLECTIONS,
    INSERT_ONLY,
    GuardedStore,
    StoreConfigError,
    StoreUnavailable,
)

GOOD_URIS = ["mongodb://h/", "mongodb://h/scratch", "mongodb://h/?authSource=admin",
             f"mongodb://user:{CANARY}@h1,h2/pathlynks?replicaSet=r"]


def make(server: FakeMongoServer,
         uri: str = "mongodb://h/") -> tuple[GuardedStore, FakeMongoClient]:
    client = server.client()
    return open_store(uri, client), client


def workload(store: GuardedStore) -> None:
    """Every collection verb, GridFS put/get/delete, the marker, ping, listing."""
    store.ping()
    for name in sorted(COLLECTIONS):
        col = store.collection(name)
        col.create_index([("p", 1)])
        col.insert_one({"_id": f"{name}-1", "p": "proj", "k": "key"})
        assert col.find_one({"_id": f"{name}-1"}) is not None
        assert col.count_documents({"p": "proj"}) == 1
        if name not in INSERT_ONLY and name != "server_state":
            col.replace_one({"_id": f"{name}-1"}, {"p": "proj", "k": "key", "n": 1})
            col.update_one({"_id": f"{name}-1"}, {"$inc": {"n": 1}})
            col.delete_many({"p": "proj"})
    bucket = store.bucket()
    file_id = bucket.upload("a/b.png", b"png", metadata={"sha256": "x"})
    assert bucket.download("a/b.png") == b"png"
    assert [r["id"] for r in bucket.revisions("a/b.png")] == [file_id]
    bucket.delete(file_id)
    store.collection_names()
    store.ensure_marker()


@pytest.mark.parametrize("uri", GOOD_URIS)
def test_the_spy_sees_exactly_the_configured_database_across_the_whole_workload(uri: str) -> None:
    server = FakeMongoServer()
    names = ("pathlynks", "scratch", "admin")
    for name in names:
        server.seed_foreign(name)
    foreign = {n: list(server.databases[n]["users"].docs) for n in names}
    server.log.clear()
    store, client = make(server, uri)
    workload(store)
    assert set(client.accessed) == {"autotester"}
    assert {db for db, _ in server.log} == {"autotester"}
    assert {n: server.databases[n]["users"].docs for n in names} == foreign
    assert set(server.databases) == {"autotester", *names}
    assert all(set(server.databases[n].collections) == {"users"} for n in names)


def test_signatures_take_no_database_parameter() -> None:
    with pytest.raises(TypeError):
        GuardedStore("mongodb://h/", "x")  # type: ignore[misc]
    for keyword in ("db", "database", "db_name"):
        with pytest.raises(TypeError):
            GuardedStore("mongodb://h/", **{keyword: "x"})  # type: ignore[arg-type]
    banned = {"db", "database", "db_name"}
    seen = 0
    for obj in vars(guard_module).values():
        if getattr(obj, "__module__", None) != guard_module.__name__:
            continue
        if inspect.isfunction(obj):
            members = [obj]
        elif inspect.isclass(obj):
            members = [m for _, m in inspect.getmembers(obj, inspect.isfunction)]
        else:
            members = []
        for fn in members:
            seen += 1
            assert not banned & set(inspect.signature(fn).parameters), fn
    assert seen > 20


def test_the_constructor_takes_a_uri_and_nothing_else() -> None:
    params = inspect.signature(GuardedStore.__init__).parameters
    assert list(params) == ["self", "uri"]


def test_no_public_path_builds_a_store_on_another_database(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = tmp_path / "pyproject.toml"
    other.write_text('[tool.autotester.store]' + chr(10) + 'database = "pathlynks_prod"' + chr(10),
                     encoding="utf-8")
    server = FakeMongoServer()
    client = server.client()
    attempts: list[Callable[[], object]] = [
        lambda: GuardedStore("mongodb://h/", config_path=other),
        lambda: GuardedStore("mongodb://h/", other),
        lambda: GuardedStore("mongodb://h/", client_factory=lambda _u: client),
        lambda: GuardedStore("mongodb://h/", bucket_factory=FakeBucket),
        lambda: GuardedStore("mongodb://h/", config=other),
        lambda: GuardedStore("mongodb://h/", database="pathlynks_prod"),
        lambda: GuardedStore("mongodb://h/pathlynks_prod", client_factory=lambda _u: client),
    ]
    for attempt in attempts:
        with pytest.raises(TypeError):
            attempt()
    for key in ("AUTOTESTER_STORE_CONFIG", "AUTOTESTER_STORE_DATABASE", "AUTOTESTER_DB",
                "MONGODB_DB", "AUTOTESTER_ROOT"):
        monkeypatch.setenv(key, str(other if "CONFIG" in key else tmp_path))
    store, spy = make(server, "mongodb://h/pathlynks_prod")
    store.collection("projects").insert_one({"_id": "a", "p": "a"})
    assert set(spy.accessed) == {"autotester"} and set(server.databases) == {"autotester"}
    assert client.accessed == [] and "pathlynks_prod" not in server.databases


def test_the_seams_are_restored_after_use_so_one_test_cannot_leak_into_the_next() -> None:
    before = dict(guard_module._SEAM)
    with seams(client_factory=lambda _u: None):
        assert guard_module._SEAM["client_factory"] is not None
    assert before == guard_module._SEAM
    assert before == {"config_path": None, "client_factory": None, "bucket_factory": None}


def test_an_existing_unmarked_database_with_collections_is_somebody_elses() -> None:
    server = FakeMongoServer()
    server.seed_foreign("autotester", "customers")
    client = server.client()
    with pytest.raises(StoreConfigError):
        open_store("mongodb://h/", client)
    assert set(client.accessed) == {"autotester"}
    assert server.databases["autotester"]["customers"].docs == [{"_id": "foreign", "keep": True}]


def test_a_marker_for_another_name_stops_startup() -> None:
    server = FakeMongoServer()
    state = server.database("autotester")["server_state"]
    state.docs.append({"_id": "marker", "database": "other"})
    with pytest.raises(StoreConfigError):
        make(server)


def test_an_empty_database_starts_without_writing_and_marks_on_first_write() -> None:
    server = FakeMongoServer()
    store, _ = make(server)
    assert server.databases["autotester"]["server_state"].docs == []
    store.collection("projects").insert_one({"_id": "a", "p": "a"})
    marker = server.databases["autotester"]["server_state"].find_one({"_id": "marker"})
    assert marker is not None
    assert (marker["database"], marker["schema_version"]) == ("autotester", 1)
    assert "created_at" in marker


def test_the_marker_is_never_rewritten_and_a_second_start_accepts_it() -> None:
    server = FakeMongoServer()
    first, _ = make(server)
    first.ensure_marker()
    original = dict(server.databases["autotester"]["server_state"].docs[0])
    second, _ = make(server)
    second.collection("projects").insert_one({"_id": "b", "p": "b"})
    second.ensure_marker()
    assert server.databases["autotester"]["server_state"].docs == [original]


def test_the_marker_cannot_be_written_deleted_or_reached_by_a_broad_filter() -> None:
    server = FakeMongoServer()
    store, _ = make(server)
    store.ensure_marker()
    state = store.collection("server_state")
    for call in (
        lambda: state.insert_one({"_id": "marker", "database": "x"}),
        lambda: state.replace_one({"_id": "marker"}, {"database": "x"}),
        lambda: state.update_one({"_id": "marker"}, {"$set": {"database": "x"}}),
        lambda: state.delete_one({"_id": "marker"}),
        lambda: state.delete_one({"database": "autotester"}),
        lambda: state.update_one({"schema_version": 1}, {"$set": {"schema_version": 2}}),
        lambda: state.replace_one({"_id": {"$ne": "x"}}, {"a": 1}),
    ):
        with pytest.raises(ValueError):
            call()
    marker = server.databases["autotester"]["server_state"].find_one({"_id": "marker"})
    assert marker is not None and marker["database"] == "autotester"
    state.replace_one({"_id": "heartbeat"}, {"last_tick": 1}, upsert=True)


def test_identity_reports_the_configured_name_and_nothing_secret() -> None:
    store, _ = make(FakeMongoServer(), f"mongodb://u:{CANARY}@h/x")
    assert store.identity() == {"database": "autotester"}
    assert "autotester" in repr(store) and CANARY not in repr(store)


def test_a_failing_connect_never_echoes_the_uri(
        capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    server = FakeMongoServer(down_message=f"connect failed for mongodb://u:{CANARY}@h/x")
    server.down = True
    with caplog.at_level(logging.DEBUG), pytest.raises(StoreUnavailable) as caught:
        make(server, f"mongodb://u:{CANARY}@h/x")
    assert "AutoReconnect" in str(caught.value)
    assert_no_canary(caught.value, capsys, caplog)


def test_a_failing_ping_and_write_never_echo_the_uri(
        capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    server = FakeMongoServer(down_message=f"mongodb://u:{CANARY}@h/x unreachable")
    store, _ = make(server, f"mongodb://u:{CANARY}@h/x")
    server.down = True
    for action in (store.ping, lambda: store.collection("projects").insert_one({"_id": "a"}),
                   lambda: store.bucket().upload("f", b"x", metadata={})):
        with caplog.at_level(logging.DEBUG), pytest.raises(StoreUnavailable) as caught:
            action()
        assert_no_canary(caught.value, capsys, caplog)
    assert CANARY not in repr(store) and CANARY not in str(vars(store))

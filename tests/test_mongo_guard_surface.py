"""mongo-store M6, M7, M47: the closed verb set, insert-only collections, the collection allow-list.

The surface is pinned as an EXACT list: adding a verb (an `aggregate`, a `command`, a `drop`) turns
the equality red, which is how a widening gets noticed in review rather than in production.
"""

from __future__ import annotations

import gc
from typing import Any

import pytest
from fake_mongo import FakeBucket, FakeMongoServer

from autotester.store.mongo_guard import (
    COLLECTIONS,
    INSERT_ONLY,
    GuardedBucket,
    GuardedCollection,
    GuardedStore,
    InsertOnlyCollection,
    StoreDuplicateKey,
)

READ_INSERT = {"count_documents", "create_index", "find", "find_one", "insert_one"}
MUTATING = {"delete_many", "delete_one", "replace_one", "update_one"}
FORBIDDEN = ("aggregate", "command", "bulk_write", "watch", "drop", "drop_collection",
             "drop_database", "rename", "with_options", "get_database", "get_default_database",
             "list_database_names", "client", "database", "db", "_client", "_db", "__getattr__")


def _public(obj: object) -> set[str]:
    return {n for n in dir(obj) if not n.startswith("_")}


@pytest.fixture
def store() -> GuardedStore:
    client = FakeMongoServer().client()
    return GuardedStore("mongodb://h/", client_factory=lambda _u: client,
                        bucket_factory=FakeBucket)


def _walk(obj: Any, seen: set[int], depth: int = 0) -> list[Any]:
    """Every object reachable through instance `__dict__`s and public attributes."""
    if id(obj) in seen or depth > 6:
        return []
    seen.add(id(obj))
    found = [obj]
    if isinstance(obj, dict):
        values = list(obj.values())
    elif isinstance(obj, list | tuple | set | frozenset):
        values = list(obj)
    else:
        values = list(getattr(obj, "__dict__", {}).values())
        names = [n for n in _public(obj) if not n.startswith("model_")]
        values += [v for v in (getattr(obj, n, None) for n in names) if not callable(v)]
    for value in values:
        found += _walk(value, seen, depth + 1)
    return found


def test_the_public_surface_is_exactly_the_frozen_list(store: GuardedStore) -> None:
    assert _public(store) == {"bucket", "collection", "collection_names", "ensure_marker",
                              "identity", "ping"}
    assert _public(GuardedCollection) == READ_INSERT | MUTATING
    assert _public(InsertOnlyCollection) == READ_INSERT
    assert _public(GuardedBucket) == {"delete", "download", "revisions", "upload"}


def test_no_forbidden_name_is_reachable_on_any_guarded_object(store: GuardedStore) -> None:
    for obj in (store, store.collection("projects"), store.collection("approvals"),
                store.bucket()):
        for name in FORBIDDEN:
            assert getattr(obj, name, None) is None, (type(obj).__name__, name)


def test_no_walk_of_the_guarded_objects_reaches_a_driver_or_fake_object(
        store: GuardedStore) -> None:
    reachable = []
    for root in (store, store.collection("projects"), store.bucket()):
        reachable += _walk(root, set())
    modules = {type(o).__module__.split(".")[0] for o in reachable}
    assert not modules & {"pymongo", "gridfs", "fake_mongo"}, modules


def test_the_walker_itself_finds_a_client_hidden_in_an_instance_dict() -> None:
    class Leaky:
        def __init__(self) -> None:
            self.inner = {"deep": [FakeMongoServer().client()]}

    modules = {type(o).__module__ for o in _walk(Leaky(), set())}
    assert "fake_mongo" in modules


def test_the_store_holds_no_uri_after_construction() -> None:
    client = FakeMongoServer().client()
    uri = "mongodb://user:CANARY-held@h/"
    guarded = GuardedStore(uri, client_factory=lambda _u: client)
    holders = [r for r in gc.get_referrers(uri) if r is guarded.__dict__]
    assert holders == [] and "CANARY-held" not in str(guarded.__dict__)


@pytest.mark.parametrize("name", sorted(INSERT_ONLY))
def test_insert_only_collections_have_no_replace_update_or_delete(
        store: GuardedStore, name: str) -> None:
    col = store.collection(name)
    assert type(col) is InsertOnlyCollection
    for verb in MUTATING:
        assert not hasattr(col, verb)
    col.insert_one({"_id": "a", "p": "x"})
    assert col.find_one({"_id": "a"}) == {"_id": "a", "p": "x"}
    with pytest.raises(StoreDuplicateKey):
        col.insert_one({"_id": "a", "p": "x"})


def test_every_other_collection_is_the_full_closed_verb_set(store: GuardedStore) -> None:
    assert all(type(store.collection(n)) is GuardedCollection for n in COLLECTIONS - INSERT_ONLY)


def test_collection_names_are_a_closed_set(store: GuardedStore) -> None:
    for name in ("anything_else", "system.users", "fs.files", "", "projects ", "Projects"):
        with pytest.raises(ValueError):
            store.collection(name)


def test_live_smoke_collection_needs_the_flag_and_no_ci(
        store: GuardedStore, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("AUTOTESTER_LIVE_MONGO_TEST", raising=False)
    with pytest.raises(ValueError):
        store.collection("t_x")
    monkeypatch.setenv("AUTOTESTER_LIVE_MONGO_TEST", "1")
    assert store.collection("t_smoke_1") is not None
    for bad in ("anything_else", "t_X", "T_x", "t_" + "a" * 31, "t_", "t_a.b"):
        with pytest.raises(ValueError):
            store.collection(bad)
    monkeypatch.setenv("CI", "true")
    with pytest.raises(ValueError):
        store.collection("t_smoke_1")


def test_update_operators_are_limited_and_immutable_fields_are_untouchable(
        store: GuardedStore) -> None:
    col = store.collection("auth_users")
    col.insert_one({"_id": 1, "p": "x", "generation": 1, "n": 0})
    assert col.update_one({"_id": 1}, {"$set": {"n": 5}}) is True
    assert col.update_one({"_id": 1}, {"$inc": {"n": 1}}) is True
    assert col.find_one({"_id": 1})["n"] == 6  # type: ignore[index]
    assert col.update_one({"_id": 2}, {"$setOnInsert": {"n": 0}, "$set": {"p": "x"}},
                          upsert=True) is True
    for update in ({"$unset": {"n": ""}}, {"$push": {"n": 1}}, {"$rename": {"n": "m"}},
                   {"$set": {"generation": 2}}, {"$inc": {"generation": 1}},
                   {"$set": {"_id": 9}}, {"$set": {"generation.x": 1}}, {}, {"n": 1}):
        with pytest.raises(ValueError):
            col.update_one({"_id": 1}, update)
    assert col.find_one({"_id": 1})["generation"] == 1  # type: ignore[index]


def test_writes_need_a_filter_and_delete_many_needs_a_project_or_key(store: GuardedStore) -> None:
    col = store.collection("cases")
    for p in ("a", "a", "b"):
        col.insert_one({"p": p, "k": p})
    for call in (lambda: col.delete_one({}), lambda: col.update_one({}, {"$set": {"x": 1}}),
                 lambda: col.replace_one({}, {"x": 1}), lambda: col.delete_many({}),
                 lambda: col.delete_many({"x": 1}), lambda: col.delete_many({"p": ""}),
                 lambda: col.delete_many({"p": {"$exists": True}}),
                 lambda: col.delete_many({"p": {"$ne": "a"}}), lambda: col.delete_many({"k": None}),
                 lambda: col.delete_many({"p": {"$in": []}}),
                 lambda: col.delete_many({"p": {"$in": [1]}})):
        with pytest.raises(ValueError):
            call()
    assert col.count_documents({}) == 3
    assert col.delete_many({"p": "a"}) == 2
    assert col.delete_many({"k": {"$in": ["b"]}}) == 1


def test_script_and_function_operators_are_refused_in_every_filter(store: GuardedStore) -> None:
    col = store.collection("cases")
    for flt in ({"$where": "1"}, {"a": {"$function": {}}}, {"$or": [{"$where": "1"}]}):
        for call in (col.find, col.find_one, col.count_documents, col.delete_one):
            with pytest.raises(ValueError):
                call(flt)

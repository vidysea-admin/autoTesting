"""mongo-store M2, M5, M8, M23, M25, M26 for `MongoBlobStore`, and the file-mode import boundary.

The contract suite (test_blobs.py) covers what both stores share; this is what only GridFS has:
revisions, the integrity of an interrupted put, the fence, the LRU cache and fail-closed.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from blob_support import KEY, SECRET, MongoRig, UniqueBucket, clean, put, tree
from fake_mongo import CANARY, FakeCollection, FakeMongoServer, assert_no_canary
from pymongo.errors import AutoReconnect

import autotester.store.blobs as blobs_module
from autotester.store.blobs import BlobRefused, MongoBlobStore
from autotester.store.mongo_guard import StoreUnavailable


def rev_data(rig: MongoRig) -> list[bytes]:
    return [d["data"] for d in rig.files]


# ---- M23 -----------------------------------------------------------------

def test_the_stored_metadata_has_sha256_kind_masked_and_content_type(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig, data=b"abc")
    meta = rig.files[0]["metadata"]
    assert meta["sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert (meta["kind"], meta["masked"], meta["content_type"]) == ("screenshot", True, "image/png")


def test_a_changed_put_uploads_the_new_revision_before_it_deletes_the_old(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig)
    order: list[str] = []
    real_insert, real_delete = FakeCollection.insert_one, FakeCollection.delete_one

    def spy_insert(self: Any, doc: Any) -> Any:
        order.extend(["upload"] * (self.name == "blobs.files"))
        return real_insert(self, doc)

    def spy_delete(self: Any, flt: Any) -> Any:
        order.extend(["delete"] * (self.name == "blobs.files"))
        return real_delete(self, flt)

    monkeypatch.setattr(FakeCollection, "insert_one", spy_insert)
    monkeypatch.setattr(FakeCollection, "delete_one", spy_delete)
    put(rig, data=b"two")
    assert order == ["upload", "delete"]
    assert rev_data(rig) == [b"two"]


def test_an_upload_that_fails_leaves_the_old_revision_readable(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig)

    def refuse(*_a: Any, **_k: Any) -> Any:
        raise AutoReconnect("upload died")  # only the upload dies: reads and the listing worked

    monkeypatch.setattr(UniqueBucket, "upload_from_stream", refuse)
    with pytest.raises(StoreUnavailable):
        put(rig, data=b"two")
    monkeypatch.undo()
    assert rig.blobs.get(KEY) == b"one" and rig.count(KEY) == 1


def test_a_put_interrupted_after_the_upload_leaves_both_and_reads_the_newest(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig)
    monkeypatch.setattr(type(rig.blobs), "_prune", lambda self, revs: (_ for _ in ()).throw(
        StoreUnavailable("down")))
    with pytest.raises(StoreUnavailable):
        put(rig, data=b"two")
    monkeypatch.undo()
    assert rig.count(KEY) == 2 and rig.blobs.get(KEY) == b"two"
    assert rig.blobs.stat(KEY).sha256 == hashlib.sha256(b"two").hexdigest()
    put(rig, data=b"two")  # the retry is a no-op write that heals the leftover
    assert rig.count(KEY) == 1 and rev_data(rig) == [b"two"]


def test_two_racing_puts_never_leave_zero_revisions(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """A put prunes only the revisions IT saw: a racing put's newer revision survives it."""
    first = MongoRig(tmp_path, redactor=clean)
    second = MongoRig(tmp_path, redactor=clean, server=first.server)
    put(first, data=b"x")
    stale = first.blobs._revisions(KEY)  # what the slower writer saw before the other finished
    put(second, data=b"y")
    monkeypatch.setattr(type(first.blobs), "_revisions", lambda self, key: stale)
    put(first, data=b"z")
    monkeypatch.undo()
    assert sorted(rev_data(first)) == [b"y", b"z"]  # two, never zero
    assert first.blobs.get(KEY) == b"z"
    put(first, data=b"z")  # the next put sees both and heals
    assert rev_data(first) == [b"z"]


def test_a_delete_racing_a_delete_does_not_raise_for_a_revision_already_gone(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real GridFS `delete` raises NoFile on a missing id; the loser of the race must not."""
    first = MongoRig(tmp_path, redactor=clean)
    second = MongoRig(tmp_path, redactor=clean, server=first.server)
    put(first)
    stale = first.blobs._revisions(KEY)
    assert second.blobs.delete(KEY) is True
    monkeypatch.setattr(type(first.blobs), "_revisions", lambda self, key: stale)
    assert first.blobs.delete(KEY) is True
    monkeypatch.undo()
    assert first.count(KEY) == 0


def test_a_missing_revision_is_still_an_error_for_the_bucket_itself(tmp_path: Path) -> None:
    from autotester.store.mongo_guard import StoreNotFound
    rig = MongoRig(tmp_path, redactor=clean)
    with pytest.raises(StoreNotFound):
        rig.blobs._bucket.delete("no-such-id")  # the fake now matches pymongo: NoFile -> NotFound


def test_delete_removes_every_revision_of_the_key_and_only_that_key(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig)
    put(rig, "p/other.png", b"keep")
    for body, seq in ((b"v2", 5), (b"v3", 6)):  # leftover revisions an interrupted put can leave
        rig.blobs._bucket.upload(KEY, body, metadata={"sha256": "s", "size": 2, "kind": "dom",
                                                      "masked": True, "content_type": "t",
                                                      "put_seq": seq})
    assert rig.count(KEY) == 3
    assert rig.blobs.delete(KEY) is True
    assert rig.count(KEY) == 0 and rig.count("p/other.png") == 1


def test_the_newest_revision_is_the_one_with_the_highest_put_seq_not_the_listing_order(
        tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    meta = {"size": 1, "kind": "dom", "masked": True, "content_type": "t"}
    for body, seq in ((b"newer", 9), (b"older", 3)):  # listed newest first
        sha = hashlib.sha256(body).hexdigest()
        rig.blobs._bucket.upload(KEY, body, metadata={**meta, "sha256": sha, "put_seq": seq})
    assert rig.blobs.stat(KEY).sha256 == hashlib.sha256(b"newer").hexdigest()


def test_the_bucket_lives_only_in_the_configured_database(tmp_path: Path) -> None:
    server = FakeMongoServer()
    server.seed_foreign("pathlynks")
    rig = MongoRig(tmp_path, redactor=clean, server=server)
    put(rig)
    assert set(server.databases) == {"autotester", "pathlynks"}
    assert set(server.databases["pathlynks"].collections) == {"users"}


# ---- M5 / M2 / M8 / M9 -----------------------------------------------------

@pytest.mark.parametrize("uri", ["mongodb://h/", "mongodb://h/scratch",
                                 "mongodb://h/?authSource=admin"])
def test_the_spy_sees_only_the_configured_database_across_the_blob_workload(
        tmp_path: Path, uri: str) -> None:
    server = FakeMongoServer()
    server.seed_foreign("scratch")
    rig = MongoRig(tmp_path, redactor=clean, uri=uri, server=server)
    server.log.clear()
    put(rig)
    put(rig, data=b"two")
    rig.blobs.get(KEY)
    rig.blobs.stat(KEY)
    rig.blobs.materialize(KEY)
    rig.blobs.delete(KEY)
    assert set(rig.client.accessed) == {"autotester"}
    assert {db for db, _ in server.log} == {"autotester"}
    assert server.databases["scratch"]["users"].docs == [{"_id": "foreign", "keep": True}]


def test_no_public_blob_api_takes_a_database_name() -> None:
    banned = {"db", "database", "db_name"}
    callables: list[Any] = []
    for obj in vars(blobs_module).values():
        if getattr(obj, "__module__", None) != blobs_module.__name__:
            continue
        if inspect.isfunction(obj):
            callables.append(obj)
        elif inspect.isclass(obj) and not issubclass(obj, BaseException):
            callables += [obj] + [m for n, m in inspect.getmembers(obj, inspect.isfunction)
                                  if not n.startswith("_") or n == "__init__"]
    assert len(callables) > 12
    for member in callables:
        assert not banned & set(inspect.signature(member).parameters), member
    with pytest.raises(TypeError):
        MongoBlobStore(None, "x")  # type: ignore[call-arg, misc]
    with pytest.raises(TypeError):
        MongoBlobStore(None, database="x")  # type: ignore[call-arg]


def test_a_secret_is_in_no_collection_or_chunk_of_the_whole_fake(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig)
    for plant in (f"p/{SECRET}.png", "p/n.txt"):
        with pytest.raises(BlobRefused):
            rig.blobs.put(plant, SECRET.encode(), kind="console", masked=True,
                          content_type="text/plain")
    dump = repr([(d.name, n, c.docs) for d in rig.server.databases.values()
                 for n, c in d.collections.items()])
    assert SECRET not in dump


def test_the_uri_password_is_never_echoed_by_a_failing_blob_call(
        tmp_path: Path, capsys: Any, caplog: Any) -> None:
    rig = MongoRig(tmp_path, redactor=clean, uri=f"mongodb://user:{CANARY}@h/")
    put(rig)
    rig.server.down = True
    for call in (lambda: put(rig, data=b"two"), lambda: rig.blobs.get(KEY),
                 lambda: rig.blobs.materialize(KEY), lambda: rig.blobs.delete(KEY)):
        with pytest.raises(StoreUnavailable) as err:
            call()
        assert_no_canary(err.value, capsys, caplog)


# ---- M26 / import boundary ---------------------------------------------------

def test_with_the_server_down_nothing_is_created_on_disk(tmp_path: Path) -> None:
    rig = MongoRig(tmp_path, redactor=clean)
    put(rig)
    rig.server.down = True
    before = tree(tmp_path)
    for call in (lambda: put(rig, "p/b.png", b"two"), lambda: rig.blobs.get(KEY),
                 lambda: rig.blobs.stat(KEY), lambda: rig.blobs.materialize(KEY)):
        with pytest.raises(StoreUnavailable):
            call()
    assert tree(tmp_path) == before
    rig.server.down_message, rig.server.down = AutoReconnect.__name__, False


def test_the_file_store_alone_never_imports_a_database_driver(tmp_path: Path) -> None:
    script = (
        "import sys, pathlib\n"
        "from autotester.store.blobs import FileBlobStore, repo_redactor\n"
        "s = FileBlobStore(pathlib.Path(sys.argv[1]), redactor=lambda: repo_redactor())\n"
        "s.put('p/a.png', b'x', kind='screenshot', masked=True)\n"
        "assert s.get('p/a.png') == b'x' and s.materialize('p/a.png').is_file()\n"
        "bad = [m for m in ('pymongo', 'gridfs', 'bson') if m in sys.modules]\n"
        "print('LOADED:' + ','.join(bad))\n")
    env = {**os.environ, "AUTOTESTER_ROOT": str(tmp_path)}
    done = subprocess.run([sys.executable, "-c", script, str(tmp_path / "d")], env=env,
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "LOADED:"

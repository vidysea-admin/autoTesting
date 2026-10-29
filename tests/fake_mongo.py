"""Hand-written Mongo double (contract mongo-store M47; `mongomock` is deliberately not used).

Covers exactly the verbs of `store/mongo_guard.py` and nothing else: a call outside that set is an
AttributeError, which is the point. `FakeMongoServer` holds the databases (so a test can plant a
FOREIGN database and prove the store never touches it); every `FakeMongoClient` is a SPY that
records each database name asked of it. No socket is ever opened.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from gridfs.errors import NoFile
from pymongo.errors import AutoReconnect, DuplicateKeyError

import autotester.store.mongo_guard as guard


def _match(doc: dict[str, Any], flt: dict[str, Any]) -> bool:
    return all(_ok(doc.get(key), cond, key in doc) for key, cond in flt.items())


def _ok(value: Any, cond: Any, present: bool) -> bool:
    if not (isinstance(cond, dict) and any(str(k).startswith("$") for k in cond)):
        return value == cond
    tests: dict[str, Callable[[Any], bool]] = {
        "$in": lambda arg: value in arg, "$ne": lambda arg: value != arg,
        "$exists": lambda arg: present == bool(arg), "$gt": lambda arg: value > arg,
        "$gte": lambda arg: value >= arg, "$lt": lambda arg: value < arg,
        "$lte": lambda arg: value <= arg,
    }
    return all(tests[op](arg) for op, arg in cond.items())


class FakeCollection:
    def __init__(self, db: FakeDatabase, name: str) -> None:
        self._db, self.name = db, name
        self.docs: list[dict[str, Any]] = []
        self.indexes: dict[str, tuple[list[tuple[str, int]], bool]] = {}

    def _down(self) -> None:
        self._db.server.check_up()
        self._db.server.log.append((self._db.name, self.name))

    def _unique_clash(self, doc: dict[str, Any], skip: dict[str, Any] | None = None) -> None:
        if any(d["_id"] == doc["_id"] for d in self.docs if d is not skip):
            raise DuplicateKeyError("E11000 duplicate key _id")
        for keys, unique in self.indexes.values():
            fields = [k for k, _ in keys]
            if unique and any(f in doc for f in fields) and any(
                    all(d.get(f) == doc.get(f) for f in fields)
                    for d in self.docs if d is not skip):
                raise DuplicateKeyError("E11000 duplicate key index")

    def find(self, flt: dict[str, Any], *, projection: Any = None, sort: Any = None,
             limit: int = 0) -> list[dict[str, Any]]:
        self._down()
        rows = [dict(d) for d in self.docs if _match(d, flt)]
        for key, direction in reversed(sort or []):
            rows.sort(key=lambda d, k=key: d.get(k), reverse=direction < 0)
        return rows[:limit] if limit else rows

    def find_one(self, flt: dict[str, Any]) -> dict[str, Any] | None:
        rows = self.find(flt, limit=1)
        return rows[0] if rows else None

    def count_documents(self, flt: dict[str, Any]) -> int:
        return len(self.find(flt))

    def insert_one(self, doc: dict[str, Any]) -> Any:
        self._down()
        doc = dict(doc)
        doc.setdefault("_id", f"auto-{len(self.docs)}")
        self._unique_clash(doc)
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc["_id"])

    def replace_one(self, flt: dict[str, Any], doc: dict[str, Any], *, upsert: bool = False) -> Any:
        self._down()
        hit = next((d for d in self.docs if _match(d, flt)), None)
        if hit is None:
            if not upsert:
                return SimpleNamespace(matched_count=0, upserted_id=None)
            new = {**{k: v for k, v in flt.items() if not isinstance(v, dict)}, **doc}
            self._unique_clash(new)
            self.docs.append(new)
            return SimpleNamespace(matched_count=0, upserted_id=new.get("_id"))
        new = {"_id": hit["_id"], **doc}
        self._unique_clash(new, skip=hit)
        hit.clear()
        hit.update(new)
        return SimpleNamespace(matched_count=1, upserted_id=None)

    def update_one(self, flt: dict[str, Any], update: dict[str, Any], *,
                   upsert: bool = False) -> Any:
        self._down()
        hit = next((d for d in self.docs if _match(d, flt)), None)
        inserted = hit is None
        if hit is None:
            if not upsert:
                return SimpleNamespace(matched_count=0, upserted_id=None)
            hit = {k: v for k, v in flt.items() if not isinstance(v, dict)}
            hit.update(update.get("$setOnInsert", {}))
            self.docs.append(hit)
        hit.update(update.get("$set", {}))
        for key, amount in update.get("$inc", {}).items():
            hit[key] = hit.get(key, 0) + amount
        return SimpleNamespace(matched_count=0 if inserted else 1,
                               upserted_id=hit.get("_id") if inserted else None)

    def delete_one(self, flt: dict[str, Any]) -> Any:
        self._down()
        hit = next((d for d in self.docs if _match(d, flt)), None)
        if hit is not None:
            self.docs.remove(hit)
        return SimpleNamespace(deleted_count=int(hit is not None))

    def delete_many(self, flt: dict[str, Any]) -> Any:
        self._down()
        gone = [d for d in self.docs if _match(d, flt)]
        self.docs[:] = [d for d in self.docs if d not in gone]
        return SimpleNamespace(deleted_count=len(gone))

    def create_index(self, keys: list[tuple[str, int]], *, unique: bool = False,
                     name: str | None = None) -> str:
        self._down()
        label = name or "_".join(f"{k}_{d}" for k, d in keys)
        self.indexes[label] = (keys, unique)
        return label


class FakeDatabase:
    def __init__(self, server: FakeMongoServer, name: str) -> None:
        self.server, self.name = server, name
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection(self, name))

    def list_collection_names(self) -> list[str]:
        self.server.check_up()
        return [n for n, c in self.collections.items() if c.docs or c.indexes]

    def command(self, name: str) -> dict[str, int]:
        self.server.check_up()
        self.server.log.append((self.name, f"command:{name}"))
        return {"ok": 1}


class FakeMongoServer:
    """Databases by name, an operation log, and an `down` switch that mimics a dead server."""

    def __init__(self, *, down_message: str = "server unreachable") -> None:
        self.databases: dict[str, FakeDatabase] = {}
        self.log: list[tuple[str, str]] = []
        self.down, self.down_message = False, down_message

    def check_up(self) -> None:
        if self.down:
            raise AutoReconnect(self.down_message)

    def database(self, name: str) -> FakeDatabase:
        return self.databases.setdefault(name, FakeDatabase(self, name))

    def seed_foreign(self, name: str, collection: str = "users") -> None:
        self.database(name)[collection].docs.append({"_id": "foreign", "keep": True})

    def client(self) -> FakeMongoClient:
        return FakeMongoClient(self)


class FakeMongoClient:
    """A spy: `.accessed` is every database name asked of it, in order."""

    def __init__(self, server: FakeMongoServer) -> None:
        self._server = server
        self.accessed: list[str] = []

    def __getitem__(self, name: str) -> FakeDatabase:
        self.accessed.append(name)
        return self._server.database(name)

    def get_database(self, name: str | None = None) -> FakeDatabase:
        self.accessed.append(f"get_database:{name}")
        return self._server.database(name or "test")


class FakeGridOut:
    def __init__(self, row: dict[str, Any]) -> None:
        self._id, self.filename = row["_id"], row["filename"]
        self.length, self.metadata = len(row["data"]), row["metadata"]


class FakeBucket:
    """Minimal `GridFSBucket`: files live in the SAME fake database as everything else."""

    def __init__(self, database: FakeDatabase, name: str) -> None:
        self._files = database[f"{name}.files"]

    def upload_from_stream(self, filename: str, data: bytes, *, metadata: dict[str, Any]) -> Any:
        row = {"_id": f"f{len(self._files.docs)}", "filename": filename, "data": bytes(data),
               "metadata": metadata}
        self._files.insert_one(row)
        return row["_id"]

    def open_download_stream_by_name(self, filename: str, revision: int = -1) -> io.BytesIO:
        rows = self._files.find({"filename": filename})
        if not rows:
            raise NoFile(filename)
        return io.BytesIO(rows[revision]["data"])

    def find(self, flt: dict[str, Any]) -> list[FakeGridOut]:
        return [FakeGridOut(r) for r in self._files.find(flt)]

    def delete(self, file_id: Any) -> None:
        self._files.delete_one({"_id": file_id})


@contextmanager
def seams(*, client_factory: Callable[[str], Any] | None = None, config_path: Path | None = None,
          bucket_factory: Callable[[Any, str], Any] | None = FakeBucket) -> Iterator[None]:
    """The ONLY way tests reach the guard's private seams (`guard._SEAM`); restored on exit."""
    saved = dict(guard._SEAM)
    guard._SEAM.update(client_factory=client_factory, config_path=config_path,
                       bucket_factory=bucket_factory)
    try:
        yield
    finally:
        guard._SEAM.update(saved)


def open_store(uri: str = "mongodb://h/", client: FakeMongoClient | None = None, *,
               client_factory: Callable[[str], Any] | None = None,
               config_path: Path | None = None) -> guard.GuardedStore:
    with seams(client_factory=client_factory or (lambda _uri: client), config_path=config_path):
        return guard.GuardedStore(uri)

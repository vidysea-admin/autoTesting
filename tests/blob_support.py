"""Test rig for the blob store: a guarded store over the hand-written fake, plus tree snapshots.

`UniqueBucket` fixes one flaw of `fake_mongo.FakeBucket` for THESE tests: it numbers files by the
current document count, so a delete followed by an upload can reuse an id (a false DuplicateKey).
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fake_mongo import FakeBucket, FakeMongoClient, FakeMongoServer, seams

import autotester.store.mongo_guard as guard
from autotester.core.redact import Redactor
from autotester.store.blobs import MongoBlobStore

SECRET = "Sup3r-Secret-Value-71x"
_IDS = itertools.count()


class UniqueBucket(FakeBucket):
    def upload_from_stream(self, filename: str, data: bytes, *, metadata: dict[str, Any]) -> Any:
        row = {"_id": f"f{next(_IDS)}", "filename": filename, "data": bytes(data),
               "metadata": metadata}
        self._files.insert_one(row)
        return row["_id"]


def tree(root: Path, *, stamps: bool = False) -> dict[str, Any]:
    """Every file under `root` by relative path -> bytes (or, `stamps`, bytes and mtime_ns)."""
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) if stamps
            else p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def file_count(root: Path) -> Callable[[str], int]:
    return lambda key: int((root / key).is_file())


class MongoRig:
    """A `MongoBlobStore` on a guarded store over `FakeMongoServer`; `cache` is its blob cache."""

    def __init__(self, tmp: Path, *, redactor: Callable[[], Redactor] | None = None,
                 uri: str = "mongodb://h/", cap: int = 512 * 1024 * 1024,
                 server: FakeMongoServer | None = None) -> None:
        self.server = server or FakeMongoServer()
        self.client: FakeMongoClient = self.server.client()
        with seams(client_factory=lambda _uri: self.client, bucket_factory=UniqueBucket):
            self.store = guard.GuardedStore(uri)
        self.cache = tmp / "cache"
        self.blobs = MongoBlobStore(self.store, redactor=redactor, cache_dir=self.cache,
                                    cache_cap_bytes=cap)

    @property
    def files(self) -> list[dict[str, Any]]:
        return self.server.database("autotester")["blobs.files"].docs

    def count(self, key: str) -> int:
        return sum(d["filename"] == key for d in self.files)

    def snapshot(self) -> str:
        """Every document of every collection of every database, plus the cache tree."""
        docs = {(db.name, name): [dict(d) for d in col.docs]
                for db in self.server.databases.values() for name, col in db.collections.items()}
        cached = tree(self.cache) if self.cache.exists() else {}
        return repr((sorted(docs.items(), key=repr), sorted(cached.items())))


KEY = "p/runs/r1/s1.png"


def clean() -> Redactor:
    return Redactor({"K": SECRET})


def put(rig: MongoRig, key: str = KEY, data: bytes = b"one", **kw: Any) -> Any:
    kw = {"kind": "screenshot", "masked": True, "content_type": "image/png", **kw}
    return rig.blobs.put(key, data, **kw)

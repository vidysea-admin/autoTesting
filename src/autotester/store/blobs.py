"""Binary evidence behind one interface: `BlobStore` over files or GridFS (mongo-store M23-M25).

`FileBlobStore` keeps bytes under a data root (today's layout, a sidecar under `.blobmeta/` records
the metadata). `MongoBlobStore` keeps them in the GridFS bucket of the ONE configured database,
reached only through `mongo_guard.GuardedStore.bucket()`: this module imports no driver and takes no
database name. Every `put` is vetted first (safe key, not a non-moving path, an unmasked screenshot
is refused, no declared secret value in the key, metadata or text body). `materialize` hands a
reader a real local path: the file itself, or a verified copy in `.work/blob-cache/` (512 MB LRU).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import mimetypes
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from autotester.core.env import read_dotenv
from autotester.core.paths import repo_root, work_dir
from autotester.core.redact import Redactor
from autotester.core.safe_names import safe_key
from autotester.store.filestore import FileBackend

if TYPE_CHECKING:
    from autotester.store.mongo_guard import GuardedStore

__all__ = ["CACHE_CAP_BYTES", "BlobCorrupt", "BlobInfo", "BlobNotFound", "BlobRefused",
           "BlobStore", "FileBlobStore", "MongoBlobStore", "repo_redactor"]

CACHE_CAP_BYTES = 512 * 1024 * 1024
META_DIR = ".blobmeta"
# M25: data that never moves into Mongo. Any key segment in the set, an `.env*` name, or `.xlsx`.
NOT_BLOB_SEGMENTS = frozenset({".work", "profiles", "chunks", "crawl_summaries", META_DIR})
NOT_BLOB_KINDS = frozenset({"export"})
UNMASKED_REFUSED = frozenset({"screenshot"})  # the FB3 mirror (Evidence.masked)
KIND = re.compile(r"[a-z][a-z_]{0,31}")
TEXT_MEDIA = frozenset({
    "application/json", "application/xml", "application/javascript", "application/x-javascript",
    "application/ecmascript", "application/yaml", "application/x-yaml", "application/x-ndjson",
    "application/x-www-form-urlencoded", "application/graphql"})
TEXT_SUFFIXES = ("+json", "+xml", "+yaml")


def _is_text(content_type: str) -> bool:
    """A media type is case-insensitive and may carry parameters: scan every textual body."""
    media = content_type.split(";")[0].strip().casefold()
    return media.startswith("text/") or media in TEXT_MEDIA or media.endswith(TEXT_SUFFIXES)


def _folded(part: str) -> str:
    """Windows aliases a name by case and by trailing dots or spaces: compare the alias."""
    return part.casefold().rstrip(". ")


class BlobNotFound(KeyError):
    """No such blob."""


class BlobRefused(ValueError):
    """A put the store will not take. The message names the rule, never a value."""


class BlobCorrupt(RuntimeError):
    """Stored bytes do not hash to the recorded sha256."""


@dataclass(frozen=True)
class BlobInfo:
    key: str
    sha256: str
    size: int
    kind: str
    masked: bool
    content_type: str


class BlobStore(Protocol):
    """What U5b's write-through and read sites use. Keys are safe POSIX keys (M17)."""

    def put(self, key: str, data: bytes, *, kind: str, masked: bool,
            content_type: str = "application/octet-stream") -> BlobInfo: ...
    def get(self, key: str) -> bytes: ...
    def stat(self, key: str) -> BlobInfo | None: ...
    def delete(self, key: str) -> bool: ...
    def materialize(self, key: str) -> Path: ...


def repo_redactor() -> Redactor:
    """A `Redactor` over every repo-root `.env` value (M8). The credential store's values join
    it when U11 passes its own `redactor` callable."""
    env = repo_root() / ".env"
    values = read_dotenv(env) if env.is_file() else {}
    return Redactor({k: v for k, v in values.items() if v})


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _vet(key: str, data: object, kind: str, masked: bool, content_type: str,
         redactor: Redactor) -> None:
    """Refuse before any write. Nothing here echoes the key, the body or a secret."""
    parts = [_folded(p) for p in safe_key(key).split("/")]
    name = parts[-1]
    if (NOT_BLOB_SEGMENTS.intersection(parts) or name == ".env" or name.startswith(".env.")
            or name.endswith(".xlsx") or kind in NOT_BLOB_KINDS):
        raise BlobRefused("this path or kind is not stored as a blob (M25)")
    if not isinstance(data, bytes | bytearray) or not KIND.fullmatch(kind):
        raise BlobRefused("a blob is bytes with a plain lower-case kind")
    if kind in UNMASKED_REFUSED and not masked:
        raise BlobRefused(f"a {kind} must be stored masked")
    text = [key, kind, content_type]
    if _is_text(content_type):
        text.append(bytes(data).decode("utf-8", errors="replace"))
    try:
        for part in text:
            redactor.assert_clean(part)
    except ValueError:
        raise BlobRefused("a declared secret value is in the blob or its metadata") from None


def _meta(data: bytes, kind: str, masked: bool, content_type: str) -> dict[str, Any]:
    return {"sha256": _sha(data), "size": len(data), "kind": kind, "masked": masked,
            "content_type": content_type}


def _info(key: str, meta: dict[str, Any]) -> BlobInfo:
    return BlobInfo(key, meta["sha256"], int(meta["size"]), meta["kind"], bool(meta["masked"]),
                    meta["content_type"])


def _same(a: dict[str, Any], b: dict[str, Any]) -> bool:
    fields = ("sha256", "kind", "masked", "content_type")
    return all(a.get(f) == b.get(f) for f in fields)


class FileBlobStore:
    """Bytes at `<root>/<key>`; metadata at `<root>/.blobmeta/<key>.json`. Atomic writes."""

    def __init__(self, root: Path, *, redactor: Callable[[], Redactor] | None = None) -> None:
        self._root, self._files = Path(root), FileBackend(Path(root))
        self._redactor = redactor or repo_redactor

    def _path(self, key: str) -> Path:
        return self._root.joinpath(*safe_key(key).split("/"))

    def _sidecar(self, key: str) -> dict[str, Any] | None:
        text = self._files.get(f"{META_DIR}/{safe_key(key)}.json")
        try:
            return json.loads(text) if text else None
        except ValueError:
            return None

    def stat(self, key: str) -> BlobInfo | None:
        path = self._path(key)
        if not path.is_file():
            return None
        data = path.read_bytes()
        meta = self._sidecar(key)
        if meta is None or meta.get("sha256") != _sha(data):  # absent or stale: say what we know
            guess = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            meta = _meta(data, "unknown", False, guess)
        return _info(key, meta)

    def put(self, key: str, data: bytes, *, kind: str, masked: bool,
            content_type: str = "application/octet-stream") -> BlobInfo:
        _vet(key, data, kind, masked, content_type, self._redactor())
        meta = _meta(bytes(data), kind, masked, content_type)
        current = self.stat(key)
        if current is not None and _same(meta, vars(current)) and self._sidecar(key) is not None:
            return current
        self._files.put(f"{META_DIR}/{key}.json", json.dumps(meta))  # sidecar first: a crash
        self._files.put(key, bytes(data))  # leaves a stale sidecar, which `stat` ignores
        return _info(key, meta)

    def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            raise BlobNotFound(key) from None

    def delete(self, key: str) -> bool:
        self._files.delete(f"{META_DIR}/{safe_key(key)}.json")
        return self._files.delete(key)

    def materialize(self, key: str) -> Path:
        path = self._path(key)
        if not path.is_file():
            raise BlobNotFound(key)
        return path


class MongoBlobStore:
    """GridFS revisions of one filename per key. A changed put adds the new revision FIRST, then
    removes the revisions it saw before, so a crash or a race never leaves zero (M23)."""

    def __init__(self, store: GuardedStore, *, redactor: Callable[[], Redactor] | None = None,
                 cache_dir: Path | None = None, cache_cap_bytes: int = CACHE_CAP_BYTES) -> None:
        self._bucket = store.bucket()
        self._redactor = redactor or repo_redactor
        self._cache_dir, self._cap = cache_dir, cache_cap_bytes

    def _revisions(self, key: str) -> list[dict[str, Any]]:
        revs = self._bucket.revisions(safe_key(key))
        return sorted(revs, key=lambda r: r["metadata"].get("put_seq", 0))  # oldest first

    def stat(self, key: str) -> BlobInfo | None:
        revs = self._revisions(key)
        return _info(key, revs[-1]["metadata"]) if revs else None

    def _prune(self, revs: list[dict[str, Any]]) -> None:
        from autotester.store import mongo_guard  # lazy: the file mode never loads the driver
        for rev in revs:
            with contextlib.suppress(mongo_guard.StoreNotFound):  # a racer removed it: pruned
                self._bucket.delete(rev["id"])

    def put(self, key: str, data: bytes, *, kind: str, masked: bool,
            content_type: str = "application/octet-stream") -> BlobInfo:
        _vet(key, data, kind, masked, content_type, self._redactor())
        meta = _meta(bytes(data), kind, masked, content_type)
        revs = self._revisions(key)
        if revs and _same(meta, revs[-1]["metadata"]):
            self._prune(revs[:-1])  # self-heal leftovers of an interrupted put
            return _info(key, revs[-1]["metadata"])
        self._bucket.upload(key, bytes(data), metadata={**meta, "put_seq": time.time_ns()})
        self._prune(revs)  # only what was seen BEFORE the upload: a racing put survives
        return _info(key, meta)

    def get(self, key: str) -> bytes:
        info = self.stat(key)
        if info is None:
            raise BlobNotFound(key)
        return self._verified(key, info)

    def _verified(self, key: str, info: BlobInfo) -> bytes:
        """The newest revision's bytes, proven to hash to the recorded sha256."""
        from autotester.store import mongo_guard  # lazy: the file mode never loads the driver
        try:
            data = self._bucket.download(key)
        except mongo_guard.StoreNotFound:
            raise BlobNotFound(key) from None
        if _sha(data) != info.sha256:
            raise BlobCorrupt(key)
        return data

    def delete(self, key: str) -> bool:
        revs = self._revisions(key)
        self._prune(revs)
        return bool(revs)

    def materialize(self, key: str) -> Path:
        info = self.stat(key)
        if info is None:
            raise BlobNotFound(key)
        cache = self._cache_dir or work_dir() / "blob-cache"
        rel = f"{info.sha256}/{key.rsplit('/', 1)[-1]}"
        dest = cache.joinpath(*rel.split("/"))
        if dest.is_file() and _sha(dest.read_bytes()) == info.sha256:
            os.utime(dest)  # most recently used
            return dest
        FileBackend(cache).put(rel, self._verified(key, info))
        _evict(cache, self._cap, keep=dest)
        return dest


def _evict(cache: Path, cap: int, *, keep: Path) -> None:
    """Least recently used first, until the cache fits `cap`; the file just served stays."""
    files = [(p.stat().st_mtime_ns, p.stat().st_size, p) for p in cache.rglob("*") if p.is_file()]
    total = sum(size for _, size, _ in files)
    for _, size, path in sorted(files):
        if total <= cap:
            break
        if path != keep:
            path.unlink(missing_ok=True)
            total -= size
            if path.parent != cache and not any(path.parent.iterdir()):
                path.parent.rmdir()

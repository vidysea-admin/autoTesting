"""Path-level coordination verbs over the state backends (mongo-store M19, M20, M52, M53; D-126).

One job: the verbs a store that coordinates needs on a `Path` and that `filestore` (at its line
cap) cannot hold. Every state verb routes exactly like `filestore`'s (`_route` / `_holders`), so a
path on a Mongo area reaches the Mongo backend and a path on a file area reaches the disk:

- `create_exclusive_path`, `put_if_path`: the two coordination primitives (one winner among
  concurrent callers; a write that loses to a newer one lands nothing), on every backend.
- `read_text_path`, `read_bytes_path`, `digest_path`: reads that answer `None` for an absent key.
- `rename_path`, `delete_tree`, `touch_path`: move a key, drop a prefix, refresh a lock's mtime.
- `RevisionedFile`: one whole-document file saved by compare-and-set with a `rev` that grows.
- `remove_stray_temps`, `remove_empty_dir`: file-backend housekeeping, a no-op elsewhere.

`scratch_*` are the opposite kind: they act on the LOCAL disk only, never on a backend, and refuse
any in-root path outside `.work/`. Download staging and unzip folders hold video bytes that must
never become state documents (M25: `.work/` scratch does not move), so they are not routed.
"""

from __future__ import annotations

import contextlib
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from autotester.core.safe_names import UnsafeName
from autotester.store.filestore import FileBackend, _holders, _rel, _route
from autotester.store.mongo_routes import text_sha

__all__ = [
    "RevisionedFile",
    "create_exclusive_path", "delete_tree", "digest_path", "evidence_mkdir", "is_dir_path",
    "put_if_path",
    "read_bytes_path", "read_text_path", "remove_empty_dir", "remove_stray_temps", "rename_path",
    "scratch_children", "scratch_mkdir", "scratch_mtime", "scratch_rmtree", "scratch_unlink",
    "touch_path",
]


def create_exclusive_path(path: Path, text: str) -> bool:
    """Create `path` holding `text` only if nothing is there: True for the one caller that did.
    Atomic content: a reader sees nothing or all of `text`, never part of it."""
    backend, key = _route(path)
    return backend.create_exclusive(key, text)


def put_if_path(path: Path, text: str, expect_sha: str | None) -> bool:
    """Compare-and-set: write `text` only if the stored text hashes to `expect_sha` (`None`: the
    key must not exist). False, and nothing written, when another writer got there first."""
    backend, key = _route(path)
    return backend.put_if(key, text, expect_sha)


def read_text_path(path: Path) -> str | None:
    """The stored text, or `None` when there is none."""
    backend, key = _route(path)
    return backend.get(key)


def read_bytes_path(path: Path) -> bytes | None:
    """The stored bytes (byte-exact on files; the UTF-8 of the text on a document), else `None`."""
    backend, key = _route(path)
    if isinstance(backend, FileBackend):
        return backend.get_bytes(key)
    text = backend.get(key)
    return None if text is None else text.encode("utf-8")


def digest_path(path: Path) -> str | None:
    """The digest `put_if_path` compares (SHA-256 of the stored text), `None` when absent."""
    text = read_text_path(path)
    return None if text is None else text_sha(text)


def is_dir_path(path: Path) -> bool:
    """`Path.is_dir()` for state: something is stored below `path` (any backend)."""
    backends, key = _holders(path)
    return any(b.is_dir(key) for b in backends)


def rename_path(src: Path, dst: Path) -> None:
    """Move one stored file. Two files: `os.replace` (atomic, overwrites). Otherwise copy then
    delete, so a failure part way leaves the source in place. `FileNotFoundError` if absent."""
    (from_backend, from_key), (to_backend, to_key) = _route(src), _route(dst)
    if isinstance(from_backend, FileBackend) and isinstance(to_backend, FileBackend):
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        return
    text = from_backend.get(from_key)
    if text is None:
        raise FileNotFoundError(src)
    to_backend.put(to_key, text)
    from_backend.delete(from_key)


def delete_tree(path: Path) -> int:
    """Delete `path` and everything below it, on every backend that may hold something there;
    the count of keys removed. Never the whole store (an empty scope raises `UnsafeName`)."""
    backends, key = _holders(path)
    removed = 0
    for backend in backends:
        if isinstance(backend, FileBackend) and Path(path).is_dir():
            removed += sum(1 for f in Path(path).rglob("*") if f.is_file())
            shutil.rmtree(path, ignore_errors=True)  # in one sweep: no half-emptied folder
        removed += backend.delete_prefix(key)
    return removed


def touch_path(path: Path) -> None:
    """Refresh the mtime of a stored key (a lock's heartbeat). `FileNotFoundError` if absent."""
    backend, key = _route(path)
    if isinstance(backend, FileBackend):
        os.utime(path, None)
        return
    text = backend.get(key)
    if text is None:
        raise FileNotFoundError(path)
    backend.put(key, text)


def remove_stray_temps(folder: Path) -> int:
    """Remove the `.tmp-*` leftovers of a killed atomic write in a state folder (file backend
    only; a document backend has none). Returns how many."""
    backend, _ = _route(folder)
    if not isinstance(backend, FileBackend):
        return 0
    strays = list(Path(folder).glob(".tmp-*"))
    for stray in strays:
        stray.unlink(missing_ok=True)
    return len(strays)


def remove_empty_dir(folder: Path) -> None:
    """Remove `folder` if it is an empty directory (file backend only); anything else is left."""
    backend, _ = _route(folder)
    if isinstance(backend, FileBackend):
        with contextlib.suppress(OSError):
            Path(folder).rmdir()


def _scratch(path: Path) -> Path:
    """`path` if it is scratch (outside the data root or under its `.work/`), else `UnsafeName`."""
    key = _rel(path)
    if key is not None and not key.startswith(".work/"):
        raise UnsafeName(f"{key!r} is state, not scratch: use the store verbs")
    return Path(path)


def scratch_mkdir(path: Path, *, exist_ok: bool = False) -> None:
    _scratch(path).mkdir(parents=True, exist_ok=exist_ok)


def scratch_children(path: Path) -> list[Path]:
    """The entries directly in the scratch directory, sorted; `[]` when it does not exist."""
    base = _scratch(path)
    return sorted(base.iterdir()) if base.is_dir() else []


def scratch_mtime(path: Path) -> float | None:
    try:
        return _scratch(path).stat().st_mtime
    except OSError:
        return None


def scratch_rmtree(path: Path) -> None:
    shutil.rmtree(_scratch(path), ignore_errors=True)


def scratch_unlink(path: Path) -> None:
    _scratch(path).unlink(missing_ok=True)


def evidence_mkdir(path: Path) -> None:
    """Create a checked-in evidence directory (`qa/evidence/...`; M49: evidence is not state, so it
    stays on the local disk). Any other path is refused: a state folder is made by writing to it."""
    if "qa/evidence/" not in Path(path).as_posix() + "/":
        raise UnsafeName(f"{Path(path).name!r} is not under qa/evidence/")
    Path(path).mkdir(parents=True, exist_ok=True)


M = TypeVar("M", bound=BaseModel)


class RevisionedFile(Generic[M]):
    """A whole-document state file (model `M` with an int `rev` field) saved by compare-and-set.

    `load` reads it and remembers its digest and rev as the base; `save` writes only if the stored
    text still has that digest, so a writer that lost a race lands nothing (False) and the next
    save is made against what is stored now. With no base yet, `save` takes the current digest."""

    def __init__(self, path: Callable[[], Path], model: type[M]) -> None:
        self._path, self._model = path, model
        self._known, self._rev, self._sha = False, 0, None

    def load(self) -> M | None:
        """The stored document, `None` when absent; a text that fails to validate raises
        `ValueError` and leaves the base unknown."""
        self._known = False
        text = read_text_path(self._path())
        doc = None if text is None else self._model.model_validate_json(text)
        self._rev = int(doc.model_dump().get("rev", 0)) if doc is not None else 0
        self._sha, self._known = (None if text is None else text_sha(text)), True
        return doc

    def save(self, build: Callable[[int], M]) -> bool:
        """Write `build(next rev)` if nothing changed since the base; True when it landed."""
        path = self._path()
        text = build(self._rev + 1).model_dump_json()
        if put_if_path(path, text, self._sha if self._known else digest_path(path)):
            self._known, self._rev, self._sha = True, self._rev + 1, text_sha(text)
            return True
        self.load()  # adopt what won, so the next save compares against it
        return False

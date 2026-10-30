"""The one place any artifact is read from or written to disk. Contract: core-invariants.md C6.

Every typed wrapper (`ProjectStore`, the feature ledger) is built on the `Path` functions here,
so "how does file X get persisted" has one answer. Underneath, each call goes to a `StateBackend`
addressed by a safe POSIX key (mongo-store M13-M17). `AUTOTESTER_STORE` picks `file` (the default,
so no database driver is imported) or `mongo` (`store/mongo_backend.py`, loaded on first use).
File writes are atomic (temp file + `os.replace`): a crash never leaves a half-written artifact.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from autotester.core.file_lock import atomic_write as _atomic_write
from autotester.core.file_lock import file_lock
from autotester.core.paths import repo_root
from autotester.core.safe_names import safe_key
from autotester.store.mongo_routes import (
    StateBackend,
    StoreSelectionError,
    area_of,
    require_scope,
    row_matches,
    store_selection,
    text_sha,
    under,
    within,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class FileBackend:
    """Files under `root`: atomic replace, `O_EXCL` claims, a sidecar lock for compare-and-set."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def _path(self, key: str) -> Path:
        return self._root.joinpath(*safe_key(key).split("/"))

    def get(self, key: str) -> str | None:
        try:
            return self._path(key).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def put(self, key: str, data: str | bytes) -> None:
        _atomic_write(self._path(key), data)

    def put_if(self, key: str, text: str, expect_sha: str | None) -> bool:
        path = self._path(key)
        with file_lock(path.with_name(f".{path.name}.lock"), what="state key"):
            current = self.get(key)
            if (None if current is None else text_sha(current)) != expect_sha:
                return False
            _atomic_write(path, text)
        return True

    def create_exclusive(self, key: str, text: str) -> bool:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
        except BaseException:
            path.unlink(missing_ok=True)  # never leave an empty claim behind
            raise
        return True

    def delete(self, key: str) -> bool:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            return False
        return True

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def keys(self, prefix: str, suffix: str = "") -> list[str]:
        safe_key(prefix, prefix=True)
        base = self._root.joinpath(*prefix.rpartition("/")[0].split("/"))
        found = (p.relative_to(self._root).as_posix() for p in base.rglob("*")
                 if p.is_file() and not p.name.startswith(".tmp-") and not p.name.endswith(".lock"))
        return sorted(k for k in found if k.startswith(prefix) and k.endswith(suffix))

    def delete_prefix(self, prefix: str) -> int:
        """Delete `prefix` itself and what sits below it on a `/` boundary; never everything."""
        return sum(self.delete(k) for k in self.keys(require_scope(prefix)) if within(k, prefix))

    def _dir(self, key: str) -> Path:
        return self._path(key) if key else self._root

    def children(self, key: str, suffix: str = "") -> list[str]:
        base = self._dir(key)
        return sorted(p.name for p in base.iterdir() if p.name.endswith(suffix)
                      and not p.name.startswith(".tmp-") and not p.name.endswith(".lock")
                      ) if base.is_dir() else []

    def is_dir(self, key: str) -> bool:
        return self._dir(key).is_dir()

    def mtime(self, key: str) -> float | None:
        path = self._path(key)
        return path.stat().st_mtime if path.exists() else None

    def rows(self, key: str) -> list[str]:
        return [line for line in (self.get(key) or "").splitlines() if line.strip()]

    def append_row(self, key: str, text: str) -> None:
        self.append_text(key, text + "\n")

    def append_text(self, key: str, text: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def replace_rows(self, key: str, rows: list[str]) -> None:
        _atomic_write(self._path(key), "".join(f"{row}\n" for row in rows))

    def upsert_row(self, key: str, field: str, value: str, text: str) -> None:
        rows = self.rows(key)
        hit = [row_matches(row, field, value) for row in rows]
        self.replace_rows(key, [text if h else row for row, h in zip(rows, hit, strict=True)]
                          + ([] if any(hit) else [text]))

    def delete_row(self, key: str, field: str, value: str) -> bool:
        rows = self.rows(key)
        kept = [row for row in rows if not row_matches(row, field, value)]
        if len(kept) != len(rows):
            self.replace_rows(key, kept)
        return len(kept) != len(rows)

    def ping(self) -> None: ...  # files are always reachable


def _backend(name: str) -> StateBackend:
    if name == "file":
        return FileBackend(repo_root())
    if name == "mongo":
        from autotester.store.mongo_backend import default_backend  # the only driver import

        return default_backend()
    raise StoreSelectionError(f"unknown store backend {name!r}")


def validate_store_env() -> dict[str, str]:
    """Startup check: the selection parses and every backend it chose is available (M13)."""
    selection = store_selection()
    for name in set(selection.values()):
        _backend(name)
    return selection


def backend_for(key: str) -> StateBackend:
    return _backend(store_selection()[area_of(safe_key(key))])


def _rel(path: Path) -> str | None:
    """The key of `path` under the data root (`""` for the root itself), else `None`."""
    try:
        key = Path(path).relative_to(repo_root()).as_posix()
    except ValueError:
        return None
    return "" if key == "." else key


def _route(path: Path) -> tuple[StateBackend, str]:
    """`(backend, key)`. A path outside the data root (temp, scratch) is always a plain file."""
    key = _rel(path)
    if key is None:
        return FileBackend(Path(path).parent), Path(path).name
    return backend_for(key), key


def _parse_rows(lines: list[str], path: Path, model_cls: type[ModelT]) -> list[ModelT]:
    items: list[ModelT] = []
    for number, line in enumerate(lines, start=1):
        try:
            items.append(model_cls.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from None
    return items


def write_text(path: Path, text: str) -> None:
    """Whole-file, atomic text. For stores that hold something other than one model."""
    backend, key = _route(path)
    backend.put(key, text)


def write_bytes(path: Path, data: bytes) -> None:
    """Whole-file atomic bytes, preserving encoding/newlines for reversible migrations."""
    backend, key = _route(path)
    backend.put(key, data)


def write_json(path: Path, model: BaseModel) -> None:
    """Whole-file, atomic. For the single-object artifacts (project, flowspec)."""
    write_text(path, model.model_dump_json(indent=2, exclude_none=True) + "\n")


def read_json(path: Path, model_cls: type[ModelT]) -> ModelT | None:
    """`None` when absent (a project with no flowspec yet); a file that fails to validate raises."""
    backend, key = _route(path)
    text = backend.get(key)
    if text is None:
        return None
    try:
        return model_cls.model_validate_json(text)
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from None


def read_jsonl(path: Path, model_cls: type[ModelT]) -> list[ModelT]:
    """Every row, in file order. A malformed row raises with its row number."""
    backend, key = _route(path)
    return _parse_rows(backend.rows(key), path, model_cls)


def append_path(path: Path, text: str | bytes) -> None:
    """Append to a log-style state file, creating it (atomic on Memory/Mongo, plain `a` on File)."""
    backend, key = _route(path)
    backend.append_text(key, text if isinstance(text, str) else text.decode("utf-8"))


def delete_path(path: Path, *, missing_ok: bool = True) -> None:
    """`Path.unlink()` for a state file: `FileNotFoundError` when absent unless `missing_ok`."""
    backend, key = _route(path)
    if not backend.delete(key) and not missing_ok:
        raise FileNotFoundError(path)


def append_jsonl(path: Path, model: BaseModel) -> None:
    """One more row. Never rewrites what is there: a torn write only damages the last line."""
    backend, key = _route(path)
    backend.append_row(key, model.model_dump_json(exclude_none=True))


def delete_jsonl_row(path: Path, model_cls: type[ModelT], row_id: str, *, key: str = "id") -> bool:
    """Drop the row whose stored field `key` equals `row_id`; True when one was removed."""
    if key not in model_cls.model_fields:
        raise ValueError(f"{key!r} is not a stored field of {model_cls.__name__}")
    backend, state_key = _route(path)
    _parse_rows(backend.rows(state_key), path, model_cls)  # a malformed row still raises
    return backend.delete_row(state_key, key, row_id)


def upsert_jsonl(path: Path, model: ModelT, model_cls: type[ModelT], *, key: str = "id") -> None:
    """Replace the row whose `key` matches this model's (in place), else append. A `key` that is
    a property, not a stored field, is matched on the parsed rows and the collection rewritten."""
    backend, state_key = _route(path)
    items = _parse_rows(backend.rows(state_key), path, model_cls)
    text = model.model_dump_json(exclude_none=True)
    if key in model_cls.model_fields:
        backend.upsert_row(state_key, key, str(json.loads(text).get(key)), text)
        return
    target = getattr(model, key)
    lines = [text if getattr(i, key) == target else i.model_dump_json(exclude_none=True)
             for i in items]
    backend.replace_rows(state_key, lines if text in lines else [*lines, text])


def _holders(path: Path) -> tuple[list[StateBackend], str]:
    """Every backend that may hold something at or below `path`, and its key (`_route`'s)."""
    backend, key = _route(path)
    if _rel(path) != key:  # outside the data root: always a plain file
        return [backend], key
    chosen = store_selection()
    names = {chosen[a] for a in {area_of(key), *(a for _, a in under(key))}}
    return [_backend(name) for name in sorted(names)], key


def exists_path(path: Path) -> bool:
    """`Path.exists()` for state: a file, or a directory that holds state (any backend)."""
    backends, key = _holders(path)
    return any(b.exists(key) or b.is_dir(key) for b in backends)


def list_children(path: Path, *, suffix: str = "") -> list[str]:
    """Names directly under the state directory `path`, sorted; `[]` when there is none."""
    backends, key = _holders(path)
    return sorted({name for b in backends for name in b.children(key, suffix)})


def mtime_path(path: Path) -> float | None:
    """When the state file `path` was last written (seconds since the epoch), else `None`."""
    backend, key = _route(path)
    return backend.mtime(key)

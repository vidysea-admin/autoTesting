"""The one place any artifact is read from or written to disk. Contract: core-invariants.md C6.

Every typed wrapper (`ProjectStore`, the feature ledger) is built on the `Path` functions here,
so "how does file X get persisted" has one answer. Underneath, each call goes to a `StateBackend`
addressed by a safe POSIX key (mongo-store M13-M17). Only `FileBackend` is wired in this build,
chosen by `AUTOTESTER_STORE` (default `file`), so no database driver is imported. File writes are
atomic (temp file + `os.replace`): a crash mid-write never leaves a half-written artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from autotester.core.file_lock import file_lock
from autotester.core.paths import repo_root
from autotester.core.safe_names import safe_key

ModelT = TypeVar("ModelT", bound=BaseModel)
BACKENDS = ("file", "mongo")
AREAS = ("settings", "projects", "runs", "crawls", "approvals", "auth", "credentials", "blobs",
         "queue")


class StoreSelectionError(ValueError):
    """`AUTOTESTER_STORE` / `AUTOTESTER_STORE_AREAS` names something unknown or not wired."""


def text_sha(text: str) -> str:
    """The digest `put_if` compares: SHA-256 of the text as `get` returns it, UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StateBackend(Protocol):
    """Keys: relative POSIX paths. Rows: ordered JSON lines. Each method runs `safe_key` first."""

    def get(self, key: str) -> str | None: ...
    def put(self, key: str, data: str | bytes) -> None: ...
    def put_if(self, key: str, text: str, expect_sha: str | None) -> bool: ...
    def create_exclusive(self, key: str, text: str) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def exists(self, key: str) -> bool: ...
    def keys(self, prefix: str, suffix: str = "") -> list[str]: ...
    def delete_prefix(self, prefix: str) -> int: ...
    def rows(self, key: str) -> list[str]: ...
    def append_row(self, key: str, text: str) -> None: ...
    def upsert_row(self, key: str, field: str, value: str, text: str) -> None: ...
    def delete_row(self, key: str, field: str, value: str) -> bool: ...
    def replace_rows(self, key: str, rows: list[str]) -> None: ...
    def ping(self) -> None: ...


def row_matches(line: str, field: str, value: str) -> bool:
    """True when the JSON row's `field` (as text) equals `value`; a missing field reads `None`."""
    try:
        row = json.loads(line)
    except ValueError:
        return False
    return isinstance(row, dict) and str(row.get(field)) == value


def _atomic_write(path: Path, text: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        mode, options = ("wb", {}) if isinstance(text, bytes) else ("w", {"encoding": "utf-8"})
        with os.fdopen(fd, mode, **options) as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


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
        return sum(self.delete(key) for key in self.keys(prefix))

    def rows(self, key: str) -> list[str]:
        return [line for line in (self.get(key) or "").splitlines() if line.strip()]

    def append_row(self, key: str, text: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

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


def store_selection() -> dict[str, str]:
    """Area -> backend from `AUTOTESTER_STORE` (default file) + `AUTOTESTER_STORE_AREAS=a=b,..`."""
    chosen = dict.fromkeys(AREAS, os.environ.get("AUTOTESTER_STORE", "").strip() or "file")
    for item in filter(None, (i.strip() for i in os.environ.get("AUTOTESTER_STORE_AREAS", "")
                              .split(","))):
        area, _, backend = (piece.strip() for piece in item.partition("="))
        if area not in AREAS:
            raise StoreSelectionError(f"AUTOTESTER_STORE_AREAS: unknown area {area!r} in {item!r}")
        chosen[area] = backend
    for name in chosen.values():
        if name not in BACKENDS:
            raise StoreSelectionError(f"unknown store backend {name!r}; use one of {BACKENDS}")
    return chosen


def area_of(key: str) -> str:
    """Coarse area of a key; the per-collection table is the Mongo backend's (U4)."""
    parts = [*key.split("/"), "", ""]
    if parts[0] == "projects":
        return {"runs": "runs", "crawl": "crawls"}.get(parts[2], "projects")
    return "settings" if parts[0] == ".work" else "projects"


def _backend(name: str) -> StateBackend:
    if name == "file":
        return FileBackend(repo_root())
    raise StoreSelectionError(f"backend {name!r} is recognised but not wired in this build")


def validate_store_env() -> dict[str, str]:
    """Startup check: the selection parses and every backend it chose is available (M13)."""
    selection = store_selection()
    for name in set(selection.values()):
        _backend(name)
    return selection


def backend_for(key: str) -> StateBackend:
    return _backend(store_selection()[area_of(safe_key(key))])


def _route(path: Path) -> tuple[StateBackend, str]:
    """`(backend, key)`. A path outside the data root (temp, scratch) is always a plain file."""
    path = Path(path)
    try:
        key = path.relative_to(repo_root()).as_posix()
    except ValueError:
        return FileBackend(path.parent), path.name
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
    """`None` when the file is absent — a project with no flowspec yet is not an error.

    A file that exists but fails to validate raises, naming the path.
    """
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


def append_jsonl(path: Path, model: BaseModel) -> None:
    """One more row. Never rewrites what is already there — cheap and crash-safe
    (a torn write can only ever damage the last line, never an earlier one)."""
    backend, key = _route(path)
    backend.append_row(key, model.model_dump_json(exclude_none=True))


def delete_jsonl_row(path: Path, model_cls: type[ModelT], row_id: str, *, key: str = "id") -> bool:
    """Drop the row whose stored field `key` equals `row_id`; True when one was removed.
    For a small collection a human curates, never for append-only history."""
    if key not in model_cls.model_fields:
        raise ValueError(f"{key!r} is not a stored field of {model_cls.__name__}")
    backend, state_key = _route(path)
    _parse_rows(backend.rows(state_key), path, model_cls)  # a malformed row still raises
    return backend.delete_row(state_key, key, row_id)


def upsert_jsonl(path: Path, model: ModelT, model_cls: type[ModelT], *, key: str = "id") -> None:
    """Replace the row whose `key` matches this model's (in place), else append. For status
    transitions on a small collection; prefer `append_jsonl` for history. A `key` that is a
    property, not a stored field, is matched on the parsed rows and the collection rewritten."""
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

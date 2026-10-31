"""Persist one run's LangGraph checkpoint without arbitrary Python deserialization.

The pinned InMemorySaver supplies graph semantics; explicit tagged JSON supplies
only primitives, interruptions and inert error text. No pickle, import-based
reviver or callable tag is accepted. Construction is read-only. Per-path locks
serialize background mutations; disk identity checks refuse stale instances.
The caller must hold its same-project run reservation across processes.
"""

from __future__ import annotations

import base64
import json
import math
import threading
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Interrupt

from autotester.core.redact import Redactor
from autotester.store.filestore_paths import digest_path, put_if_path, read_text_path
from autotester.store.mongo_routes import text_sha

_FORMAT = "autotester.checkpoint.v1"
_CHANGED = "Checkpoint changed outside this instance; reconstruct to resume"
_MUTATORS = ("put", "put_writes", "delete_thread")
_READERS = ("get_tuple", "list", "get_delta_channel_history")
_LOCKS: dict[Path, Any] = {}
_LOCKS_GUARD = threading.Lock()


def _enc(obj: Any) -> Any:
    """Encode only the explicit checkpoint vocabulary, never arbitrary classes."""
    if obj is None or type(obj) in (str, bool, int):
        return obj
    if type(obj) is float and math.isfinite(obj):
        return obj
    if type(obj) in (bytes, bytearray):
        return {type(obj).__name__: base64.b64encode(obj).decode("ascii")}
    if type(obj) is tuple:
        return {"tuple": [_enc(v) for v in obj]}
    if type(obj) is dict:
        return {"dict": [[_enc(k), _enc(v)] for k, v in obj.items()]}
    if type(obj) is list:
        return [_enc(v) for v in obj]
    if type(obj) is Interrupt:
        if obj.response_schema is not None and type(obj.response_schema) is not dict:
            raise ValueError("Checkpoint interrupt schema must be JSON")
        return {"interrupt": [_enc(obj.value), obj.id, _enc(obj.response_schema)]}
    if isinstance(obj, BaseException):
        return {"error": f"{type(obj).__name__}: {obj}"}
    raise ValueError("Unsupported checkpoint value")


def _dec(obj: Any) -> Any:
    """Decode explicit inert tags; unknown, duplicate or malformed tags refuse."""
    if obj is None or type(obj) in (str, bool, int):
        return obj
    if type(obj) is float and math.isfinite(obj):
        return obj
    if type(obj) is list:
        return [_dec(v) for v in obj]
    if type(obj) is not dict or len(obj) != 1:
        raise ValueError("Malformed checkpoint tag")
    tag, value = next(iter(obj.items()))
    if tag in ("bytes", "bytearray") and type(value) is str:
        raw = base64.b64decode(value, validate=True)
        return raw if tag == "bytes" else bytearray(raw)
    if tag == "tuple" and type(value) is list:
        return tuple(_dec(v) for v in value)
    if tag == "dict" and type(value) is list:
        result: dict[Any, Any] = {}
        for pair in value:
            if type(pair) is not list or len(pair) != 2:
                raise ValueError("Malformed checkpoint mapping")
            key, item = _dec(pair[0]), _dec(pair[1])
            if key in result:
                raise ValueError("Duplicate checkpoint key")
            result[key] = item
        return result
    if tag == "interrupt" and type(value) is list and len(value) == 3:
        payload, identity, schema = _dec(value[0]), value[1], _dec(value[2])
        if (type(identity) is not str or not identity
                or (schema is not None and type(schema) is not dict)):
            raise ValueError("Malformed checkpoint interruption")
        return Interrupt(payload, id=identity, response_schema=schema)
    if tag == "error" and type(value) is str:
        return RuntimeError(value)
    raise ValueError("Unknown checkpoint tag")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """JSON duplicate keys are corruption, not a last-value-wins repair."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate checkpoint JSON key")
        result[key] = value
    return result


class CheckpointSerializer:
    """The pinned typed-serde protocol, restricted to our explicit JSON tags."""

    def __init__(self, redactor: Redactor) -> None:
        self.redactor = redactor

    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        text = self.redactor.scrub(json.dumps(_enc(obj), allow_nan=False))
        self.redactor.assert_clean(text)
        return "safe-json", text.encode("utf-8")

    def loads_typed(self, data: tuple[str, bytes]) -> Any:
        if (type(data) is not tuple or len(data) != 2
                or data[0] != "safe-json" or type(data[1]) is not bytes):
            raise ValueError("Unsupported checkpoint serialization")
        self.redactor.assert_clean(data[1].decode("utf-8"))
        return _dec(json.loads(data[1], object_pairs_hook=_pairs))


def _persisting(name: str):  # type: ignore[no-untyped-def]
    """Serialize one pinned mutator and roll back memory on persistence failure."""
    parent = getattr(InMemorySaver, name)

    def wrapper(self: FileCheckpointer, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            self._check_thread(args, kwargs)
            self._check_disk()
            before = _dec(_enc(self._tables()))
            try:
                result = parent(self, *args, **kwargs)
                self.flush()
                return result
            except BaseException:
                self._restore(before)
                raise

    wrapper.__name__ = name
    return wrapper


def _reading(name: str):  # type: ignore[no-untyped-def]
    parent = getattr(InMemorySaver, name)

    def wrapper(self: FileCheckpointer, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            self._check_thread(args, kwargs)
            self._check_disk()
            result = parent(self, *args, **kwargs)
            return iter(list(result)) if name == "list" else result

    wrapper.__name__ = name
    return wrapper


class FileCheckpointer(InMemorySaver):
    """Run-bound atomic snapshots over checkpoint4.2.0's three memory tables."""

    def __init__(self, path: Path, *, thread_id: str, redactor: Redactor | None = None) -> None:
        if type(thread_id) is not str or not thread_id.strip():
            raise ValueError("A checkpoint needs an exact run identity")
        super().__init__(serde=CheckpointSerializer(redactor or Redactor({})))
        self.path = Path(path).resolve()
        self.thread_id = thread_id
        with _LOCKS_GUARD:
            self._lock = _LOCKS.setdefault(self.path, threading.RLock())
        with self._lock:
            self._disk_hash = self._digest()
            self._load()

    def _digest(self) -> str | None:
        return digest_path(self.path)

    def _check_disk(self) -> None:
        if self._digest() != self._disk_hash:
            raise RuntimeError(_CHANGED)

    def _check_thread(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        config = args[0] if args else kwargs.get("config", kwargs.get("thread_id"))
        if config is None:
            return
        identity = (config.get("configurable", {}).get("thread_id")
                    if type(config) is dict else config)
        if identity != self.thread_id:
            raise ValueError("Foreign checkpoint run identity")

    def _tables(self) -> dict[str, Any]:
        return {"storage": {t: dict(n) for t, n in self.storage.items()},
                "writes": dict(self.writes), "blobs": dict(self.blobs)}

    def _restore(self, data: dict[str, Any]) -> None:
        self.storage.clear()
        self.writes.clear()
        self.blobs.clear()
        for thread, namespaces in data["storage"].items():
            for ns, checkpoints in namespaces.items():
                self.storage[thread][ns].update(checkpoints)
        for key, rows in data["writes"].items():
            self.writes[key].update(rows)
        self.blobs.update(data["blobs"])

    def _load(self) -> None:
        text = read_text_path(self.path)
        if text is None:
            return
        raw = json.loads(text, object_pairs_hook=_pairs)
        if type(raw) is not dict or set(raw) != {"format", "thread_id", "tables"}:
            raise ValueError("Malformed checkpoint envelope")
        if raw["format"] != _FORMAT or raw["thread_id"] != self.thread_id:
            raise ValueError("Unknown or foreign checkpoint envelope")
        data = _dec(raw["tables"])
        self._validate_tables(data)
        self._restore(data)

    def _validate_tables(self, data: Any) -> None:
        if type(data) is not dict or set(data) != {"storage", "writes", "blobs"}:
            raise ValueError("Malformed checkpoint tables")
        if any(type(table) is not dict for table in data.values()):
            raise ValueError("Malformed checkpoint table")
        for thread, namespaces in data["storage"].items():
            if thread != self.thread_id or type(namespaces) is not dict:
                raise ValueError("Foreign checkpoint storage")
            for ns, checkpoints in namespaces.items():
                if type(ns) is not str or type(checkpoints) is not dict:
                    raise ValueError("Malformed checkpoint namespace")
                for identity, row in checkpoints.items():
                    if type(identity) is not str or type(row) is not tuple or len(row) != 3:
                        raise ValueError("Malformed stored checkpoint")
                    self.serde.loads_typed(row[0])
                    self.serde.loads_typed(row[1])
                    if row[2] is not None and type(row[2]) is not str:
                        raise ValueError("Malformed checkpoint parent")
        for key, rows in data["writes"].items():
            if (type(key) is not tuple or len(key) != 3
                    or key[0] != self.thread_id or type(rows) is not dict):
                raise ValueError("Foreign checkpoint writes")
            for identity, row in rows.items():
                if (type(identity) is not tuple or len(identity) != 2
                        or type(row) is not tuple or len(row) != 4):
                    raise ValueError("Malformed pending checkpoint write")
                self.serde.loads_typed(row[2])
        for key, row in data["blobs"].items():
            if type(key) is not tuple or len(key) != 4 or key[0] != self.thread_id:
                raise ValueError("Foreign checkpoint blob")
            if row != ("empty", b""):
                self.serde.loads_typed(row)

    def flush(self) -> None:
        """Persist through the store's atomic whole-document write, under the mutation lock."""
        with self._lock:
            self._check_disk()
            tables = self._tables()
            self._validate_tables(tables)
            payload = {"format": _FORMAT, "thread_id": self.thread_id, "tables": _enc(tables)}
            text = json.dumps(payload, allow_nan=False)
            self.serde.redactor.assert_clean(text)
            if not put_if_path(self.path, text, self._disk_hash):  # compare-and-set (M20)
                raise RuntimeError(_CHANGED)
            self._disk_hash = text_sha(text)


for _name in _MUTATORS:
    setattr(FileCheckpointer, _name, _persisting(_name))
for _name in _READERS:
    setattr(FileCheckpointer, _name, _reading(_name))

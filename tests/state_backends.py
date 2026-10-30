"""The backends the one contract suite runs on (mongo-store M15), and the dict-backed double.

`BACKEND_FACTORIES` is the single place a backend joins the suite: U4 adds one `"mongo"` entry that
builds a `MongoBackend` over `fake_mongo`, and every contract test then runs on it unchanged.

`InMemoryBackend` is the second leg.

It keeps each key as one text document, exactly as the file backend does, so a row is a line of
that text. That makes it a reference for the semantics (ordering, position-keeping upsert, one
winner for `create_exclusive`, `put_if` against the digest of the text) rather than a second
implementation to keep in step. One lock serialises every method, which is all the exclusive-create
and compare-and-set guarantees need in a single process.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from autotester.core.safe_names import safe_key
from autotester.store.filestore import FileBackend, StateBackend, row_matches, text_sha


class InMemoryBackend:
    def __init__(self) -> None:
        self.docs: dict[str, str] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self.docs.get(safe_key(key))

    def put(self, key: str, data: str | bytes) -> None:
        with self._lock:
            self.docs[safe_key(key)] = data.decode("utf-8") if isinstance(data, bytes) else data

    def put_if(self, key: str, text: str, expect_sha: str | None) -> bool:
        with self._lock:
            current = self.get(key)
            if (None if current is None else text_sha(current)) != expect_sha:
                return False
            self.put(key, text)
            return True

    def create_exclusive(self, key: str, text: str) -> bool:
        with self._lock:
            if safe_key(key) in self.docs:
                return False
            self.docs[key] = text
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            return self.docs.pop(safe_key(key), None) is not None

    def exists(self, key: str) -> bool:
        with self._lock:
            return safe_key(key) in self.docs

    def keys(self, prefix: str, suffix: str = "") -> list[str]:
        with self._lock:
            safe_key(prefix, prefix=True)
            return sorted(k for k in self.docs if k.startswith(prefix) and k.endswith(suffix))

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            return sum(self.delete(key) for key in self.keys(prefix))

    def rows(self, key: str) -> list[str]:
        return [line for line in (self.get(key) or "").splitlines() if line.strip()]

    def append_row(self, key: str, text: str) -> None:
        with self._lock:
            self.put(key, (self.get(key) or "") + text + "\n")

    def replace_rows(self, key: str, rows: list[str]) -> None:
        self.put(key, "".join(f"{row}\n" for row in rows))

    def upsert_row(self, key: str, field: str, value: str, text: str) -> None:
        with self._lock:
            rows = self.rows(key)
            hit = [row_matches(row, field, value) for row in rows]
            self.replace_rows(key, [text if h else row for row, h in zip(rows, hit, strict=True)]
                              + ([] if any(hit) else [text]))

    def delete_row(self, key: str, field: str, value: str) -> bool:
        with self._lock:
            rows = self.rows(key)
            kept = [row for row in rows if not row_matches(row, field, value)]
            if len(kept) != len(rows):
                self.replace_rows(key, kept)
            return len(kept) != len(rows)

    def ping(self) -> None:
        return None


BACKEND_FACTORIES: dict[str, Callable[[Path], StateBackend]] = {
    "file": FileBackend,
    "memory": lambda _root: InMemoryBackend(),
}

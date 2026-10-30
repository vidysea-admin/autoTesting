"""mongo-store U11 test rig: the credentials area on mongo over the hand-written fake.

`CredRig` turns the area on (`AUTOTESTER_STORE_AREAS=credentials=mongo`), plants a URI whose
password is the canary, and exposes what the fake server holds, so a test can say where a value
is and, above all, where it is not (M31). Every value here is synthetic.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fake_mongo import CANARY, FakeMongoServer, seams

from autotester.core.env import MONGO_URI_ENV
from autotester.store.mongo_backend import reset_default_backend

URI = f"mongodb://user:{CANARY}@db.example/"
VALUE = "Qv7-synthetic-store-value-1"
OTHER = "Qv7-synthetic-store-value-2"


class CredRig:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.server = FakeMongoServer()

    def collection(self, name: str) -> list[dict[str, Any]]:
        return [d for db in self.server.databases.values() for c in [db.collections.get(name)]
                if c is not None for d in c.docs]

    def secrets(self) -> list[dict[str, Any]]:
        return self.collection("secrets")

    def everywhere(self) -> str:
        """Every document in every collection of every database, as one string."""
        return repr([(db.name, name, c.docs) for db in self.server.databases.values()
                     for name, c in db.collections.items()])

    def tree(self) -> str:
        """A digest of the data root: names and bytes of every file."""
        digest = hashlib.sha256()
        for path in sorted(self.root.rglob("*")) if self.root.exists() else []:
            digest.update(path.relative_to(self.root).as_posix().encode())
            digest.update(path.read_bytes() if path.is_file() else b"")
        return digest.hexdigest()

    @contextmanager
    def live(self) -> Iterator[CredRig]:
        reset_default_backend()
        with seams(client_factory=lambda _uri: self.server.client()):
            yield self
        reset_default_backend()


def make_rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, area: bool = True) -> CredRig:
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.delenv("AUTOTESTER_MONGO_URI", raising=False)
    if area:
        monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "credentials=mongo")
        monkeypatch.setenv(MONGO_URI_ENV, URI)
    else:
        monkeypatch.delenv("AUTOTESTER_STORE_AREAS", raising=False)
        monkeypatch.delenv(MONGO_URI_ENV, raising=False)
    return CredRig(root)

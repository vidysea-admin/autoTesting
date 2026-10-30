"""The auth store backends the one contract suite runs on (mongo-store U6b, M29/M30).

`auth_env` is the single place a backend joins `tests/test_auth_store_contract.py`: the `"mongo"`
leg selects the auth area through the real `AUTOTESTER_STORE_AREAS` path and points the guard at
the hand-written `fake_mongo` double (no socket), so the business modules (`accounts`, `groups`,
`sessions`, `access`) run unchanged on both.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path

import pytest
from auth_harness import gate_on
from fake_mongo import FakeMongoServer, seams

from autotester.auth import db
from autotester.auth.store_mongo import reset_auth_store

BACKENDS = ("sqlite", "mongo")
OLD = "2000-01-01T00:00:00+00:00"
DATABASE = "autotester"  # `[tool.autotester.store].database`


class AuthEnv:
    def __init__(self, name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.name, self.tmp_path, self._mp = name, tmp_path, monkeypatch
        self.server = FakeMongoServer()
        self._count = 0

    def fresh(self) -> None:
        """A brand-new, empty auth store (a new SQLite file, or a new fake Mongo server)."""
        self._count += 1
        if self.name == "sqlite":
            self._mp.setenv("AUTOTESTER_AUTH_DIR", str(self.tmp_path / f"auth-{self._count}"))
        else:
            self.server = FakeMongoServer()
            reset_auth_store()

    def digests(self) -> list[str]:
        """The session ids the store holds (only ever the sha256 of a token)."""
        if self.name == "sqlite":
            with sqlite3.connect(db.auth_db_path()) as raw:
                return [d for (d,) in raw.execute("SELECT token_hash FROM sessions")]
        return [d["_id"] for d in self._coll("auth_sessions").docs]

    def expire(self, token: str) -> None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        if self.name == "sqlite":
            with sqlite3.connect(db.auth_db_path()) as raw:
                raw.execute("UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
                            (OLD, digest))
            return
        for doc in self._coll("auth_sessions").docs:
            if doc["_id"] == digest:
                doc["expires_at"] = OLD

    def _coll(self, name: str):
        return self.server.database(DATABASE)[name]

    def nothing_written(self) -> bool:
        if self.name == "sqlite":
            return not db.auth_db_path().exists()
        return not any(c.docs or c.indexes
                       for d in self.server.databases.values() for c in d.collections.values())

    def dump(self) -> str:
        """Every stored value of the active store, as text (for the no-leak scans)."""
        if self.name == "sqlite":
            with sqlite3.connect(db.auth_db_path()) as raw:
                return "".join(repr(raw.execute(f"SELECT * FROM {t}").fetchall())
                               for t in ("meta", "users", "groups", "group_permissions",
                                         "memberships", "sessions", "project_grants"))
        return repr({n: c.docs for n, c in self.server.database(DATABASE).collections.items()})


def auth_env(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    gate_on(tmp_path, monkeypatch)
    env = AuthEnv(name, tmp_path, monkeypatch)
    with ExitStack() as stack:
        if name == "mongo":
            monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "auth=mongo")
            monkeypatch.setenv("AUTOTESTER_MONGO_URI", "mongodb://h/")
            stack.enter_context(seams(client_factory=lambda _uri: env.server.client()))
        reset_auth_store()
        env.fresh()
        try:
            yield env
        finally:
            reset_auth_store()
